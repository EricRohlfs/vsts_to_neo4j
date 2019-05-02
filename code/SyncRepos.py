"""
Syncs repos between two TFS/VSTS/AzureDevOps repos
"""

from multiprocessing import Pool
from ProjectsTeamsUsers import ProjectsTeamsUsersWorker
from Repositories import RepositoriesWorker
from VSTSInfo import VstsInfo
import configparser
import os

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

    def make_clone_script(self, repo_list, missing, git_folder_root):
        """
        Makes a clone script to run in a batch file
        """
        clone = []
        for url in repo_list:
            repo_name = self.get_repo_name_from_url(url)
            for missed in missing:
                if missed in url:
                    #where_to_clone = "{0}{1}\\".format(git_folder_root, repo_name)
                    where_to_clone = os.path.join(git_folder_root, repo_name)
                    cmd = 'git clone {0} \"{1}\"'.format(url, where_to_clone)
                    clone.append(cmd)
        return clone

    def get_local_git_repos(self, git_root):
        """
        Crawls a folder, gets the list of folder names
        The folder names should be the same as the repo names
        """
        #repos = [x[0] for x in os.walk(git_root)]
        repos = os.listdir(git_root) 
        return repos

    def get_repo_name_from_url(self, url):
        """
        given a git clone url, get the name of the repo
        """
        full = len(url)
        idx = url.find("_git/") + 5
        name = url[idx:full]
        return name


    def get_missing_local_repos(self, local_folders, repos):
        """
        Compares the list of repo names to local folders and returns the difference 
        """
        repo_names = []
        for url in repos:
            name = self.get_repo_name_from_url(url)
            repo_names.append(name)

        missing = set(repo_names).difference(local_folders)
        return missing

    #def generate_remotes(self, )


if __name__ == '__main__':
    print("starting Repo Sync")

    config = configparser.ConfigParser()
    config.read_file(open('default.cfg'))

    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = config['RepoSync']['RunMultiThreaded']
    RUN_MULTITHREADED = RUN_MULTITHREADED in ['True', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']
    SERVER_NO_IP =  config['RepoSync']['ServerNoIp']
    SERVER_IP = config['RepoSync']['ServerIp']
    GIT_ROOT_FOLDER_PATH = config['RepoSync']['GitRootFolderPath']

    #for this script we always want to ignore the cache
    VSTS = VstsInfo(None, None, ignore_cache=False)

    PTU_WORKER = ProjectsTeamsUsersWorker(VSTS.get_request_settings(), VSTS.project_whitelist, VSTS)
    PROJECTS_URL = PTU_WORKER.get_vsts_projects_url()
    RAW = PTU_WORKER.vsts.make_request(PROJECTS_URL)
    PROJECTS = RAW["value"]

    REPO_WORKER = RepositoriesWorker(VSTS.get_request_settings(), VSTS)

    REPO_SYNC = RepoSync()
    LOCAL_REPOS = REPO_SYNC.get_local_git_repos(GIT_ROOT_FOLDER_PATH)

    REPO_NOIP_STORE = []

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(REPO_SYNC.add_repo_urls_to_store, PROJECTS, REPO_NOIP_STORE)
    else:
        for PROJ in PROJECTS:
            REPO_SYNC.add_repo_urls_to_store(PROJ, REPO_NOIP_STORE)


    LOCAL_MISSING = REPO_SYNC.get_missing_local_repos(LOCAL_REPOS, REPO_NOIP_STORE)
    CLONE_MISSING = REPO_SYNC.make_clone_script(REPO_NOIP_STORE, LOCAL_MISSING, GIT_ROOT_FOLDER_PATH)
    REPO_SYNC.save_repo_urls(CLONE_MISSING, GIT_ROOT_FOLDER_PATH + "\\git_clone_missing.bat")


    #REPO_SYNC.save_repo_urls(REPO_NOIP_STORE, "git_web_urls_original.txt")

    #REPO_IP_STORE = REPO_SYNC.swap_fqdn(REPO_NOIP_STORE, SERVER_NO_IP, SERVER_IP)
    #REPO_SYNC.save_repo_urls(REPO_IP_STORE, "git_web_urls.txt")



                
            



