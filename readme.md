# VSTS to Neo4J 

Extracts data from VSTS then saves the data in Neo4j with helpful relationships.

## Security

Do not check in your config file.  The .gitignore file is set to ignore .cfg files.


# Getting Started

# Install Neo4J

Download and install Neo4J

Install apoc into Neo4J. (Download and the apoc jar file in the plugins folder of Neo4J. If the plugins folder does not exist, just create it in the root of your database folder eg: logs, plugins, schema)

## Make default.cfg

In the code folder, rename the default_cfg.txt file to default.cfg and change the values.

## Pip

pip install py2neo

## Run the Scripts
```
  python ProjectsTeamsUsers.py
  python Repositories.py
  python PullRequests.py
  python Comments.py
  python WorkItems.py
  python WorkItemLinks.py
  python PostProcessingCmds.py
```
## Few Queries

Note: Must run the post processing commands first to create the CreatedTimestamp fields.

Note: 1514764800000 is Jan 1st 2018


Total Count of Pull Requests Created this year
```
  MATCH (n:PullRequest)
  WHERE n.CreatedTimestamp > 1514764800000
  RETURN count(n)
```

Total Count of Pull Requests by Project since 2018
```
  MATCH (n:PullRequest)-[r1]-(repo:Repository)-[r2]-(p:Project{Name:'Oystertoad'})
  WHERE n.CreatedTimestamp > 1514764800000
  RETURN count(n)
```

List of developers accociated with a pull request since 2018 (by project)
```
  MATCH (d:Person)-[r3]-(n:PullRequest)-[r1]-(repo:Repository)-[r2]-(p:Project{Name:'Oystertoad'})
  WHERE n.CreatedTimestamp > 1514764800000
  RETURN distinct d.Name
```

List of developers who created a pull request since 2018 (by project)
```
  MATCH (d:Person)-[r3:CREATED_BY]-(n:PullRequest)-[r1]-(repo:Repository)-[r2]-(p:Project{Name:'Oystertoad'})
  WHERE n.CreatedTimestamp > 1514764800000
  RETURN distinct d.Name
```

List of developers who reviewed pull requests since 2018 (by project)
```
  MATCH (d:Person)-[r3:REVIEWED_BY]-(n:PullRequest)-[r1]-(repo:Repository)-[r2]-(p:Project{Name:'Oystertoad'})
  WHERE n.CreatedTimestamp > 1514764800000
  RETURN distinct d.Name
```

Count of Comments by User for the past 365 days

```
  WITH apoc.date.add(timestamp(),"ms", -365, 'd') as PastDate
  Match (u:Person)
  Optional Match (u)-[:AUTHOR]-(c:Comment)
  WHERE c.PublishedTimestamp >= PastDate
  RETURN count(c) as numberOfComments, u.Name as CodeReviewer
  ORDER BY numberOfComments
```

Dump all comments made over the past year
```
  WITH apoc.date.add(timestamp(),"ms", -365, 'd') as PastDate
  Match (u:Developer)
  Optional Match (u)-[:AUTHOR]-(c:Comment)
  WHERE c.PublishedTimestamp >= PastDate
  RETURN u.Name as CodeReviewer, c.Id, c.Content, c.PublishedTimestamp as PTimestamp
```
