"""
From a Pull Request Id, gets related work items and saves them
"""
import logging
from multiprocessing import Pool
from VSTSInfo import VstsInfo
from models import GraphBuilder, WorkItem
from py2neo import Relationship, PropertyDict
from WorkItems import PullReqeustWorkItemsWorker

class WorkItemLinksWorker(object):
    """
    Gets work items linked to pull requests and saves them to Neo4j
    """

    def __init__(self, vsts):
        request_info = vsts.get_request_settings()
        self.instance = vsts.instance
        self.api_version = vsts.api_version
        self.headers = vsts.headers
        self.vsts = vsts
        self.vsts_work_item_repo = PullReqeustWorkItemsWorker(request_info, vsts)

    def get_url(self, project_name, work_item_ids=None):
        """
        builds a url
        :param string work_item_ids:
            comma separated list of ids
        """
        url = ("%s/DefaultCollection/%s/_apis/wit/reporting/workItemLinks?api-version=%s" %
               (self.instance,
                project_name,
                self.api_version
               ))
        if work_item_ids is not None:
            url = url + "&ids=" + work_item_ids
        return url

    def crawl_projects(self, projects):
        """
        Just a wrapper for crawl that accepts an array of projects
        """
        for proj in projects:
            self.crawl(proj)

    def crawl(self, project_name, url=None):
        """
        This method will be recursive since we have to follow a url at the end of each request.

        """
        if project_name is None:
            print("ProjectId is needed to link work items")
            return

        if url is None:
            url = self.get_url(project_name)

        data = self.vsts.make_request(url)
        if data is None:
            return
        if "values" not in data:
            logging.info("no work items linked")
            return
        for raw in data["values"]:
            graph = GraphBuilder().GetNewGraph()
            r = self.build_relationship(graph, raw)
            print("adding workitem and relationships")
            graph.create(r)

        if data.get("nextLink"):
            if data.get("isLastBatch"):
                print("reached the end of linked work items for project " + project_name)
                return
            next_url = data["nextLink"]
            self.crawl(project_name, next_url)

    def get_work_item(self, work_item_id, graph):
        """
        Updates workitem data regardless now
        :param string work_item_id:

        """
        if work_item_id is None:
            print("workitem id cannot be none")
            return
        work_item = WorkItem.select(graph, work_item_id).first()
        if work_item is None:
            work_item = WorkItem()
            work_item.Id = str(work_item_id)
            graph.merge(work_item)
        try:
            self.vsts_work_item_repo.fill_in_the_rest(work_item, graph)
        except:
            #Not sure why this happens could be old work items or possibly artifact links
            print("could not get work item from vsts: " + str(work_item.Id))

        graph.push(work_item)
        return work_item

    def parse_link_type(self, full_link_type):
        """
        We don't wat the relationship names to be too long.
        This method strips out the most common names
        """
        names = ["System.LinkTypes.", "Microsoft.VSTS.Common."]
        link_type = full_link_type
        for name in names:
            if full_link_type.startswith(name):
                link_type = full_link_type.replace(name, "")
        return link_type

    def set_link_props(self, link, raw_link):
        """
        Attaches some metadata to the link that helps describe the type of link
        some of the data is redundant, but could help troubleshoot orphaned records.
        """
        props = PropertyDict()
        if raw_link["sourceProjectId"] is not None:
            link["sourceProjectId"] = raw_link["sourceProjectId"]
        if raw_link["targetProjectId"] is not None:
            link["targetProjectId"] = raw_link["targetProjectId"]
        if raw_link["changedDate"] is not None:
            link["changedDate"] = raw_link["changedDate"]
        if raw_link["linkType"] is not None:
            link["fullLinkType"] = raw_link["linkType"]
        
    def build_relationship(self, graph, raw_link):
        """
        finds the source and target work items and links them together
        """
        source = self.get_work_item(raw_link.get("sourceId"), graph)
        target = self.get_work_item(raw_link.get("targetId"), graph)
        link_type = self.parse_link_type(raw_link.get("linkType"))
        link = Relationship(source.__ogm__.node, link_type, target.__ogm__.node)
        self.set_link_props(link, raw_link)
        return link

if __name__ == '__main__':
    print("starting WorkItemLinks")
    #set to false for easier debugging, but it is slower
    RUN_MULTITHREADED = False

    GRAPH = GraphBuilder()
    GRAPH.create_unique_constraints()

    VSTS = VstsInfo(None, None)
    WORKER = WorkItemLinksWorker(VSTS)

    if RUN_MULTITHREADED:
        with Pool(5) as p:
            p.map(WORKER.crawl, VSTS.project_whitelist)
    else:
        WORKER.crawl_projects(VSTS.project_whitelist)
