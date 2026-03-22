# Staging

BioNexus staging contains the relational and graph stores used by the gateway and intelligence layers.

- Postgres keeps the refined `silver` schema keyed by UniProt ID.
- Neo4j keeps `Gene`, `Disease`, `Medicine`, and `Pathway` nodes with a Gene-first graph contract.
- `db_check.py` audits schema drift and cross-store UniProt integrity.
- `seed.py` provides a deterministic local Gene-Disease-Medicine triplet for smoke tests.
