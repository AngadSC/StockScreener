from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine (
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Check connections before using
    pool_size=10,            # Max connections in pool
    max_overflow=20,       # Extra connections when pool full
    echo=False
) 

#session facotry 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base class for the models 
Base = declarative_base()

#depdenecy for FASTAPI routes
def get_db(): 
    db = SessionLocal() 
    try:
        yield db 
    finally:
        db.close () 

