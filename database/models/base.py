"""
SQLAlchemy Base Configuration for Database
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection URL
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///aitrader.db'
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_recycle=3600,
    pool_pre_ping=True,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

api_engine = engine
backtest_engine = engine

# Create Base class for models
Base = declarative_base()
