# YOURLS Action

This is the python package supporting the YOURLS action.

## Description

This folder contains the Python package `yourls-action` as well as the Docker system context to create the corresponding container.

- `yourls_action` is the python package supporting the action. The includes the Command Line Interface and the api manager.
- `Dockerfile` is the Docker build context for a container running yourls-action.

### Usage

The yourls-action cannot run in isolation and has to be able to connect MySQL.
This can be done by running both containers inside of docker compose.

The basic command to use the yourls-action CLI is:

```
yourls-action run /path/to/directory
```
