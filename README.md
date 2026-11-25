# ScholarSync — Official-Source Scholarship Discovery & Deterministic Eligibility Guide

ScholarSync is a production-ready web application for students in India to discover scholarships backed by official government/institutional sources, evaluate eligibility deterministically, track applications, and ask an evidence-grounded AI guide.

## Core Design Guarantees

1. **Zero Mock / Fake Data in Production:** Production ships with verified official sources (currently AICTE schemes and official 2026–27 notification/guideline PDFs from `aicte.gov.in`) and supports adding any official HTML, PDF, or permitted JSON source in the Admin Source Registry. Test fixtures reside exclusively in `backend/tests/fixtures/`.
2. **Full Auto-Update with Audit Trail:** When scheduled or manual sync detects updated dates or status from a live official source, ScholarSync updates the scheme, records an immutable snapshot + field diff in `scholarship_versions`, re-indexes official passages in PostgreSQL, and creates in-app notifications for saved/matched users.
3. **Deterministic Eligibility Engine:** `backend/app/eligibility/engine.py` evaluates `PASS`, `FAIL`, and `UNKNOWN` in pure Python (no LLM involvement). Missing or `prefer_not_to_say` fields never silently pass.
4. **PostgreSQL RAG Persistence:** Extracted guideline passages and full-text search indexes (`tsvector` + GIN index on PostgreSQL) live in PostgreSQL so they survive redeploys on Render without requiring a paid persistent disk.
5. **Works Without `GEMINI_API_KEY`:** Registration, login, profile matching, discovery, deterministic eligibility breakdowns, saved lists, trackers, source sync, and non-LLM AI fallback all work out of the box without a Gemini key.
6. **Privacy by Design:** Never requests or stores Aadhaar numbers, bank details, portal passwords, or certificate uploads. Users can edit or permanently delete their account and data at any time.

---

## Project Structure

```text
├── backend/
│   ├── alembic/                  # Database migrations
│   ├── app/
│   │   ├── agent/                # Gemini coordinator + controlled tools + deterministic fallback
│   │   ├── api/v1/               # Versioned REST endpoints (/api/v1/*)
│   │   ├── collectors/           # HTML, PDF (PyMuPDF), API, and AICTE official adapters
│   │   ├── core/                 # Config validation, Argon2id + session security, logging
│   │   ├── db/                   # SQLAlchemy 2.x engine & session
│   │   ├── eligibility/          # Pydantic rule schema & deterministic Python engine
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── monitoring/           # Source sync, change detection, version history
│   │   ├── rag/                  # Chunker + PostgreSQL FTS / BM25 passage retriever
│   │   ├── schemas/              # Typed Pydantic request/response schemas
│   │   ├── services/             # Auth, scholarship, notification services
│   │   ├── cli.py                # CLI: create-admin, bootstrap-registry, sync-sources
│   │   └── main.py               # FastAPI app + SPA static serving for Render
│   └── tests/                    # Pytest unit, integration, and E2E journey tests
├── frontend/                     # React + Vite + TypeScript + Tailwind CSS + TanStack Query
├── docker-compose.yml            # Local PostgreSQL 16 service
├── render.yaml                   # Render Blueprint (Web Service + Postgres + Cron Job)
└── .env.example
```

---

## Local Development Setup

### 1. Start PostgreSQL (Docker Compose)

```bash
cp .env.example .env
docker compose up -d postgres
```

### 2. Backend Setup, Migrations & Official Source Sync

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Run Alembic database migrations
alembic upgrade head

# Bootstrap verified official sources & run initial live sync
python -m app.cli bootstrap-registry
python -m app.cli sync-sources

# Create your first admin user (no default password is ever hardcoded)
python -m app.cli create-admin --email admin@example.com

# Start FastAPI backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

---

## Running Tests & Quality Checks

### Backend (`pytest` + `ruff`)

```bash
cd backend
pytest -v
ruff check app tests
```

### Frontend (`vitest` + TypeScript + Vite build)

```bash
cd frontend
npm test
npm run build
```

---

## Deploying to Render

This repository includes a complete [`render.yaml`](./render.yaml) Blueprint configured for:
1. **Single Render Web Service (`scholarsync`)**: builds `frontend/dist` and serves both the React SPA and FastAPI `/api/v1` on the same origin (enabling `HttpOnly; Secure; SameSite=Lax` session cookies cleanly).
2. **Render Managed PostgreSQL (`scholarsync-db`)**: stores users, profiles, scholarships, version diffs, check logs, notifications, and PostgreSQL RAG guideline chunks.
3. **Render Cron Job (`scholarsync-official-source-sync`)**: runs `python -m app.cli sync-sources` every 12 hours against the same PostgreSQL database to detect updates on live official scholarship URLs and PDFs.

### Required Environment Variables on Render

| Variable | Required | Description |
| --- | --- | --- |
| `APP_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Generated automatically by `render.yaml` (32+ chars) |
| `DATABASE_URL` | Yes | Connected automatically from `scholarsync-db` |
| `FRONTEND_ORIGIN` | Recommended | Your Render URL, e.g. `https://scholarsync.onrender.com` |
| `GEMINI_API_KEY` | Optional (add later) | Enables conversational Gemini AI assistant (`google-genai`). App works deterministically without it. |
| `GEMINI_MODEL` | Optional | Defaults to `gemini-3.8-flash` |
| `ADMIN_EMAIL` & `ADMIN_INITIAL_PASSWORD` | Optional | Bootstraps the first admin user on startup if no admin exists yet (alternatively run `python -m app.cli create-admin` in Render Shell). |

---

## Known Limitations & Operational Notes

- Official portal availability depends on external government web servers (`aicte.gov.in`, `scholarships.gov.in`, etc.). If a source is unreachable or blocks automated requests, ScholarSync logs the error, preserves existing verified data, and marks records `STALE` after `STALE_AFTER_DAYS` (default 14 days).
- Application submission and official status tracking always remain on the official scholarship portal; ScholarSync's tracker stores user-maintained personal statuses only.
