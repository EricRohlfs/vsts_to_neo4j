"""
Adds extra goodness to the Neo4j data model after the data has been imported.
"""
from models import GraphBuilder
import os
import configparser

class PostProcessingCommands(object):
    """
    Adds extra goodness to the Neo4j data model after the data has been imported.
    """

    def __init__(self):
        """
        class init
        """
        self.graph = GraphBuilder().GetNewGraph()
        self.config = configparser.ConfigParser()
        self.config.read_file(open('default.cfg'))

    @property
    def developer_names(self):
        """
        List of developers to add a label for in Neo4j
        """
        devs = self.config['DEFAULT']['developer_names'].replace('"', '').replace("\r", '').replace("\n", '').split(",")
        return devs

    @property
    def data_developers(self):
        devs = self.config['DEFAULT']['database_developers'].replace('"', '').replace("\r", '').replace("\n", '').split(",")
        return devs

    def add_bug_label(self):
        """
        Finds work items of type bug and adds the label of bug.
        This makes it easier to query and also visualize the various work item types.
        """
        qry = """MATCH (b:WorkItem{WorkItemType:'Bug'})
                set b :Bug
                return count(b)"""
        self.graph.run(qry)
        print("Added Bug label to work items")

    def add_user_story_label(self):
        """
        Finds work items of type User Story and adds the label of UserStory.
        This makes it easier to query and also visualize the various work item types.
        """
        qry = """MATCH (n:WorkItem{WorkItemType:'User Story'})
                set n :UserStory
                return count(n)"""
        self.graph.run(qry)
        print("Added User Story label to work items")

    def add_tasks_label(self):
        """
        Finds work items of type Task and adds the label of Task.
        This makes it easier to query and also visualize the various work item types.
        """
        qry = """MATCH (n:WorkItem{WorkItemType:'Task'})
                set n :Task
                return count(n)"""
        self.graph.run(qry)
        print("Added Task label to work items")

    def add_created_timestamp(self):
        """
        Finds all nodes with a CreatedDate and adds a CreatedTimestap
        """
        qry = """MATCH (n)
                Where exists( n.CreatedDate)
                set n.CreatedTimestamp = apoc.date.parse(left(replace(n.CreatedDate,"T"," "),19),"ms","yyyy-MM-dd HH:mm:ss")
                return count(n) as n"""
        result = self.graph.evaluate(qry)
        print("Added CreatedTimestamps: Records Changed: {}".format(result))

    def add_creation_timestamp(self):
        """
        creation instead of created, but sticks with the CreatedTimestamp vs CreationTimestap
        Finds all nodes with a Creation and adds a CreatedTimestap
        """
        qry = """MATCH (n)
                Where exists( n.CreationDate)
                set n.CreatedTimestamp = apoc.date.parse(left(replace(n.CreationDate,"T"," "),19),"ms","yyyy-MM-dd HH:mm:ss")
                return count(n) as n"""
        result = self.graph.evaluate(qry)
        print("Added CreatedTimestamps for CreationDate: Records Changed: {}".format(result))

    def add_closed_timestamp(self):
        """
        Finds all nodes with a ClosedDate and adds a ClosedTimestap
        """
        qry = """MATCH (n)
                Where exists( n.ClosedDate)
                set n.ClosedTimestamp = apoc.date.parse(left(replace(n.ClosedDate,"T"," "),19),"ms","yyyy-MM-dd HH:mm:ss")
                return count(n)"""
        result = self.graph.evaluate(qry)
        print("Added ClosedTimestamps: Records Changed: {}".format(result))

    def add_published_timestamp(self):
        """
        Finds all nodes with a PublishedDate and adds a PublishedTimestap
        """
        qry = """MATCH (n)
                Where exists( n.PublishedDate)
                set n.PublishedTimestamp = apoc.date.parse(left(replace(n.PublishedDate,"T"," "),19),"ms","yyyy-MM-dd HH:mm:ss")
                return count(n)"""
        result = self.graph.evaluate(qry)
        print("Added PublishedTimestap: Records Changed: {}".format(result))


    def add_developer_label(self):
        """
        Given a list of names adds a label of dev
        """
        developer_names = self.developer_names
        for dev in developer_names:
            qry = """MATCH (n:Person{{Name:"{}"}})
                    set n :Developer
                    """.format(dev)
            self.graph.run(qry)
        print("Added Developers labels to devlist")

    def add_database_developer_label(self):
        """
        Given a list of names adds a label of dev
        """

        for dev in self.data_developers:
            qry = """MATCH (n:Person{{Name:"{}"}})
                    set n :DatabaseDev
                    """.format(dev)
            self.graph.run(qry)
        print("Added Developers labels to devlist")

    def run_all_commands(self):
        """
        Runs all the commands
        """
        print("Executing post processing commands")
        self.add_developer_label()
        self.add_database_developer_label()
        self.add_bug_label()
        self.add_user_story_label()
        self.add_tasks_label()
        self.add_created_timestamp()
        self.add_creation_timestamp()
        self.add_closed_timestamp()
        self.add_published_timestamp()
        print("Finished running post processing commands")

if __name__ == '__main__':
    CMDS = PostProcessingCommands()
    CMDS.run_all_commands()
