import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL belum diatur. Isi backend-news/.env atau environment Docker."
    )

# Keep the full connection URL in .env. Docker Compose overrides only the host
# so the same credentials work on the compose network (service name: db).
database_url = make_url(DATABASE_URL)
database_host = os.getenv("DATABASE_HOST")
database_port = os.getenv("DATABASE_PORT")
if database_host:
    database_url = database_url.set(host=database_host)
if database_port:
    database_url = database_url.set(port=int(database_port))

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
    pool_timeout=int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
    connect_args={"connect_timeout": int(os.getenv("DATABASE_CONNECT_TIMEOUT", "10"))},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
