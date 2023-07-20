# yourls-action

Populate a YOURLS database via GitHub Actions

# Build

The YOURLS Action is used to populate the YOURLS tables from a filesystem of CSVs.

This container is run during the Github workflow.

### Description

The deployment is intended to run after the creation of a MySQL server with a valid YOURLS schema.

- `mysql` is the Docker build a YOURLS deployment with for MySQL 5.7
- `yourls_action` is the Docker build for the python package supporting the YOURLS population.
- `docker-compose.yml` is the Docker compose setup for the two containers.

### Usage

The basic workflow is to build the containers:

```
docker compose build
```

Then start start MySQL:

```
docker compose up -d mysql
```

Then run the yourls-action container to fill the database:

```
docker run \
    --rm \
    --name yourls-action \
    --network=yourls-action_default \
    --env YOURLS_DB_PASSWORD=${YOURLS_DB_PASSWORD:-arootpassword} \
    --env YOURLS_DB_USER=${YOURLS_DB_USER:-root} \
    --env YOURLS_DB_HOST=${YOURLS_DB_HOST:-mysql} \
    -v ./namespaces:/namespaces \
    yourls-action-yourls
```

Then generate a SQL dump of the database:

```
docker exec mysql sh /dump.sh | gzip > yourls.sql.gz
```