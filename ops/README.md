# BioNexus Ops Runbook

This folder contains the isolated observability stack for BioNexus:

- `docker-compose.ops.yml`: OpenObserve and the OTel collector
- `otel-config.yaml`: OTLP receivers, processors, and OpenObserve exporters
- `ops_logger.py`: shared Python logger with non-blocking OTel export
- `openobserve_client.py`: query helper for logs
- `check_health.py`: collector reachability check

## Start and Stop

Start the stack:

```bash
./START_OPS.sh
```

This also seeds or updates the `BioNexus Ops` dashboard in OpenObserve.

Stop the stack:

```bash
cd ops
docker compose -f docker-compose.ops.yml down
```

## Portal Access

- URL: `http://localhost:5080`
- Organization: `default`
- Bootstrap email: `root@bionexus.local`
- Bootstrap password: `BioNexusOps123!`

The OpenObserve portal is separate from the BioNexus UI portal at `http://localhost:3000`.

Seed or refresh the dashboard manually:

```bash
python ops/bootstrap_openobserve_assets.py
```

## Read Logs in the Portal

1. Sign in to OpenObserve.
2. Open `Dashboards` and select `BioNexus Ops`, or open `Logs`.
3. Choose stream `bionexus_app`.
4. Set a recent time range.
5. Filter by text or switch to SQL mode.

Direct preset URL:

`http://localhost:5080/web/logs?stream_type=logs&stream=bionexus_app&period=15m&refresh=0&fn_editor=false&defined_schemas=user_defined_schema&org_identifier=default&quick_mode=false&show_histogram=true&logs_visualize_toggle=logs`

Dashboard URL pattern after bootstrap:

`http://localhost:5080/web/dashboards/view?org_identifier=default&dashboard=<dashboard_id>&folder=default&tab=overview&refresh=Off&period=15m&print=false`

Useful queries:

```sql
SELECT * FROM "bionexus_app"
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE service_name = 'gatherers'
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE severity = 'ERROR'
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE gene_context = 'P04637'
ORDER BY _timestamp DESC
LIMIT 50
```

## Read RUM Events

OpenObserve stores browser RUM as structured records in the same log stream.

Use either:

- `RUM` in the OpenObserve sidebar for browser-focused exploration
- `Logs` for raw `rum_*` records

Queries:

```sql
SELECT * FROM "bionexus_app"
WHERE rum_metric_name IS NOT NULL
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE rum_route = '/telemetry'
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE rum_session_id = 'manual-rum-smoke-3'
ORDER BY _timestamp DESC
LIMIT 10
```

## Query Logs by API or Code

Python:

```python
from ops.openobserve_client import OpenObserveClient

client = OpenObserveClient()
print(client.query_logs('SELECT * FROM "bionexus_app" ORDER BY _timestamp DESC LIMIT 10'))
```

MCP:

```text
query_ops_logs('SELECT * FROM "bionexus_app" WHERE severity = ''ERROR'' ORDER BY _timestamp DESC LIMIT 20')
```

Direct API:

```bash
curl -X POST "http://localhost:5080/api/default/_search" \
  -H "Authorization: Basic $(printf 'root@bionexus.local:BioNexusOps123!' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "sql": "SELECT * FROM \"bionexus_app\" ORDER BY _timestamp DESC LIMIT 20",
      "start_time": 0,
      "end_time": 4102444800000000,
      "from": 0,
      "size": 20
    },
    "search_type": "ui",
    "timeout": 0
  }'
```

## Create Additional OpenObserve Users

### Option 1: OpenObserve Portal

1. Sign in as an admin.
2. Open `IAM`.
3. Open the `Users` tab.
4. Click `New user`.

Use this for human users who need portal access.

### Option 2: OpenObserve API

```bash
curl -X POST "http://localhost:5080/api/default/users" \
  -H "Authorization: Basic $(printf 'root@bionexus.local:BioNexusOps123!' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ops-reader@bionexus.local",
    "password": "ChangeMe123!",
    "first_name": "Ops",
    "last_name": "Reader",
    "role": "user"
  }'
```

Use this when you want repeatable setup from scripts.

### Option 3: Service Accounts

Open `IAM` -> `Service Accounts` when a machine or integration needs credentials but no interactive UI login.

## Bootstrap Account Behavior

The root account is initialized from `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD` in `docker-compose.ops.yml`.

That only applies when OpenObserve initializes a fresh data volume. If you already have an `openobserve_data` volume, changing those environment variables will not replace the existing root user.

## Health Check

Run:

```bash
python ops/check_health.py
```

Expected result:

- OTLP gRPC ready on `localhost:4317`
- OTLP HTTP ready on `localhost:4318`

## Runtime Containers to Rebuild After Ops Changes

If you change logger, collector, or RUM behavior, rebuild the affected services:

```bash
docker compose -f api-gateway/compose.yaml up -d --build api-gateway
docker compose -f intelligence/docker-compose.yml up -d --build intelligence
docker compose -f gatherers/docker-compose.yml up -d --build gatherers
docker compose -f refineries/docker-compose.yml up --build pipeline
docker compose -f ui-portal/docker-compose.yml up -d --build ui-portal
```
