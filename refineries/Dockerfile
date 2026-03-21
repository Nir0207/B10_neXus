# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps only in this layer so the final image stays lean
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="BioNexus Refinery"
LABEL org.opencontainers.image.description="Polars ETL pipeline: Bronze JSON → Silver CSVs → Postgres / Neo4j"

# Non-root user for safety
RUN useradd --create-home --uid 1001 refinery
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source (no venv, no tests, no .processed_manifest)
COPY config.py idempotency.py refine_uniprot.py refine_ncbi.py \
     load_postgres.py load_neo4j.py run_pipeline.py ./

# Data lake mounts (host volumes at runtime)
RUN mkdir -p /data_lake/raw/uniprot /data_lake/raw/ncbi /data_lake/silver \
    && chown -R refinery:refinery /data_lake /app

USER refinery

# Env defaults (overridable in docker-compose / --env-file)
ENV RAW_ROOT_DIR=/data_lake/raw \
    SILVER_DIR=/data_lake/silver \
    MANIFEST_PATH=/data_lake/silver/.processed_manifest.json \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Default: run the full pipeline (idempotent).
# Override CMD to run individual stages or pytest.
ENTRYPOINT ["python"]
CMD ["run_pipeline.py"]
