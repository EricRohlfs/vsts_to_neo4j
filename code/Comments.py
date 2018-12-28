'''
Comments.py
From VSTS imports the pull request comments and stores them in Neo4j linked to users and pull requests
'''
import logging
from multiprocessing import Pool
from VSTSInfo import VstsInfo
from models import GraphBuilder, PullRequest, Comment, PullRequestThread, Person

class CommentsWorker():
    '''
    Gets Comments from VSTS and saves them to Neo4J
    '''

    def __init__(self, vsts, exclude_system_comments=True):
        self._exclude_system_comments = exclude_system_comments
        self._vsts = vsts

    @property
    def vsts_api(self):
        """
        api helper class to make calls to vsts
        """
        return self._vsts

    @property
    def exclude_system_comments(self):
        """
        When getting comments from VSTS should system comments be excluded.
        This ensures only user comments are put into Neo4j
        """
        return self._exclude_system_comments

    def generate_vsts_url(self, repository_id, pull_request_id):
        '''
        returns the url
        '''
        '''todo:upgrade to modern string format'''
        get_comments_url = ("%s/DefaultCollection/_apis/git/repositories/%s/pullRequests/%s/threads?api-version=%s")%(self._vsts.instance, repository_id, pull_request_id, self.vsts_api.api_version)
        print(get_comments_url)
        return get_comments_url

    def get_pull_request_ids(self, project_name):
        """
        from neo4j get all of the pull request id's for a given project.
        """
        graph = GraphBuilder().GetNewGraph()
        qry = '''MATCH (pr:PullRequest)-[]-
                 (r:Repository)-[]-(p:Project{{Name:"{}"}})
                 RETURN pr.Id as Id'''.format(project_name)
        print(qry)
        raw_pull_request_ids = list(graph.run(qry))
        ids = []
        for item in raw_pull_request_ids:
            ids.append(item.get("Id"))
        #freeing up memory, not sure if this is very pythonic or not.
        raw_pull_request_ids = None
        return ids


    def crawl(self, pull_request_id):
        '''
        Crawls the comments and puts them in Neo4J
        '''
        graph = GraphBuilder().GetNewGraph()
        pull_request = PullRequest.select(graph, pull_request_id).first()
        for repo in pull_request.ForRepository:
            self.copy_over_comments(repo.Id, pull_request)
        print("finished adding comments")

    def make_comment_node(self, vsts_data, thread_id, graph, url):
        '''
        make a node so we can link things to and later save
        '''
        raw_id = vsts_data.get('id')
        if raw_id is None:
            print("comment was not added id could not be generated")
            return None

        comment = Comment.select(graph, raw_id).first()
        if comment is None:
            comment = Comment()
        comment.Id = comment.get_id(raw_id, thread_id)
        if "commentType" in vsts_data:
            comment.CommentType = vsts_data.get("commentType", "")
        comment.Content = vsts_data.get("content", "")
        comment.LastContentUpdatedDate = vsts_data.get("lastContentUpdatedDate", "")
        comment.LastUpdatedDate = vsts_data.get("lastUpdatedDate", "")
        comment.PublishedDate = vsts_data.get("publishedDate", "")
        comment.Url = url
        return comment

    def make_thread_node(self, vsts_data, graph):
        '''
        Pull Request comments are stored in threads
        this builds a thread node
        '''
        thread_id = vsts_data.get("id")
        thread = PullRequestThread.select(graph, thread_id).first()
        if thread is None:
            thread = PullRequestThread()

        thread.Id = vsts_data.get("id")
        thread.IsDeleted = vsts_data.get("isDeleted", "")
        thread.Status = vsts_data.get("status")
        ctx = vsts_data.get("threadContext")
        if ctx is not None:
            thread.FilePath = ctx.get("filePath")
        return thread


    def save_comment(self, comment, graph):
        '''
        save the pull request and all the linked nodes to neo4J
        '''
        print("     Saving Comment " + str(comment.Id))
        transaction = graph.begin()
        transaction.merge(comment)
        transaction.graph.push(comment)

    def link_to_parent_comment(self, comment, vsts_data, thread_id, graph):
        '''
        link to parent comment
        '''
        parent_id = vsts_data.get("parentCommentId", "0")
        if parent_id == 0:
            return
        else:
            parent = list(Comment.select(graph, thread_id))
            parent_comment = {}
            if parent:
                comment.ParentComment.add(parent[0])
            else:
                parent_comment = Comment()
                parent_comment.Id = comment.get_id(parent_id, thread_id)
                comment.ParentComment.add(parent_comment)

    def link_to_author(self, comment, vsts_data, graph):
        '''
        Link to Author
        '''
        author_id = vsts_data.get("author").get("id")
        author = Person.select(graph, author_id).first()
        if author is None:
            author = Person()
            author.Id = author_id
        comment.Author.add(author)

    def get_vsts_comments(self, url):
        '''
        Make the call to VSTS and return a dictionary of data
        '''
        data = self.vsts_api.make_request(url)
        return data


    def is_user_comment(self, vsts_comment_data):
        '''
        There are more system comments than user comments
        To filter out system comments use this method in your logic to prevent them from saving
        '''
        result = False
        if vsts_comment_data.get("commentType") == "text":
            result = True
        return result

    def copy_over_comments(self, repository_id, pull_request):
        '''
        Copy VSTS Comments to VSTS
        '''
        print("adding comments for pull_request_id" + str(pull_request.Id))
        url = self.generate_vsts_url(repository_id, pull_request.Id)
        data = self.get_vsts_comments(url)
        if data is None:
            logging.warning("no comments from vsts for pull request " + pull_request.Id)
            return

        for item in data["value"]:
            graph = GraphBuilder().GetNewGraph()
            #vsts comment thread not python thread
            thread = self.make_thread_node(item, graph)
            print("working thread " + str(thread.Id))
            for raw_comment in item.get("comments"):
                if self.exclude_system_comments and not self.is_user_comment(raw_comment):
                    continue
                else:
                    thread.PartOf.add(pull_request)
                    comment = self.make_comment_node(raw_comment, thread.Id, graph, url)
                    print("saving comment " + str(comment.Id))
                    graph.merge(comment)
                    print("saved comment " + str(comment.Id))
                    #this should save the therad too
                    comment.PartOf.add(thread)
                    self.link_to_parent_comment(comment, raw_comment, thread.Id, graph)
                    self.link_to_author(comment, raw_comment, graph)
                    graph.push(comment)
                    print("added links for comment " + str(comment.Id))

    def crawl_by_project(self, project_name):
        """
        Helps with multithreaded execution to crawl by project.
        """
        pull_ids = self.get_pull_request_ids(project_name)
        for pull_id in pull_ids:
            self.crawl(pull_id)

if __name__ == '__main__':
    print("starting Comments")
    print("Threads will not be saved if there are no user comments")
    #set to false for easier debugging, but it is slower
    RUN_MULTI_THREADED = False

    #logging.basicConfig(filename='logs/comments_runner.log', level=logging.WARNING)
    GRAPH = GraphBuilder()
    GRAPH.create_unique_constraints()
    VSTS = VstsInfo(None, None)
    WORKER = CommentsWorker(VSTS)

    if RUN_MULTI_THREADED:
        with Pool(5) as p:
            p.map(WORKER.crawl_by_project, VSTS.project_whitelist)
    else:
        for proj in VSTS.project_whitelist:
            WORKER.crawl_by_project(proj)
