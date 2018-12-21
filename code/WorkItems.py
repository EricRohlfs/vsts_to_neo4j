"""
From a Pull Request Id, gets related work items and saves them.
"""
import logging
from multiprocessing import Pool
from VSTSInfo import VstsInfo
from models import GraphBuilder, Project, WorkItem, Person, PullRequest

class PullReqeustWorkItemsWorker(object):
    """
    Gets work items linked to pull requests and saves them to Neo4j
    :param: int space_out_requests:
        time to wait between http calls so we don't max out the server

    :todo $expand=relations will get the relations so we can link them up
    """

    def __init__(self, request_info, vsts, space_out_requests=1):
        self.instance = request_info["instance"]
        self.api_version = request_info["api_version"]
        self.headers = request_info["headers"]
        self.space_out_requests = space_out_requests
        self.vsts = vsts

    def crawl(self, repository_id, pull_request_id):
        """
        Entry point for this class
        """
        if (repository_id is None) or (pull_request_id is None):
            print("could not get work item one of the id's was None")
            print(repository_id)
            print(pull_request_id)
            return

        graph = GraphBuilder().GetNewGraph()
        pull_request = PullRequest.select(graph, pull_request_id).first()
        if pull_request is None:
            print("Could not continue, pullrequest was not in db")
            return
        url = self.pull_request_workitems_url(repository_id, pull_request.Id)
        data = self.get_data(url)
        if data is None:
            return
        if "value" not in data:
            logging.info("no work items linked")
            return
        for raw in data["value"]:
            work_item = self.make_work_item(raw)
            if work_item is not None:
                self.link_to_pull_request(work_item, pull_request)
                self.fill_in_the_rest(work_item, graph)
                transaction = graph.begin()
                transaction.merge(work_item)
                transaction.graph.push(work_item)

    def link_to_pull_request(self, work_item, pull_request):
        """
        links pull request to a work item
        """
        if pull_request is None:
            return
        if pull_request.Id is None:
            return
        if work_item is None:
            return

        work_item.LinkedTo.add(pull_request)

    def clean_up_user_name(self, name):
        """
        Names have email addresses in them like: John Doe <john_doe@example.com>
        """
        name = name.split(" <")[0]
        return name

    def get_work_item_url(self, work_item_id):
        """
        get url to call vsts work item
        """
        #https://mycompany.visualstudio.com/DefaultCollection/_apis/wit/workItems/12345
        url = ("%s/DefaultCollection/_apis/wit/workitems/%s?api-version=%s" %
               (self.instance, work_item_id, self.api_version))
        return url

    def fill_in_the_rest(self, work_item, graph):
        """
        Query VSTS for the given url, then save the results
        """
        if work_item.Url is None:
            work_item.Url = self.get_work_item_url(work_item.Id)
        raw = self.get_data(work_item.Url)
        fields = raw.get("fields")
        work_item.WorkItemType = fields.get("System.WorkItemType")
        work_item.Title = fields.get("System.Title")
        work_item.AreaPath = fields.get("System.AreaPath")
        work_item.IterationPath = fields.get("System.IterationPath") #todo:link to real iterations
        work_item.CreatedDate = fields.get("System.CreatedDate")
        work_item.ValueArea = fields.get("System.ValueArea")
        work_item.Url = raw.get("url")
        work_item.Rev = raw.get("rev")
        work_item.State = fields.get("System.State")
        work_item.ClosedDate = fields.get("Microsoft.VSTS.Common.ClosedDate")
        work_item.ChangedDate = fields.get("System.ChangedDate")

        #if work_item.WorkItemType == "User Story":
        work_item.StoryPoints = fields.get("Microsoft.VSTS.Scheduling.StoryPoints")
        work_item.Priority = fields.get("Microsoft.VSTS.Common.Priority:")
        work_item.Risk = fields.get("Microsoft.VSTS.Common.Risk")
        work_item.ValueArea = fields.get("Microsoft.VSTS.Common.ValueArea") #Business or Architectual

        #if work_item.WorkItemType == "Task":
        work_item.Activity = fields.get("Microsoft.VSTS.Common.Activity")
        work_item.OriginalEstimate = fields.get("Microsoft.VSTS.Scheduling.OriginalEstimate")
        work_item.CompletedWork = fields.get("Microsoft.VSTS.Scheduling.CompletedWork")

        #bugs
        work_item.Severity = fields.get("Microsoft.VSTS.Common.Severity")
        work_item.BugFoundInEnvironment = fields.get("Microsoft.VSTS.CMMI.FoundInEnvironment")
        work_item.BugReason = fields.get("System.Reason")

        #todo add ability for custom fields from the cfg file.
        #risk
        #work_item.RiskProbability = fields.get("")
        #work_item.RiskExposure = fields.get("")
        #work_item.RiskSeverity = fields.get("")

        #Issue
        #work_item.IssueSource = fields.get("")

        name_raw = fields.get("System.CreatedBy")
        if name_raw is not None:
            name = self.clean_up_user_name(name_raw)
            work_item.Creator = name #just in case the relationship link fails
            stmt = "_.Name =~ '" + name + "' "
            creator = Person.select(graph).where(stmt).first()
            if creator is not None:
                work_item.CreatedBy.add(creator)

        assigned_to = fields.get("System.AssignedTo")
        if assigned_to is not None:
            name = self.clean_up_user_name(name_raw)
            work_item.Creator = name #just in case the relationship link fails
            stmt = "_.Name =~ '" + name + "' "
            person = Person.select(graph).where(stmt).first()
            if person is not None:
                work_item.AssignedTo.add(person)

        _proj_name = fields.get("System.TeamProject")
        if _proj_name is not None:
            work_item.ProjectName = _proj_name #just in case the relationship link fails
            where_stmt = "_.Name = '" + _proj_name + "'"
            proj_qry = Project.select(graph).where(where_stmt)
            proj = proj_qry.first()
            if proj is not None:
                work_item.ForProject.add(proj)

    def make_work_item(self, raw):
        """
        create new
        """
        work_item = WorkItem()
        work_item.Id = raw.get("id")
        work_item.Url = raw.get("url")
        return work_item

    def pull_request_workitems_url(self, repository_id, pull_request_id):
        '''
        returns a string
        '''
        #project name has zero impact on the query
        pull_request_url = ("%s/DefaultCollection/_apis/git/repositories/%s/pullRequests/%s/workitems?api-version=%s" %
                            (self.instance,
                             repository_id,
                             pull_request_id,
                             self.api_version
                            ))
        return pull_request_url

    def get_data(self, url):
        '''
        Make the VSTS call and convert results to a dictionary
        '''
        data = self.vsts.make_request(url)
        return data

    def get_repository_ids(self, project_name):
        """
        get list of repository ids
        """
        graph = GraphBuilder().GetNewGraph()
        repo_qry = "MATCH (n:Repository)-[]-(p:Project{{Name:'{}'}}) return n.Id as Id".format(project_name)
        repo_ids = list(graph.run(repo_qry))
        ids = []
        for _id in repo_ids:
            ids.append(_id.get("Id"))
        repo_ids = None
        return ids

    def get_pull_request_ids(self, repository_id):
        """
        Get list of pull request ids
        """
        graph = GraphBuilder().GetNewGraph()
        qry = "MATCH (n:Repository{{Id:'{}'}}) -[]-(r:PullRequest) RETURN r.Id as Id ".format(repository_id)
        pull_reqs = list(graph.run(qry))
        ids = []
        for _id in pull_reqs:
            ids.append(_id.get("Id"))
        pull_reqs = None
        return ids

    def add_pull_request_work_items(self, project_name):
        """
        Helper method to call crawl
        """
        print("Getting work items for project " + project_name)
        repo_ids = self.get_repository_ids(project_name)
        for repo_id in repo_ids:
            pull_reqs = self.get_pull_request_ids(repo_id)
            for pull_request_id in pull_reqs:
                self.crawl(repo_id, pull_request_id)

if __name__ == '__main__':
    print("starting Work Items linked to Pull Requests")
    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = True

    VSTS = VstsInfo(None, None)
    WORKER = PullReqeustWorkItemsWorker(VSTS.get_request_settings(), VSTS)

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(WORKER.add_pull_request_work_items, VSTS.project_whitelist)
    else:
        for proj_name in VSTS.project_whitelist:
            WORKER.add_pull_request_work_items(proj_name)
