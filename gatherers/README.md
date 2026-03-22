# Gatherers

BioNexus gatherers fetch raw upstream payloads into the local data lake.

- All gatherers inherit from `BaseGatherer`.
- Raw payloads are partitioned under `Lake/data_lake/raw/<source>/date=YYYY-MM-DD/organ=<organ>/`.
- Retries, timeout handling, and circuit breaker behavior are centralized in `base.py`.
- Tests live in `gatherers/tests/` and mock upstream API responses per gatherer.
