# ADR-002: Why TimescaleDB for Time-Series Data

**Date:** 2026-05-07
**Status:** Accepted

---

## Context

The application stores and queries large volumes of time-series data: OHLCV prices (~500 symbols × 250 trading days × 5 years = ~625,000 rows to start, growing daily), technical indicator values, macro indicators, sentiment scores, and model features. Query patterns are time-range-heavy: "give me the last 60 days of closes for ENGRO."

Options considered:

1. **Plain PostgreSQL** — just add a date index and query normally
2. **TimescaleDB** (chosen) — PostgreSQL extension that adds hypertables and time-series optimizations
3. **InfluxDB** — purpose-built time-series DB
4. **ClickHouse** — OLAP-oriented columnar database

## Decision

Use **TimescaleDB** as a PostgreSQL extension. All time-series tables are created as hypertables via `create_hypertable()`.

## Rationale

| Concern | Plain Postgres | TimescaleDB | InfluxDB | ClickHouse |
|---|---|---|---|---|
| Time-range query performance | Degrades at scale | Excellent (chunk pruning) | Excellent | Excellent |
| Familiar SQL | Yes | Yes (it IS Postgres) | No (Flux/InfluxQL) | Mostly |
| JOIN with relational data | Native | Native | Hard | Harder |
| Single infrastructure component | Yes | Yes (same Postgres) | No (separate service) | No |
| Continuous aggregates (OHLCV rollups) | Manual | Built-in | Built-in | Manual |
| Managed hosting for later | Timescale Cloud | Same | InfluxDB Cloud | ClickHouse Cloud |
| Operational complexity | Low | Low | Medium | Medium |

The key insight: **TimescaleDB is just a Postgres extension**. The team already knows SQL. Migrations use Alembic. JOINs between `ohlcv_daily` and `securities` or `transactions` are native. There is no operational split-brain.

## Consequences

- PostgreSQL container must load the TimescaleDB extension: `CREATE EXTENSION IF NOT EXISTS timescaledb;`
- Every time-series table must be converted to a hypertable immediately after creation: `SELECT create_hypertable('table_name', 'time_column');`
- Alembic migration for hypertable creation must call `op.execute("SELECT create_hypertable(...)")` — SQLAlchemy alone cannot do this
- TimescaleDB's `time_bucket()` function replaces `date_trunc()` for aggregation queries — use it
- Self-managed on Hetzner in Phase 0–3; migrate to Timescale Cloud if operational burden becomes high
