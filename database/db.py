"""
Database connection and session management.

This module handles database initialization, connection, and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

from database.models import Base

# Load environment variables
load_dotenv()

# Get database path from environment or use default
DATABASE_PATH = os.getenv("DATABASE_PATH", "./database/properties.db")

# Ensure database directory exists
os.makedirs(os.path.dirname(DATABASE_PATH) if os.path.dirname(DATABASE_PATH) else ".", exist_ok=True)

# Create database URL
# SQLite with check_same_thread=False for FastAPI compatibility
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
# Using StaticPool for SQLite to handle multiple threads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_PATH}")


def get_db() -> Session:
    """
    Dependency function for FastAPI to get database session.
    
    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session for direct use (not as FastAPI dependency).
    
    Remember to close the session when done:
        db = get_db_session()
        try:
            # use db
        finally:
            db.close()
    """
    return SessionLocal()


def reset_db():
    """Drop all tables and recreate them. WARNING: This deletes all data!"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset complete - all tables recreated.")


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print("Database tables created successfully!")

