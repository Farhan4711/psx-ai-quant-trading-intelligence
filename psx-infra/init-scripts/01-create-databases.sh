#!/usr/bin/env bash
# Creates multiple databases on first container startup.
# The POSTGRES_MULTIPLE_DATABASES env var is a comma-separated list.
# This script is mounted at /docker-entrypoint-initdb.d/ and runs once.

set -euo pipefail

create_database() {
    local db_name="$1"
    echo "Creating database: ${db_name}"
    psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" <<-EOSQL
        CREATE DATABASE "${db_name}";
        GRANT ALL PRIVILEGES ON DATABASE "${db_name}" TO "${POSTGRES_USER}";
EOSQL
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "Multiple databases requested: ${POSTGRES_MULTIPLE_DATABASES}"
    for db in $(echo "${POSTGRES_MULTIPLE_DATABASES}" | tr ',' ' '); do
        create_database "${db}"
    done
    echo "All databases created."
fi
