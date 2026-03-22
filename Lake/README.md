# Lake

The BioNexus lake stores immutable raw data and local-first derived artifacts.

- `data_lake/raw/` is the bronze layer fed by gatherers.
- `data_lake/silver/` is the refined output consumed by Postgres and Neo4j loaders.
- `scripts/` contains health and initialization utilities for the local lake stack.
- `tests/` validates lake initialization and structural assumptions.
