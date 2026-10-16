import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5434")
DB_NAME = os.getenv("DB_NAME", "women_safe_navigation")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "khushi")

PG_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Test PostgreSQL availability
pg_engine = None
try:
    _test_engine = create_engine(PG_DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 1})
    with _test_engine.connect():
        pg_engine = _test_engine
        print("[Database] Connected to PostgreSQL/PostGIS.")
except Exception:
    pg_engine = None

Base = declarative_base()

if pg_engine is not None:
    engine = pg_engine
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Resilient local SQLite database fallback for user auth, reports, and POIs when PostgreSQL is offline
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_dir = os.path.join(repo_root, "data", "dev_test")
    os.makedirs(db_dir, exist_ok=True)
    sqlite_path = os.path.join(db_dir, "women_safe_navigation.db")
    SQLITE_DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_sqlite_tables():
    """Initializes tables in fallback SQLite database if PostgreSQL is not active."""
    if pg_engine is None:
        from backend.app.models.user import User
        from backend.app.models.report import UserReport
        Base.metadata.create_all(bind=engine, tables=[User.__table__, UserReport.__table__])

try:
    init_sqlite_tables()
except Exception as e:
    print(f"[Database] Warning creating tables: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
