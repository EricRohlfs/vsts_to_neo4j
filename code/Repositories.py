'''
Repositories.py
From VSTS get the list of code repositories so we can
later crawl and link up pull request info and comments.
'''

# import logging
import configparser
from multiprocessing import Pool
from VSTSInfo import VstsInfo
# from models import GraphBuilder, Repository, Project

class RepositoriesWorker(object):
    """
    Gets the repository info from VSTS
    """

    def __init__(self, request_info, vsts):
        self.instance = vsts.instance
        self.api_version = vsts.api_version
        self.headers = vsts.get_request_headers()
        self.vsts = vsts

    def build_url(self, project_name):
        """
        Returns the url fragment for the list of repositories
        """
        url = ("%s/DefaultCollection/%s/_apis/git/repositories?api-version=%s" % (self.instance, project_name, self.api_version))
        return url


    def crawl(self, project_name):
        """
        Gets Repositories for a given project
        """
        url = self.build_url(project_name)
        data = self.vsts.make_request(url)

        for r in data["value"]:
            graph = GraphBuilder().GetNewGraph()
            #print(r["id"])
            repo = Repository()
            repo.Id = r.get("id")
            repo.Name = r.get("name")
            repo.Url = r.get("url")

            raw_proj = r.get("project")
            proj = Project()
            proj.Id = raw_proj.get("id")
            proj.Name = raw_proj.get("name")
            proj.Url = raw_proj.get("url")

            repo_proj = Project.select(graph, proj.Id)
            '''todo: may not need to do this.'''
            if repo_proj is not None:
                proj_tx = graph.begin()
                proj_tx.create(proj)
                proj_tx.commit()

            repo.BelongsTo.add(proj)
            print("Adding Repo: ")
            print(repo.Name)
            transaction = graph.begin()
            transaction.merge(repo)
            transaction.graph.push(repo)
        print("Finished mapping repos")


"""
if __name__ == '__main__':
    print("starting Repositories Crawl")
    #set to false for easier debugging, but it is slower
    run_multithreaded = True

    GRAPH = GraphBuilder()
    GRAPH.create_unique_constraints()

    #If you feel your cache is up to date, then set ignore_cache to False.
    VSTS = VstsInfo(None, None, ignore_cache=True)
    PULL_REQUEST_STATUS = "Completed"
    WORKER = RepositoriesWorker(VSTS.get_request_settings(), VSTS)

    if run_multithreaded:
        with Pool(5) as p:
            p.map(WORKER.crawl, VSTS.project_whitelist)
    else:
        for proj in VSTS.project_whitelist:
            WORKER.crawl(proj)
"""