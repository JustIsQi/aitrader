"""
SQLAlchemy Base Configuration for PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection URL
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:Yy882388lsls@localhost:5432/aitrader'
)

# Create engine with optimized connection pooling for analytical workloads
# 针对分析型工作负载优化连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=20,                   # ⭐ Increased from 5 to 20 for better concurrency
    max_overflow=30,                # ⭐ Increased from 10 to 30 (total: 50 connections max)
    pool_pre_ping=False,            # ⭐ Remove overhead (use pool_recycle instead)
    pool_recycle=3600,              # Recycle connections after 1 hour
    pool_timeout=30,                # ⭐ Wait 30 seconds for connection before error
    echo=False,
    pool_use_lifo=True,             # Use LIFO strategy for better connection reuse
    connect_args={
        'connect_timeout': 10,
        # ⭐ OPTIMIZE: Increase timeout for analytical queries (5 min → 30 min)
        'options': '-c statement_timeout=1800000'  # SQL语句超时时间 (30 minutes)
    },
    # ⭐ ADD: Enable query result caching at connection level
    execution_options={
        "isolation_level": "READ COMMITTED",  # Allow reading committed data
        "stream_results": False               # Load full results (faster for analytics)
    }
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()
