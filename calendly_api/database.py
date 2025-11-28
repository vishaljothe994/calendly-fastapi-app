from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./calendlyy.db"

# Use the default SQLite engine with check_same_thread disabled for the
# application's threaded server. The previous WAL and timeout configuration
# was added to work around transient locking during development; since the
# issue has been resolved external to the app, keep the simpler configuration
# here. For heavier concurrency consider running a proper RDBMS (Postgres)
# in production.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
