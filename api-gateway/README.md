# API Gateway

BioNexus API Gateway exposes authenticated read APIs over Postgres and Neo4j.

- JWTs include issuer, audience, expiry, not-before, and admin-aware claims emitted by the telemetry GraphQL service.
- `/token` and `/register` remain for compatibility, but they proxy authentication to the telemetry GraphQL service backed by MongoDB.
- CORS is allowlisted through `CORS_ALLOW_ORIGINS`.
- `/api/v1/genes/{uniprot_id}` resolves the canonical UniProt-backed gene record.
- `/api/v1/discovery/graph` and `/api/v1/discovery/triplets` expose the Gene-Disease-Medicine graph contract used by the UI.
