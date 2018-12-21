# VSTS to Neo4J 

Extracts data from VSTS then saves the data in Neo4j with helpful relationships.

## Security

Do not check in your config file.  The .gitignore file is set to ignore .cfg files.


# Getting Started

# Install Neo4J

Download and install Neo4J

## Make default.cfg

In the code folder, rename the default_cfg.txt file to default.cfg and change the values.

## Pip

pip install py2neo

## Run the Scripts

python ProjectsTeamsUsers.py
python Repositories.py
python PullRequests.py
python Comments.py
python WorkItems.py
python WorkItemLinks.py
python PostProcessingCmds.py

