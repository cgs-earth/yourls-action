#!/bin/bash

mysqldump \
    --databases yourls \
    -u ${MYSQL_ROOT_USER} \
    --password=${MYSQL_ROOT_PASSWORD} \
    --hex-blob \
    --default-character-set=utf8mb4 \
    --skip-triggers \
    --set-gtid-purged=OFF
