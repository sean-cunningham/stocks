# Stock Bot Frontend

Next.js App Router frontend that consumes the existing FastAPI backend.

## Requirements

- Node.js 18+
- Running backend at `http://localhost:8000` (or set env var below)

## Environment

Create `.env.local` (optional):

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

If not set, the app defaults to `http://localhost:8000`.

## Install and run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Routes

- `/holdings` -> active positions + sell modal
- `/market` -> analyze ticker + buy modal
- `/metrics` -> KPIs + equity curve chart

The home route `/` redirects to `/holdings`.
