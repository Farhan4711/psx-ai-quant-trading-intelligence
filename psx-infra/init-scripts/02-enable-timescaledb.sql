-- Enable TimescaleDB extension on every application database.
-- This runs once on first container startup via docker-entrypoint-initdb.d.
-- Alembic migrations will call create_hypertable() per-table later.

\connect psx_dev
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

\connect psx_test
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Staging / prod databases are created by the app migration on first deploy.
-- Their TimescaleDB extension is enabled in the Alembic initial migration.
