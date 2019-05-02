"""
Syncs repos between two TFS/VSTS/AzureDevOps repos
"""

from multiprocessing import Pool
from ProjectsTeamsUsers import ProjectsTeamsUsersWorker
from Repositories import RepositoriesWorker
from VSTSInfo import VstsInfo

class RepoSync(object):
    """
    RepoSync helps get a list of Repos to later sync
    """

    def add_repo_urls_to_store(self, project_info, store):
        """
        Gets the url for a git clone
        """
        url = REPO_WORKER.build_url(project_info.get("id"))
        repo_data = VSTS.make_request(url)
        for r in repo_data["value"]:
            web_url = r.get("webUrl")
            store.append(web_url)

    def save_repo_urls(self, urls ,filename):
        """
        saves the urls to a file
        """
        with open(filename, 'w') as f:
            for item in urls:
                f.write("%s\n" % item)

    def swap_fqdn(self, repo_list, old_fqdn, new_fqdn):
        """
        swaps out the fqdn's
        """
        changed = []
        for url in repo_list:
            changed.append(url.replace(old_fqdn, new_fqdn))
        return changed

    def make_clone_script(self, repo_list):
        """
        Makes a clone script to run in a batch file
        """
        clone = []
        for url in repo_list:
            cmd = "git clone {0}".format(url)
            clone.append(cmd)
        return clone


if __name__ == '__main__':
    print("starting Repo Sync")
    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = False
    OLD_FQDN = "https://innovasystems.visualstudio.com"
    NEW_FQDN = "https://example.com"

    VSTS = VstsInfo(None, None, ignore_cache=True)

    PTU_WORKER = ProjectsTeamsUsersWorker(VSTS.get_request_settings(), VSTS.project_whitelist, VSTS)
    PROJECTS_URL = PTU_WORKER.get_vsts_projects_url()
    RAW = PTU_WORKER.vsts.make_request(PROJECTS_URL)
    PROJECTS = RAW["value"]

    REPO_WORKER = RepositoriesWorker(VSTS.get_request_settings(), VSTS)

    REPO_SYNC = RepoSync()

    GIT_WEB = []

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(REPO_SYNC.add_repo_urls_to_store, PROJECTS, GIT_WEB)
    else:
        for PROJ in PROJECTS:
            REPO_SYNC.add_repo_urls_to_store(PROJ, GIT_WEB)
    
    REPO_SYNC.save_repo_urls(GIT_WEB, "git_web_urls_original.txt")

    GIT_WEB2 = REPO_SYNC.swap_fqdn(GIT_WEB, OLD_FQDN, NEW_FQDN)
    REPO_SYNC.save_repo_urls(GIT_WEB2, "git_web_urls.txt")

    CLONE = REPO_SYNC.make_clone_script(GIT_WEB2)
    REPO_SYNC.save_repo_urls(CLONE, "git_clone_external.bat")




                
            



