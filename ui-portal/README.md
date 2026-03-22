# UI Portal

BioNexus UI Portal is the Next.js client for graph exploration, clinical review, and the admin telemetry dashboard.

## Runtime Integrations

- REST gateway: `NEXT_PUBLIC_API_URL` for existing explorer, pathway, and analytics data.
- Telemetry GraphQL: `NEXT_PUBLIC_TELEMETRY_API_URL` for login, registration, session hydration, and telemetry queries.
- Local auth session: stored in browser storage with `isAdmin` so admin-only routes can be hidden client-side.

## Routes

- `/explorer`, `/pathways`, `/clinical-trials`, `/historical-trends`: authenticated user routes.
- `/telemetry`: admin-only dashboard with comparative charts backed by MongoDB telemetry data.
- `/login`, `/register`: GraphQL-backed auth screens.

## Local Run

```bash
cd ui-portal
npm install
npm test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
