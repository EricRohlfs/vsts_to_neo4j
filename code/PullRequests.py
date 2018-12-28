'''
Copys VSTS PullRequests to Neo4J
Todo: permanently cache the completed and abandoned pull requests
Todo: have a flag to update non-completed. This can be helpful if recently crashed
Todo: could have a flag to not use open pull requests are older than so may days
'''
from multiprocessing import Pool
from VSTSInfo import VstsInfo
from models import GraphBuilder, Repository, PullRequest, Person, WorkItem

class PullRequestsWorker(object):
    '''
    Adds VSTS pull requests to Neo4J
    and links to various other nodes such as CreatedBy and Repository just to name a few.

    Note: queries Neo4J for the git repositories.

    :param string status:
        pull request status usually Active, Abandoned, Completed

    :param VstsInfo vsts:
        stuff needed to connect to VSTS

    :param int num_per_request:
        number of pull requests to get per request
        we don't want to get too many it might take too long or fail in other ways

    '''

    def __init__(self, pull_request_status, vsts, num_per_request=10):
        self.num_per_request = num_per_request
        self.vsts = vsts
        self.pull_request_status = pull_request_status

    def crawl_projects(self, projects):
        """
        Same as crawl but accepts an array of projects to call and calls them
        """
        for proj in projects:
            self.crawl(proj)

    def get_repo_ids(self, graph, project_name):
        """
        Gets the git repository id's stored in Neo4j
        """
        repo_ids = []
        qry = """MATCH (n:Repository)-[r]-(:Project{{Name:'{0}'}})
                 RETURN n.Id""".format(project_name)
        raw_repo_ids = graph.data(qry)
        for raw_repo_id in raw_repo_ids:
            repo_ids.append(raw_repo_id.get('n.Id'))
        return repo_ids

    def crawl(self, project_name):
        '''
        For a single project, gets the pull requests
            from VSTS and saves them to a neo4j database instance
        The list of repositories comes from neo4j, so that import must be done first.

        :param project_name:
        '''

        graph = GraphBuilder().GetNewGraph()
        repo_ids = self.get_repo_ids(graph, project_name)
        for repo_id in repo_ids:
            skip = 0 #part of vsts pagination
            while True:
                url = self.get_vsts_pull_request_url(project_name, repo_id, skip)
                raw_pulls = self.vsts.make_request(url)
                if not self.has_data_to_parse(raw_pulls):
                    break
                skip = skip + self.num_per_request #increment pagination for vsts api call
                for raw_pull_req in raw_pulls["value"]:
                    self.map_and_save_pull_request(graph, raw_pull_req)

        print("Ending PullRequest Crawl for Project " + project_name)

    def get_vsts_pull_request_url(self, project_name, repository_id, skip):
        '''
        returns a string
        '''
        #request_info = self.vsts.get_info()
        #instance = self.vsts.instance
        #api_version = self.vsts.api_version

        #project name has zero impact on the query
        pull_request_url = (("%s/DefaultCollection/%s/_apis/git/repositories/"+
                             "%s/pullRequests?api-version=%s&$top=%s&$skip=%s&status=%s") %
                            (self.vsts.instance,
                             project_name,
                             repository_id,
                             self.vsts.api_version,
                             self.num_per_request,
                             skip,
                             self.pull_request_status)
                           )
        print(pull_request_url)
        return pull_request_url

    def map_pull_request_parameters(self, pull_request, vsts_results):
        '''
        creates a new pull request node to be saved to neo4J
        '''
        #build out a pull request item
        item = vsts_results
        pull_request.Id = item.get("pullRequestId")
        pull_request.CreationDate = item.get("creationDate")
        pull_request.Status = item.get("status")
        pull_request.Title = item.get("title")
        pull_request.SourceBranchName = item.get("sourceRefName")
        pull_request.TargetBranchName = item.get("targetRefName")
        pull_request.Url = item.get("url")
        pull_request.ClosedDate = item.get("closedDate")
        return pull_request

    def link_repository(self, pull_request, vsts_info, graph):
        '''
        links a git repository to a pull request
        '''
        repo_id = vsts_info["repository"]["id"]
        repo = Repository.select(graph, repo_id).first()
        if repo is not None:
            pull_request.ForRepository.add(repo)
        else:
            print("could not find repositry for pull request we have a problem.")

    def link_branches(self, pull_request, vsts_info):
        '''
        links branches to the pull request
        '''
        repo_name = None
        repo_node = vsts_info.get("repository")
        if repo_node is not None:
            repo_name = repo_node.get("name")
        if repo_name is None:
            print("problem making names so can't link branches")
            return
        pull_request.SourceBranchName = vsts_info.get("sourceRefName")
        #if source_ref is not None:
        #    source_branch_id = Branch().generate_branch_id(repo_name, source_ref)
        #    s_branch = Branch.select(graph, source_branch_id).first()
        #    if s_branch is None:
        #        s_branch = Branch()
        #        s_branch.Id = source_branch_id
        #    pull_request.SourceBranch.add(s_branch)

        #target_ref = vsts_info.get("targetRefName")
        pull_request.TargetBranchName = vsts_info.get("targetRefName")
        #if target_ref is not None:
        #    target_branch_id = Branch().generate_branch_id(repo_name, target_ref)
        #    t_branch = Branch.select(graph, target_branch_id).first()
        #    if t_branch is None:
        #        t_branch = Branch()
        #        t_branch.Id = target_branch_id

        #    pull_request.TargetBranch.add(t_branch)

    def link_reviewers(self, pull_request, vsts_info, graph):
        '''
        links reviewers to the pull request
        '''
        for reviewer_info in vsts_info["reviewers"]:
            rev_id = reviewer_info.get("id")
            reviewer = Person.select(graph, rev_id).first()
            if reviewer is not None:
                pull_request.ReviewedBy.add(reviewer)

    def link_created_by(self, pull_request, vsts_info, graph):
        '''
        link the pull request to the person who created it
        '''
        raw = vsts_info.get("createdBy")
        user_id = raw.get("id")
        created_by = Person.select(graph, user_id).first()
        if created_by:
            pull_request.CreatedBy.add(created_by)
        else:
            print("Pull Request CreatedBy User not in db")
            user = Person()
            user.Id = user_id
            pull_request.CreatedBy.add(user)

    def link_work_items(self, pull_request, raw, graph):
        """
        if a pull request has links, this will crawl the links and link the work items.
        If the work item does not exist a new one will be created and hopefully added.
        """
        real_url = raw.get("url")
        data = self.vsts.make_request(real_url)

        links = data.get("_links")
        if links is None:
            print("Could not find links")
            return
        work_items_url = links.get("workItems")
        if work_items_url is None:
            print("no work items")
            return
        href = work_items_url.get("href")
        if href is None:
            print("no href found for " + str(pull_request.Id))
        work_item_links = self.vsts.make_request(href)
        for wi_link in work_item_links.get("value"):
            work_item_id = wi_link.get("id")
            work_item = WorkItem.select(graph, work_item_id).first()
            if work_item is None:
                work_item = WorkItem()
                work_item.Id = work_item_id
                graph.create(work_item)
                print("new work item added " + str(work_item.Id))
            work_item.LinkedTo.add(pull_request)
            graph.push(work_item)

    def get_pull_request_neo4j(self, graph, pull_req_id):
        """
        loads an existing Neo4j pull request or creates a new bare minimum one in the database
        :param graph: py2neo PullRequest
        :returns: from Neo4j either a new or existing PullRequest
        """
        pull = PullRequest.select(graph, pull_req_id).first()
        if pull is None:
            pull = PullRequest()
            pull.Id = pull_req_id
            graph.create(pull)
        return pull

    def has_data_to_parse(self, raw_vsts_data):
        """
        In some cases a request does not have any data,
        Others we have reached the end of pagination
        """
        has_data = False
        if raw_vsts_data is not None:
            if raw_vsts_data.get("count") > 0:
                has_data = True
        return has_data

    def map_and_save_pull_request(self, graph, raw_pull_req):
        """
        maps raw data from VSTS and saves to Neo4j database

        :param graph: py2neo graph object
        :param raw_pull_req: raw api result form VSTS for a single pulll request
        """
        pull_id = str(raw_pull_req.get("pullRequestId"))
        print("working pull request " + pull_id)
        pull = self.get_pull_request_neo4j(graph, pull_id)
        self.map_pull_request_parameters(pull, raw_pull_req)
        graph.merge(pull)
        self.link_repository(pull, raw_pull_req, graph)
        self.link_branches(pull, raw_pull_req)
        self.link_reviewers(pull, raw_pull_req, graph)
        self.link_created_by(pull, raw_pull_req, graph)
        self.link_work_items(pull, raw_pull_req, graph)
        graph.push(pull)
        print("saved pull request " + str(pull.Id))

if __name__ == '__main__':
    print("starting PullRequests")
    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = False

    GRAPH = GraphBuilder()
    GRAPH.create_unique_constraints()

    VSTS = VstsInfo(None, None)
    PULL_REQUEST_STATUS = "Completed"
    WORKER = PullRequestsWorker(PULL_REQUEST_STATUS, VSTS)

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(WORKER.crawl, VSTS.project_whitelist)
    else:
        WORKER.crawl_projects(VSTS.project_whitelist)
