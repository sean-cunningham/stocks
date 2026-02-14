# Stock Bot Backend v2

## Run

From the `backend/` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

The SQLite database is created as `stocks.db` in the current working directory (run from `backend/` so the file is `backend/stocks.db`).

## CORS

The API allows the Next.js frontend by default from `http://localhost:3000`. Configure origins via env:

```bash
# default: http://localhost:3000
set ALLOWED_ORIGINS=http://localhost:3000,https://myapp.example.com
```

## Quickstart (backend + frontend)

1. Start backend from `backend/`: `uvicorn app.main:app --reload --port 8000`
2. Start frontend from `frontend/`: `npm run dev`
3. Open `http://localhost:3000`; the app will call the backend at `http://localhost:8000`.

## API examples

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl http://127.0.0.1:8000/api/analyze/AAPL
```

```bash
curl -X POST http://127.0.0.1:8000/api/portfolio/buy \
  -H "Content-Type: application/json" \
  -d "{\"ticker\":\"AAPL\",\"qty_optional\":null,\"notional_usd_optional\":1500,\"risk_mode\":\"moderate\",\"fees\":0}"
```

```bash
curl http://127.0.0.1:8000/api/portfolio/active
```

```bash
curl -X POST http://127.0.0.1:8000/api/portfolio/sell \
  -H "Content-Type: application/json" \
  -d "{\"ticker\":\"AAPL\",\"qty_optional\":1,\"fees\":0}"
```

```bash
curl http://127.0.0.1:8000/api/metrics
```

## Scheduler (APScheduler)

The app can run background jobs using APScheduler (in-memory scheduler/cache).

- Enable via `app/config.py` (`ENABLE_SCHEDULER = True`).
- Cadence:
  - Reserve job every `RESERVE_JOB_MINUTES` (default 60)
  - Broad job every `BROAD_JOB_HOURS` (default 6)

Jobs write audit rows with:

- `event_type='JOB'` for normal job summaries
- `event_type='ERROR'` for failures

Inspect `audit_log` after runtime (from `backend/` so DB path is `stocks.db`):

```bash
python -c "import sqlite3; c=sqlite3.connect('stocks.db'); print(c.execute(\"SELECT id, ts_utc, event_type, payload_json FROM audit_log ORDER BY id DESC LIMIT 20\").fetchall())"
```
