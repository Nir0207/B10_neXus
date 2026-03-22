# BioNexus Environment Setup

This checklist is for a new developer who has just cloned the repository.

It does not include any secret values. Fill in your own local values.

## Files To Create

Create these two files first:

1. Copy [`.env.example`](/BioNexus/.env.example) to `.env`
2. Copy [`refineries/.env.example`](/BioNexus/refineries/.env.example) to `refineries/.env`

## Root `.env`

These are the main keys a new user should set.

### Required

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `MONGODB_USER`
- `MONGODB_PASSWORD`
- `MONGODB_DATABASE`
- `TELEMETRY_ADMIN_USERNAME`
- `TELEMETRY_ADMIN_PASSWORD`
- `TELEMETRY_ADMIN_EMAIL`
- `TELEMETRY_ADMIN_FULL_NAME`
- `SECRET_KEY`
- `JWT_ISSUER`
- `JWT_AUDIENCE`

### Usually Set For Local Development

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `NEO4J_HOST`
- `NEO4J_BOLT_PORT`
- `NEO4J_HTTP_PORT`
- `MONGODB_HOST`
- `MONGODB_PORT`
- `TELEMETRY_PORT`
- `TELEMETRY_GRAPHQL_URL`
- `NEXT_PUBLIC_TELEMETRY_API_URL`

### Optional

- `DUCKDB_PATH`
- `LAKE_DIRECTORY`
- `SILVER_DIRECTORY`
- `NCBI_API_URL`
- `OPEN_TARGETS_API`
- `UNIPROT_API`
- `REACTOME_API`
- `BIOGRID_API`
- `CHEMBL_API`
- `BATCH_SIZE`
- `CHUNK_SIZE`
- `PARQUET_COMPRESSION`
- `PARTITION_BY_DATE`
- `DEBUG`
- `LOG_LEVEL`
- `ENV`

## `refineries/.env`

### Required

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `NEO4J_PASSWORD`

### Optional

- `FORCE`
- `SKIP_POSTGRES`
- `SKIP_NEO4J`

## Variables Usually Supplied By Compose

These are already wired by the repo’s compose files in the normal local setup. You only need to set them yourself if you want to override behavior.

### Ops / OpenObserve

- `OPENOBSERVE_BASE_URL`
- `OPENOBSERVE_ORG`
- `OPENOBSERVE_USERNAME`
- `OPENOBSERVE_PASSWORD`
- `OPENOBSERVE_LOG_STREAM`
- `OPENOBSERVE_DASHBOARD_TITLE`
- `OPENOBSERVE_TIMEOUT_SECONDS`
- `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_EXPORTER_OTLP_HEADERS`
- `OTEL_COLLECTOR_HOST`
- `OTEL_COLLECTOR_GRPC_PORT`
- `OTEL_COLLECTOR_HTTP_PORT`

### API Gateway

- `POSTGRES_URL`
- `NEO4J_URI`
- `TELEMETRY_GRAPHQL_URL`
- `INTELLIGENCE_API_URL`
- `GATEWAY_ADMIN_USERNAME`
- `GATEWAY_ADMIN_PASSWORD`
- `GATEWAY_ADMIN_PASSWORD_HASH`
- `BIONEXUS_API_URL`
- `CORS_ALLOW_ORIGINS`

### UI Portal

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_TELEMETRY_API_URL`
- `NEXT_PUBLIC_BIONEXUS_API_TOKEN`

### Intelligence

- `PG_DSN`
- `OLLAMA_HOST`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_TRANSPORT`
- `RAG_SNIPPET_LIMIT`
- `PATHWAY_LIMIT`
- `OT_EVIDENCE_PATH`
- `STUDY_CSV_PATH`

## Recommended Secret Checklist

For a clean local setup, generate or choose values for:

- `POSTGRES_PASSWORD`
- `NEO4J_PASSWORD`
- `MONGODB_PASSWORD`
- `TELEMETRY_ADMIN_PASSWORD`
- `SECRET_KEY`

If you want to override the default ops login, also define:

- `OPENOBSERVE_USERNAME`
- `OPENOBSERVE_PASSWORD`

## Notes

- Keep `.env` and `refineries/.env` out of version control.
- The current README startup order stays the source of truth for which stacks to run first.
- If you change database passwords after Docker volumes already exist, you may need to recreate those volumes or update the credentials inside the running services.
