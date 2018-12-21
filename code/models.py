'''
Strongly typed models suitable for Neo4J database
'''
import os
import configparser
from py2neo import Graph, Node, Relationship, authenticate, watch
from py2neo.ogm import GraphObject, Property, RelatedTo, RelatedFrom

class GraphBuilder(object):
    '''
    Helper class for connectnios to Neo4J
    '''
    def __init__(self):
        """
        """
        self.config = configparser.ConfigParser()
        self.config.read_file(open("default.cfg"))

    @property
    def neo4j_password(self):
        """
        """
        return self.config['DEFAULT']['neo4j_password']

    @property
    def neo4j_user(self):
        """
        """
        return self.config['DEFAULT']['neo4j_user']

    @property
    def neo4j_url(self):
        """
        """
        return self.config['DEFAULT']['neo4j_url']

    def GetNewGraph(self):
        '''
        Class to new up a graph object so we can makes calls to the database
        '''
        authenticate(self.neo4j_url, self.neo4j_user, self.neo4j_password)
        graph = Graph("http://" + self.neo4j_url)
        return graph

    def create_unique_constraints(self):
        '''
        Half baked helper scrit to generate unique constraints to help
        prevent duplicate items in the Neo4J model
        '''

        graph = self.GetNewGraph()
        try:
            graph.schema.create_uniqueness_constraint("Repository", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Project", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Project", "Name")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("PullRequest", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Person", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Person", "UniqueName")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Branch", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Comment", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("PullRequestThread", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("Team", "Id")
        except:
            print("db constraint already addad")
        try:
            graph.schema.create_uniqueness_constraint("WorkItem", "Id")
        except:
            print("db constraint already addad")

class PullRequest(GraphObject):
    '''
    VSTS Pull request
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "PullRequest"

    Id = Property()
    Title = Property()
    CreationDate = Property()
    ClosedDate = Property()
    Status = Property() #Completed, Abandoned, Active?
    Url = Property()
    #branches could also be links, but starting here
    SourceBranchName = Property()
    TargetBranchName = Property()

    CreatedBy = RelatedTo("Person")
    ReviewedBy = RelatedTo("Person")
    #ForProject = RelatedTo("Project")
    ForRepository = RelatedTo("Repository")
    #LinkedTo = RelatedFrom("WorkItem")

    SourceBranch = RelatedTo("Branch")
    TargetBranch = RelatedTo("Branch")


class Repository(GraphObject):
    '''
    A VSTS GIT repository
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "Repository"

    Id = Property()
    Name = Property()
    Url = Property()

    BelongsTo = RelatedTo("Project")

class Project(GraphObject):
    '''
    VSTS Project
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "Project"

    Id = Property()
    Name = Property()
    Url = Property()
    Description = Property()
    Revision = Property()

class Team(GraphObject):
    __primarykey__ = "Id"
    __primarylabel__ = "Team"

    Id = Property()
    Name = Property()
    Description = Property()
    Url = Property()

    PartOf = RelatedTo("Project")

class Person(GraphObject):
    '''
    Usually a user in the system
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "Person"

    Id = Property()
    Name = Property()
    Url = Property()
    UniqueName = Property()
    Mail = Property()

    MemberOf = RelatedTo("Team")

class Comment(GraphObject):
    '''
    Comment for a PullRequest
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "Comment"

    Id = Property()
    Content = Property()
    PublishedDate = Property()
    LastUpdatedDate = Property()
    LastContentUpdatedDate = Property()
    CommentType = Property()
    Url = Property()

    PartOf = RelatedTo("PullRequestThread")
    ParentComment = RelatedTo("Comment")
    Author = RelatedTo("Person")

    def get_id(self, comment_id, thread_id):
        '''
        need a concat id
        '''
        return str(thread_id) + '_' + str(comment_id)

class PullRequestThread(GraphObject):
    '''
    Comments are part of a thread
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "PullRequestThread"

    Id = Property()
    Status = Property()
    FilePath = Property()
    IsDeleted = Property()
    Url = Property()

    PartOf = RelatedTo("PullRequest")

class Iteration(GraphObject):
    '''
    VSTS Iteration or Sprint
    '''
    __primarykey__ = "Id"
    __primarylabel__ = "Iteration"

    Id = Property()
    Name = Property()
    StartDate = Property()
    EndDate = Property()
    Url = Property()


class Branch(GraphObject):
    """
    Git Branch
    """
    __primarykey__ = "Id"
    __primarylabel__ = "Branch"

    Id = Property()
    Name = Property()
    Url = Property()

    def generate_branch_id(self,repository_name, branch_ref):
        '''
        Because different projects can have the same branch names, we need a better Id
        Call this method to build the id
        '''
        id = repository_name +"/" + branch_ref

class WorkItem(GraphObject):
    """
    VSTS Work item
    """
    __primarykey__ = "Id"
    __primarylabel__ = "WorkItem"

    Id = Property()
    Title = Property()
    Url = Property()
    WorkItemType = Property()
    CreatedDate = Property()
    ValueArea = Property()
    AreaPath = Property()
    IterationPath = Property()
    Creator = Property()
    ProjectName = Property()
    Rev = Property()
    ClosedDate = Property()
    ChangedDate = Property()
    
    #user stories
    StoryPoints = Property()
    Priority = Property()
    Risk = Property()
    ValueArea = Property()

    # tasks
    Activity = Property()
    OriginalEstimate = Property()
    CompletedWork = Property()

    #bugs
    Severity = Property()
    BugFoundInEnvironment = Property()
    BugReason = Property()
    State = Property()

    #risk
    RiskProbability = Property()
    RiskExposure = Property()
    RiskSeverity = Property()

    #issue
    IssueSource = Property()

    LinkedTo = RelatedTo("PullRequest")
    CreatedBy = RelatedTo("Person")
    AssignedTo = RelatedTo("Person")

    # System.TeamProject
    ForProject = RelatedTo("Project")

    #links between workitems to be dynamic


