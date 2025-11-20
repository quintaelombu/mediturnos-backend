from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.environ["DATABASE_URL"]

# Crear motor SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener sesión
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
