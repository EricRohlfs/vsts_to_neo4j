'''
ProjectsTeamUsers.py
Crawls VSTS Project data.
Adds the project teams.
Adds users and connects them to their teams.
'''

from multiprocessing import Pool
from VSTSInfo import VstsInfo
from models import GraphBuilder, Project, Team, Person

class ProjectsTeamsUsersWorker(object):
    """
    :param array project_whitelist:
         Array of Project Names ['Project1','Project2"]
    """
    def __init__(self, request_info, project_whitelist, vsts):
        self.instance = request_info["instance"]
        self.project = request_info["project_name"]
        self.api_version = request_info["api_version"]
        self.headers = request_info["headers"]
        self.project_whitelist = project_whitelist
        self.vsts = vsts

    def get_vsts_projects_url(self):
        """
        :return: url
        """
        url = ("%s/DefaultCollection/_apis/projects?api-version=%s"
               % (self.instance, self.api_version))
        return url

    def get_vsts_teams_url(self, project_id):
        """
        :return: url
        """
        url = ("%s/DefaultCollection/_apis/projects/%s/teams?api-version=%s"
               % (self.instance, project_id, self.api_version))
        return url

    def get_vsts_team_membership_url(self, project_id, team_id):
        """
        :return: url
        """
        url = ("%s/DefaultCollection/_apis/projects/%s/teams/%s/members?api-version=%s"
               % (self.instance, project_id, team_id, self.api_version))
        return url

    def add_users_to_repo(self, project, team, graph):
        """
        adds users to Neo4j
        """
        url = self.get_vsts_team_membership_url(project.Id, team.Id)
        print("Users Url:")
        print(url)
        users = self.vsts.make_request(url)

        for item in users["value"]:
            #we don't want system users
            if item.get('isContainer', False):
                print("skipped system user")
                continue

            user = Person()
            user.Id = item.get("id")
            user.Name = item.get("displayName")
            user.Url = item.get("url")
            user.UniqueName = item.get("uniqueName")
            user.MemberOf.add(team)
            print("Adding User")
            transaction = graph.begin()
            transaction.merge(user)
            transaction.graph.push(user)

    def add_teams_to_repo(self, project, graph):
        """
        :param GraphObject project:
            Filled out Neo4j project object
        """
        url = self.get_vsts_teams_url(project.Id)
        print(url)
        teams = self.vsts.make_request(url)

        for item in teams["value"]:
            team = Team()
            team.Id = item.get("id")
            team.Name = item.get("name")
            #team.Description = item["description"]
            team.PartOf.add(project)
            print("Adding Team")
            transaction = graph.begin()
            transaction.merge(team)
            transaction.graph.push(team)
            self.add_users_to_repo(project, team, graph)

    def map_and_save_project(self, raw_data, graph):
        """
        :param json raw_data:
            raw vsts project data
        :param Graph graph:
            py2neo graph
        """
        if raw_data["name"] in self.project_whitelist:
            proj = Project()
            proj.Id = raw_data.get("id")
            proj.Name = raw_data.get("name")
            #proj.Description = item["description"]
            proj.Revision = raw_data.get("revision")
            print("Adding Project")
            graph.create(proj)
            return proj

    def add_projects_to_repo(self, projects, graph):
        """
        Saves project data to Neo4j
        """
        for project in projects:
            if project["name"] in self.project_whitelist:
                self.map_and_save_project(project, graph)
                self.add_teams_to_repo(project, graph)
        return

    def crawl(self, raw_data):
        """
        starts doing the crawling work
        """
        graph = GraphBuilder().GetNewGraph()
        proj = self.map_and_save_project(raw_data, graph)
        if proj is not None:
            self.add_teams_to_repo(proj, graph)
        print("Finished Adding Projects Teams and Users")

if __name__ == '__main__':
    print("starting PullRequests")
    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = True

    GRAPH = GraphBuilder()
    GRAPH.create_unique_constraints()

    VSTS = VstsInfo(None, None)

    #tod clean up this signature mess and just pass in VSTS
    WORKER = ProjectsTeamsUsersWorker(VSTS.get_request_settings(), VSTS.project_whitelist, VSTS)
    PROJECTS_URL = WORKER.get_vsts_projects_url()
    RAW = WORKER.vsts.make_request(PROJECTS_URL)
    PROJECTS = RAW["value"]

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(WORKER.crawl, PROJECTS)
    else:
        for PROJ in PROJECTS:
            WORKER.crawl(PROJ)
