"""
Database configuration and session management.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .models import Base
from dotenv import load_dotenv

load_dotenv()

# Database URL
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=os.getenv('DEBUG', 'False').lower() == 'true'
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def close_db_session(db):
    """Close a database session."""
    db.close()

class DatabaseManager:
    """Database manager for handling database operations."""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def create_all_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all_tables(self):
        """Drop all tables in the database."""
        Base.metadata.drop_all(bind=self.engine)

# Global database manager instance
db_manager = DatabaseManager()