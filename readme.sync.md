# Syncing code between two VSTS Projects

This is a quick addon, really not part of the VSTS Neo4j work, but I had a quick need and using the existing VSTS connection info and classes made life easy.

You need to create the default.cfg file, see the readme.md file

Then run SyncRepos.py

You do not need to install Py2Neo for this to work.

## Initial Flow

User logs onto AzureDevOps on Server1, does a repo import. Now Server1 will be the primary data source for what repos are updated.

The SyncRepos.py, runs on Server1 on a daily schedule and does it's thing.

(Note: since 

## Use case

In a world, where a team has two on prems versions of AzureDevOps, behind firewalls and only Server2 public IP Addresses ...

### Use Case

A repo on Server2 updates, when the script runs, the repo on Server1 should have all the updates.

### Use Case

When a new repo is created on Server2, Server1 needs to know about it. This will be a manual process see Initial Flow.

