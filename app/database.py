from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# TODO: Improvement use async engine here.
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    Declarative base class for SQLAlchemy ORM models.

    This class defines a global naming convention for constraints and indexes,
    ensuring consistent schema generation across databases. It also enables
    eager defaults for ORM mappings.

    - **naming_convention**: Defines custom patterns for primary keys, foreign keys,
      unique constraints, indexes, and check constraints.
    - **metadata**: Metadata object configured with the naming convention.
    - **__mapper_args__**: Ensures defaults are loaded eagerly after INSERT operations.
    """

    naming_convention = {
        "ix": "idx_%(column_0_N_label)s",
        "uq": "%(table_name)s_%(column_0_N_name)s_uq",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "%(table_name)s_%(column_0_name)s_fkey",
        "pk": "%(table_name)s_pkey",
    }

    metadata = MetaData(naming_convention=naming_convention)
    __mapper_args__ = {"eager_defaults": True}


# Dependency
def get_db() -> Generator[Session]:
    """
    Provide a database session for request handling.

    This function is used as a FastAPI dependency. It yields a database session
    that can be used to interact with the database during the request lifecycle.
    After the request is processed, the session is automatically closed.

    - **yield**: An active `Session` object bound to the configured engine.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
