#!/bin/bash

DB_CONTAINER=docker-db-1
DB_NAME=patents_db
DB_USER=postgres

# Load granted claims data into the database from 1976 to 2007

YEAR_START=1976
YEAR_END=2007

for (( year=$YEAR_START; year<=$YEAR_END; year++ )); do
  file="/srv/cmmi/home/thomvray/data/granted_claims/g_claims_${year}.tsv"
  if [ -f "$file" ]; then
    echo "Loading $file..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME \
      -c "\copy claims FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\t')" < "$file"
  
  file_pg="/srv/cmmi/home/thomvray/data/PRE-Granted/pg_claims_${year}.tsv.gz"
  if [ -f "$file_pg" ]; then
    echo "Loading $file_pg..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME \
      -c "\copy claims FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\t')" < "$file_pg"
  fi
done