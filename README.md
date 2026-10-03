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

Neon requires TLS, so retain `sslmode=require`. The backend uses the database URL directly and creates the MVP tables and seed data on startup. SQLite remains a local-only fallback if `DATABASE_URL` is omitted.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`). The API endpoint is configured by `VITE_API_URL`, defaulting to `http://localhost:8000/api`.

## API flow

1. `POST /api/questions` creates or returns a question.
2. `POST /api/submissions` records a response and runs diagnosis.
3. `POST /api/interventions` retrieves misconception-specific pedagogy and creates an intervention.
4. `POST /api/reassessment` answers a structurally different follow-up and updates the learner model.

Tests: `cd backend && pytest`
