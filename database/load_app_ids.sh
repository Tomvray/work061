DB_CONTAINER=docker-db-1
DB_NAME=patents_db
DB_USER=postgres

docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "\copy applications FROM STDIN WITH (FORMAT csv, HEADER true)" < database/list_apps.csv
