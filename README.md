# Re:Learn

Re:Learn is an adaptive learning MVP built around a complete misconception loop:

`diagnose → intervene → reassess → update learner model`

The initial domain is Python `range()` loop boundaries. The demo deliberately uses a small, controlled taxonomy so every diagnosis is explainable and traceable—not a generic chatbot or PDF Q&A system.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
```

Create `backend/.env` from the root `.env.example` and replace the Neon placeholders with the **pooled** connection string from your Neon dashboard. It should use the SQLAlchemy psycopg form:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@YOUR-HOST-pooler.REGION.aws.neon.tech/neondb?sslmode=require
```

Neon requires TLS, so retain `sslmode=require`. The backend uses the database URL directly and creates missing MVP tables on startup. SQLite remains a local-only fallback if `DATABASE_URL` is omitted.

Configure authenticated API access in `backend/.env`:

```env
NEON_AUTH_ISSUER=https://YOUR_NEON_AUTH_HOST/neondb/auth
NEON_AUTH_JWKS_URL=https://YOUR_NEON_AUTH_HOST/neondb/auth/.well-known/jwks.json
NEON_AUTH_AUDIENCE=authenticated
NEON_AUTH_TEACHER_EMAILS=teacher@example.edu
NEON_AUTH_ADMIN_EMAILS=admin@example.edu
```

Only verified email addresses in the server-side allowlists receive staff roles. All other authenticated identities are students. The API verifies bearer tokens against the configured issuer and JWKS; client role headers are ignored. Rotate credentials that were previously present in `.env.example` and keep real values in local environment files, never in committed examples.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`). The API endpoint is configured by `VITE_API_URL`, defaulting to `http://localhost:8000/api`.
Set `VITE_NEON_AUTH_URL` in `frontend/.env.local` to the same Neon Auth base URL used by the backend. Sign-in fails closed when this is missing.
Keep the FastAPI backend running in a separate terminal while using the frontend. Neon handles the credential check, then the frontend calls the API at `/api/auth/me` to load the application profile; if that API is unavailable, start the backend or set `VITE_API_URL` to its reachable URL.

## API flow

1. `POST /api/questions` creates or returns a question.
2. `POST /api/submissions` records a response and runs diagnosis.
3. `POST /api/interventions` retrieves misconception-specific pedagogy and creates an intervention.
4. `POST /api/reassessment` answers a structurally different follow-up and updates the learner model.

Teacher assignment APIs create drafts. Owners can publish drafts with `POST /api/teacher/assignments/{id}/publish`; enrolled students can submit multiple attempts to `POST /api/assignments/{id}/submissions`, and teachers can review attempts. Current grading is normalized exact-answer matching, not ML diagnosis.

Institution records, memberships, class links, enrollment, and reports are available under `/api/institutions`. Institution creation is restricted to the server allowlisted admin role; membership changes are institution-admin scoped.

## ML and RAG status

The diagnosis implementation remains the existing controlled rule-based detector; no trained artifact is present under `ml/`. The RAG package contains retrieval/ingestion protocols and the current intervention path reads curated `KnowledgeDocument` rows with SQL metadata filters. A pgvector store, ingestion runtime, and authenticated RAG endpoint are not configured in this repository. Do not treat the current intervention lookup as vector RAG or as a trained ML model.

Tests: `cd backend && pytest`
