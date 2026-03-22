# Telemetry Service

BioNexus Telemetry is a TypeScript GraphQL service built with Express and Apollo Server.

- Users and UI telemetry events are stored in MongoDB.
- Authentication and registration are managed through GraphQL mutations.
- JWTs are signed with the same secret, issuer, and audience contract used by the Python gateway.
- Telemetry dashboard queries are restricted to `isAdmin` users.

## Routes

- GraphQL endpoint: `http://localhost:4100/graphql`

## Core Operations

- `login(input)`
- `register(input)`
- `me`
- `recordTelemetry(input)`
- `telemetryDashboard(rangeDays)`

## Local Run

```bash
cd telemetry
npm install
npm test
docker compose up -d --build
```

The compose file expects the Lake stack network and MongoDB container to already be available.
