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

# Database URL - Support both PostgreSQL and SQLite
# Priority: DATABASE_URL (Heroku) -> Manual config -> SQLite fallback
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Heroku PostgreSQL - fix postgresql:// to postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
elif os.getenv('DB_USER') == 'sqlite':
    # SQLite configuration for local development
    DATABASE_URL = f"sqlite:///{os.getenv('DB_NAME', 'teleaccount_bot.db')}"
else:
    # PostgreSQL configuration for manual setup
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

def init_db():
    """Initialize database - create all tables. Used by Heroku release phase."""
    try:
        print("🚀 Initializing database tables...")
        db_manager.create_all_tables()
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False