# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single research prototype (`grapheval_prototype`) with two long-running services plus a CLI. It runs **fully offline** using the built-in `mock` LLM provider; `Ollama` and `Neo4j` are optional and only needed for real-LLM runs / graph storage.

### Environment
- Python deps are installed into a project-local virtualenv at `.venv` (the OS Python is PEP-668 "externally managed", so use the venv). Run Python tools as `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/uvicorn`.
- Frontend deps live in `frontend/node_modules` (npm; `frontend/package-lock.json` is the lockfile).
- Docker and Ollama are NOT installed in this environment. Do not use `scripts/start-dev.sh` here — it hard-requires Docker (for Neo4j) and exits early. Start the backend and frontend manually instead (see below).

### Services

| Service | Required | Run command | Notes |
|---|---|---|---|
| FastAPI backend | Yes | `DEFAULT_LLM_PROVIDER=mock NEO4J_ENABLED=false .venv/bin/python -m uvicorn api.server:app --reload --port 8000` | Health: `/health`, dep status: `/dependencies`, docs: `/docs`. Run from repo root. |
| Next.js frontend | Yes | `npm run dev` in `frontend/` | Serves on :3000 (falls back to :3001). Talks to backend at `http://localhost:8000` (override via `NEXT_PUBLIC_API_URL`). |
| Neo4j | Optional | via Docker (not installed here) | Storage only, not the verifier. Endpoints degrade gracefully when disabled (empty `claims` + `error`). |
| Ollama | Optional | `ollama serve` + pull `gemma4:*` (not installed here) | Only for real LLM runs. Use `provider=mock` otherwise. |

### Running / testing gotchas
- The web UI defaults the Provider dropdown to `Ollama`; since Ollama isn't installed, select **`Mock`** (or use the `Built-in Example` / `Custom Input` tabs with `mock`) to run offline.
- Tests: `.venv/bin/pytest tests/ -q` — all default tests use `MockProvider` and need no Ollama/Neo4j/frontend. 6 tests are skipped (live Ollama/Neo4j integration) by design.
- Frontend lint: `npm run lint` in `frontend/`. Build: `npm run build`.
- CLI: `.venv/bin/python -m src.main --provider mock`.
- Env defaults come from `.env.example` (copy to `.env` if desired); the manual run commands above set the needed vars inline so `.env`/Ollama/Neo4j are not required.
