# Security

- **Never commit secrets.** Do not add `.env`, `.env.local`, or any file containing API keys, tokens, or passwords to version control.
- **Use env templates.** Copy `backend/.env.example` and `frontend/.env.local.example` to `.env` / `.env.local` and fill in values locally only.
- **Rotate keys if leaked.** If an API key or credential is ever committed or exposed, revoke and replace it immediately.
- **Keep the database out of git.** The SQLite file (e.g. `backend/stocks.db`) must stay in `.gitignore`; it may contain sensitive or local-only data.
- **Do not commit credential files.** Ignore `*.pem`, `*.key`, `credentials.json`, `service-account*.json`, and similar; rely on env vars or secure secret stores instead.
