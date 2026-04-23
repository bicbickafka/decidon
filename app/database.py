from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from app.config import settings

engine = create_engine(settings.DB_URI, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
db_session = scoped_session(session_factory)

Base = declarative_base()

def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()