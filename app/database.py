from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from app.config import settings

engine = create_engine(settings.DB_URI, connect_args={"check_same_thread": False})

# fk sqlite activated for each connection - due to cascads
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

session_factory = sessionmaker(bind=engine)
db_session = scoped_session(session_factory)

Base = declarative_base()

def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()