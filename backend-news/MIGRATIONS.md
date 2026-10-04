# Database migration and Docker

## Local backend development

1. Copy `.env.example` to `.env` and fill in database credentials. `DATABASE_URL` is the SQLAlchemy connection URL; URL-encode reserved characters in its username or password.
2. Install backend dependencies: `pip install -r requirements.txt`.
3. Apply schema changes: `alembic upgrade head` from this folder.
4. Start the API: `uvicorn app.main:app --reload`.

The API does not create or alter tables during startup. Use Alembic for every schema change. To create a revision after editing SQLAlchemy models, run `alembic revision --autogenerate -m "describe the change"`, inspect it, then run `alembic upgrade head`.

## Separate Docker Compose projects

The backend Compose file at `backend-news/docker-compose.yml` starts PostgreSQL and FastAPI. PostgreSQL data persists in the `news-website-postgres18-data` volume. Backend waits for database health, uses `DATABASE_HOST=db`, applies `alembic upgrade head`, then starts FastAPI.

The frontend Compose file at `frontend-news/docker-compose.yml` builds and serves React/Nginx independently. Frontend calls `BACKEND_PUBLIC_URL` directly, so `CORS_ORIGINS` must include the frontend origin. Local defaults are backend `http://localhost:8000` and frontend `http://localhost:8080`. Set `backend-news/.env` first, then start each service from its own folder:

```powershell
cd D:\news-website\backend-news
docker compose --env-file .env up --build -d

cd D:\news-website\frontend-news
docker compose --env-file ..\backend-news\.env up --build -d
```

Admin and writer management pages are served directly by the backend; the frontend does not proxy `/dashboard` or `/writer`. For a VM move, back up and restore PostgreSQL logically; do not copy a live database volume as a substitute.

## Import an existing local database into Docker (Windows)

From the repository root, run `.\backend-news\scripts\import-local-db-to-docker.ps1`. It reads the source from `backend-news/.env`, saves custom-format backups under `backend-news/backups`, restores the source into Docker, then starts the backend and frontend projects separately. It requires Docker Desktop and PostgreSQL `pg_dump` on `PATH` or under `C:\Program Files\PostgreSQL`.

If the Docker database already contains users or news, the script stops without overwriting it. To replace the target, run `.\backend-news\scripts\import-local-db-to-docker.ps1 -Force`; the script backs up the target first.

Run Alembic CLI commands from this folder:

```powershell
alembic current
alembic history
docker compose --env-file .env logs -f backend
docker compose --env-file .env exec backend alembic current
```

Keep `.env` out of version control. Commit migration files so each VM applies the same schema revisions.
