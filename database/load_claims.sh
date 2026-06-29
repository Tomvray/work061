#!/bin/bash

DB_CONTAINER=docker-db-1
DB_NAME=patents_db
DB_USER=postgres

for file in ../data/granted_claims/*.tsv; do
  echo "Loading $file..."
  docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME \
    -c "\copy claims FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\t')" < "$file"
done