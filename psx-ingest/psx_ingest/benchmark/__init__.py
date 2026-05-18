"""
Anonymous peer-benchmark aggregation.

Runs nightly, computes per-bucket aggregates from all opted-in users,
and writes them to `peer_aggregates`. The read path
(`psx_api/services/benchmark_service.py`) checks
`sample_count >= MIN_BUCKET_SAMPLES` (=5) before returning anything,
so a bucket with too few members is suppressed entirely.

Bucketing rules live in `psx_api/benchmark/buckets.py` to keep one
source of truth; this module duplicates ONLY the bucket-string logic
because importing psx-api into psx-ingest crosses a service boundary.
"""
