# PostgreSQL Optimization Deployment Guide

## Overview
This guide will help you deploy the PostgreSQL optimizations to improve data loading performance from **32-37 minutes to 3-5 minutes** (85-90% reduction).

---

## Phase 1: Code-Level Optimizations ✅ (Already Applied)

The following code changes have been applied and are active:

1. ✅ **Batch query optimization** in `datafeed/db_dataloader.py`
   - Adaptive batch sizes
   - Concurrent ETF/stock loading with ThreadPoolExecutor
   - Removed redundant Python filtering
   - Added performance monitoring

2. ✅ **Connection pool optimization** in `database/models/base.py`
   - Increased pool_size from 5 to 20
   - Increased max_overflow from 10 to 30
   - Removed pool_pre_ping overhead
   - Increased statement_timeout from 5 min to 30 min

3. ✅ **Query performance logging** in `database/pg_manager.py`
   - Added query_timer() context manager
   - Logs slow queries (> 1 second)
   - Tracks batch query performance

**Expected Improvement:** 6-10x (32-37 min → 3-6 min)

**Test Current Performance:**
```bash
cd /data/home/yy/code/aitrader
python run_ashare_signals.py
```

---

## Phase 2: PostgreSQL Configuration (Requires Container Restart)

### Step 1: Backup Current Configuration

```bash
# Backup current PostgreSQL config
docker exec pg cat /var/lib/postgresql/18/docker/postgresql.conf > /data/home/yy/data/pgdata/postgresql.conf.backup

# Backup Docker run command for reference
echo "Current container config:"
docker inspect pg | grep -A 20 "Cmd"
```

### Step 2: Stop Current Container

```bash
# Stop the current PostgreSQL container
docker stop pg

# Rename old container (keep as backup)
docker rename pg pg_old
```

### Step 3: Start New Container with Optimized Config

```bash
# Start new container with optimized PostgreSQL configuration
docker run -ti -d \
  --name pg \
  -e POSTGRES_PASSWORD=Yy882388lsls \
  -v /data/home/yy/data/pgdata:/var/lib/postgresql/data \
  -v /data/home/yy/code/aitrader/postgres_config/postgresql.conf:/etc/postgresql/postgresql.conf \
  -p 5432:5432 \
  postgres:latest \
  -c config_file=/etc/postgresql/postgresql.conf
```

**Note:** The optimized config file is located at:
`/data/home/yy/code/aitrader/postgres_config/postgresql.conf`

### Step 4: Verify Configuration

```bash
# Wait 10 seconds for PostgreSQL to start
sleep 10

# Check if container is running
docker ps | grep pg

# Verify optimized settings are loaded
docker exec pg cat /var/lib/postgresql/data/postgresql.conf | grep -E "^(shared_buffers|work_mem|max_parallel_workers|effective_cache_size)" | head -10

# Expected output:
# shared_buffers = 256GB
# work_mem = 256MB
# max_parallel_workers_per_gather = 8
# effective_cache_size = 756GB

# Verify PostgreSQL is accepting connections
docker exec pg psql -U postgres -c "SELECT version();"
```

### Step 5: Test Connection from Application

```bash
# Test database connection
cd /data/home/yy/code/aitrader
python -c "
from database.pg_manager import get_db
db = get_db()
stats = db.get_statistics()
print(f'✓ Database connected successfully')
print(f'  Total symbols: {stats[\"total_symbols\"]}')
print(f'  Total records: {stats[\"total_records\"]:,}')
"
```

### Step 6: Run Full Test

```bash
# Run signal generation with optimized configuration
python run_ashare_signals.py
```

**Expected Performance After Phase 2:**
- **Target:** < 300 seconds (5 minutes)
- **Cumulative Improvement:** 12-30x (from original 32-37 minutes)

---

## Phase 3: Database Schema Optimization (No Downtime)

### Step 1: Add Composite Indexes

```bash
# Connect to PostgreSQL
docker exec -it pg psql -U postgres -d aitrader

# Execute the index creation script
\i /data/home/yy/code/aitrader/postgres_config/add_indexes.sql

# Or execute manually:
```

```sql
-- Create composite index for stock_history (date-first queries)
CREATE INDEX CONCURRENTLY idx_stock_date_symbol
ON stock_history (date, symbol);

-- Create composite index for etf_history (date-first queries)
CREATE INDEX CONCURRENTLY idx_etf_date_symbol
ON etf_history (date, symbol);
```

### Step 2: Monitor Index Creation

```sql
-- Check index creation progress (runs in background)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%date_symbol%'
ORDER BY indexname;
```

### Step 3: Verify Index Usage

```sql
-- Test query to verify index usage
EXPLAIN ANALYZE
SELECT *
FROM stock_history
WHERE date >= '2020-01-01' AND date <= '2024-12-31'
  AND symbol IN ('000001.SZ', '000002.SZ')
LIMIT 100;
```

**Expected Output:**
- Should show `Bitmap Index Scan using idx_stock_date_symbol` or `Index Scan using idx_stock_date_symbol`

**Expected Improvement:** 1.5-2x faster for date-range queries

---

## Phase 4: Monitoring and Validation

### Performance Monitoring Dashboard

```sql
-- Connect to PostgreSQL
docker exec -it pg psql -U postgres -d aitrader

-- Check slow queries (requires logging enabled in postgresql.conf)
SELECT
    query,
    calls,
    mean_exec_time,
    total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- Queries slower than 1 second
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('stock_history', 'etf_history')
ORDER BY idx_scan DESC;

-- Check buffer cache hit ratio (should be > 99% with 256GB shared_buffers)
SELECT
    round(sum(blks_hit)::numeric / (sum(blks_hit) + sum(blks_read)), 4) * 100
    AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = 'aitrader';

-- Check connection pool utilization
SELECT
    count(*) AS active_connections,
    max_connections,
    round((count(*)::float / max_connections) * 100, 2) AS utilization_percent
FROM pg_stat_activity
WHERE state = 'active'
CROSS JOIN (SELECT setting::int AS max_connections FROM pg_settings WHERE name = 'max_connections');
```

### Application-Level Monitoring

The optimized code now includes performance metrics. View them in the logs:

```bash
# View data loading performance
tail -f /data/home/yy/code/aitrader/logs/*.log | grep "数据加载"

# View query timing
tail -f /data/home/yy/code/aitrader/logs/*.log | grep "查询"

# View slow query warnings
tail -f /data/home/yy/code/aitrader/logs/*.log | grep "慢查询"
```

---

## Performance Validation

### Benchmark Script

Create `benchmark_loading.py`:

```python
import time
from datafeed.db_dataloader import DbDataLoader
from core.stock_universe import StockUniverse

def benchmark_data_load():
    """Benchmark data loading performance"""

    # Get typical stock universe
    universe = StockUniverse()
    all_symbols = universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=True,
        exclude_new_ipo_days=252
    )

    # Test with 1000 stocks
    test_symbols = all_symbols[:1000]

    print(f"🧪 开始基准测试: {len(test_symbols)} 只股票")
    print(f"📅 数据范围: 2020-01-01 ~ 2024-12-31")

    start = time.time()
    loader = DbDataLoader(auto_download=False)
    dfs = loader.read_dfs(
        symbols=test_symbols,
        start_date='20200101',
        end_date='20241231'
    )
    elapsed = time.time() - start

    total_rows = sum(len(df) for df in dfs.values())

    print(f"\n✅ 测试完成:")
    print(f"   加载标的: {len(dfs)}")
    print(f"   总行数: {total_rows:,}")
    print(f"   耗时: {elapsed:.2f}秒 ({elapsed/60:.2f}分钟)")
    print(f"   平均速度: {total_rows/elapsed:.0f} 行/秒")

    print(f"\n🎯 性能目标:")
    print(f"   当前: {elapsed:.2f}秒 ({elapsed/60:.2f}分钟)")
    print(f"   目标: < 300秒 (5分钟)")
    print(f"   优秀: < 180秒 (3分钟)")

    if elapsed < 180:
        print(f"   ✅ 优秀! 已达到3分钟目标")
    elif elapsed < 300:
        print(f"   ✓ 良好! 已达到5分钟目标")
    else:
        print(f"   ❌ 需要继续优化")

    return elapsed, total_rows

if __name__ == '__main__':
    benchmark_data_load()
```

### Run Benchmark

```bash
cd /data/home/yy/code/aitrader
python benchmark_loading.py
```

---

## Rollback Procedure

If you encounter issues, rollback to the original configuration:

### Rollback PostgreSQL Configuration

```bash
# Stop optimized container
docker stop pg
docker rm pg

# Start original container
docker start pg_old

# Rename back to pg
docker rename pg_old pg

# Verify original configuration
docker exec pg cat /var/lib/postgresql/18/docker/postgresql.conf | grep shared_buffers
```

### Rollback Code Changes

```bash
cd /data/home/yy/code/aitrader
git status
git checkout datafeed/db_dataloader.py
git checkout database/models/base.py
git checkout database/pg_manager.py
```

---

## Troubleshooting

### Issue: Container fails to start with new config

**Solution:** Check config syntax
```bash
# Validate config file
docker run --rm postgres:latest postgres -C config_file=/etc/postgresql/postgresql.conf -c config_file=/data/home/yy/code/aitrader/postgres_config/postgresql.conf
```

### Issue: Connection pool exhausted

**Solution:** Monitor and adjust pool size
```bash
# Check active connections
docker exec pg psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# If approaching max_connections (200), reduce pool_size in database/models/base.py
```

### Issue: Index creation takes too long

**Solution:** Check progress and let it complete
```sql
-- Check if index creation is still running
SELECT
    l.locktype,
    l.relation::regclass,
    l.mode,
    l.granted
FROM pg_locks l
JOIN pg_class c ON l.relation = c.oid
WHERE c.relname LIKE '%date_symbol%';
```

---

## Expected Results Summary

| Phase | Implementation | Expected Time | Improvement |
|-------|---------------|---------------|-------------|
| Baseline | Original code | 1949-2253s (32-37min) | - |
| Phase 1 | Code optimization | 200-400s (3-7min) | 6-10x |
| Phase 2 | PostgreSQL config | 100-300s (2-5min) | 12-30x |
| Phase 3 | Composite indexes | 80-250s (1-4min) | 15-35x |

**Final Target:** < 300 seconds (5 minutes) ✅
**Stretch Goal:** < 180 seconds (3 minutes) 🏆

---

## Next Steps

1. **Apply Phase 1** ✅ (Already done)
2. **Apply Phase 2** (PostgreSQL configuration restart)
3. **Apply Phase 3** (Add indexes - no downtime)
4. **Run benchmarks** and validate performance
5. **Monitor logs** for slow queries and optimize further

---

## Support

If you encounter issues:

1. Check logs: `tail -f /data/home/yy/code/aitrader/logs/*.log`
2. Review PostgreSQL logs: `docker logs pg`
3. Verify configuration: `docker exec pg cat /var/lib/postgresql/data/postgresql.conf | grep -E "^(shared_buffers|work_mem)"`
4. Run benchmark: `python benchmark_loading.py`
