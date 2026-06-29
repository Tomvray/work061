#!/bin/bash

DB_CONTAINER=docker-db-1
DB_NAME=patents_db
DB_USER=postgres

docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "\copy office_actions FROM STDIN WITH (FORMAT csv, HEADER true)" < ../data/oa/office_actions.csv
docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "\copy citations FROM STDIN WITH (FORMAT csv, HEADER true)" < ../data/oa/citations.csv