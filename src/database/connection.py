from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from contextlib import contextmanager
import os
from typing import Generator
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration with fallback values
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dronefleet")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# Create engine with connection pooling
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        echo=bool(os.getenv('SQL_ECHO', False))
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# Add SQLAlchemy event listeners for connection debugging
@event.listens_for(Engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("New database connection established")

@event.listens_for(Engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# Declarative base class
Base = declarative_base()

@contextmanager
def get_db() -> Generator:
    """
    Database session context manager.
    Handles session creation and cleanup with error handling.
    """
    db = SessionLocal()
    try:
        logger.debug("Database session started")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        logger.debug("Database session closed")
        db.close()

def init_db(drop_all: bool = False) -> None:
    """
    Initialize database tables.
    
    Args:
        drop_all: If True, drops all existing tables before creation
    """
    try:
        if drop_all:
            logger.warning("Dropping all database tables")
            Base.metadata.drop_all(bind=engine)
        
        logger.info("Creating database tables")
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

def check_db_connection() -> bool:
    """
    Check if database connection is working.
    Returns: bool indicating connection status
    """
    try:
        with get_db() as db:
            db.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False