# Re:Learn migrations

Alembic manages only Re:Learn application tables. Neon Auth tables are out of scope and must never be added to these revisions.

Migrations require a direct Neon PostgreSQL connection:

```bash
cd backend
export DATABASE_URL_UNPOOLED='postgresql+psycopg://…' # direct host; no -pooler
alembic upgrade head
```

For an existing database whose Re:Learn tables were created before Alembic, do not run the baseline create migration against those tables. Mark the existing baseline, then apply the additive Stage 4 revision:

```bash
alembic stamp 0001_baseline_core_schema
alembic upgrade head
```

Use a Neon development branch to test this sequence before a production branch. `DATABASE_URL` remains the pooled application connection; do not use it for migrations.
