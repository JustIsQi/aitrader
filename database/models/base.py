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

# Create engine with optimized connection pooling for 8GB RAM system
# 针对8GB RAM系统优化连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=10,                   # ⭐ Optimized for 8GB: reduced from 20 to 10
    max_overflow=20,                # ⭐ Reduced from 30 to 20 (total: 30 connections max)
    pool_pre_ping=False,            # ⭐ Remove overhead (use pool_recycle instead)
    pool_recycle=1800,              # ⭐ Reduced from 3600 to 1800 seconds (30 min)
    pool_timeout=30,                # ⭐ Wait 30 seconds for connection before error
    echo=False,
    pool_use_lifo=True,             # Use LIFO strategy for better connection reuse
    connect_args={
        'connect_timeout': 10,
        # ⭐ OPTIMIZED: Reduced timeout for 8GB system (30 min → 5 min)
        'options': '-c statement_timeout=300000'  # SQL语句超时时间 (5 minutes)
    },
    # ⭐ ADD: Enable query result caching at connection level
    execution_options={
        "isolation_level": "READ COMMITTED",  # Allow reading committed data
        "stream_results": False               # Load full results (faster for analytics)
    }
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ⭐ ADD: Separate connection pools for different workload types (8GB optimization)

# API专用连接池 (轻量级快速查询)
# Optimized for fast API requests with low memory footprint
api_engine = create_engine(
    DATABASE_URL,
    pool_size=5,                    # Small pool for API requests
    max_overflow=5,                 # Total: 10 connections max
    pool_recycle=1800,              # Recycle after 30 minutes
    pool_timeout=10,                # Shorter timeout for API
    echo=False,
    pool_use_lifo=True,
    connect_args={
        'connect_timeout': 5,
        # ⭐ 10 second timeout for API queries (fast response required)
        'options': '-c statement_timeout=10000'
    },
    execution_options={
        "isolation_level": "READ COMMITTED",
        "stream_results": False
    }
)

# 回测专用连接池 (重量级长查询)
# Optimized for long analytical queries in backtesting
backtest_engine = create_engine(
    DATABASE_URL,
    pool_size=10,                   # Larger pool for concurrent backtests
    max_overflow=10,                # Total: 20 connections max
    pool_recycle=3600,              # Recycle after 1 hour (longer for backtests)
    pool_timeout=60,                # Longer timeout for backtest operations
    echo=False,
    pool_use_lifo=True,
    connect_args={
        'connect_timeout': 30,
        # ⭐ 10 minute timeout for backtesting queries
        'options': '-c statement_timeout=600000'
    },
    execution_options={
        "isolation_level": "READ COMMITTED",
        "stream_results": False
    }
)

# Create Base class for models
Base = declarative_base()
