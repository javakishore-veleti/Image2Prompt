#!/bin/bash
# Creates one database per microservice on first container start.
# POSTGRES_USER owns each database.
set -e

databases=(admin_service customer_service image_service)

for db in "${databases[@]}"; do
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE $db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
done
