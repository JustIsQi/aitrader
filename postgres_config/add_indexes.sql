-- PostgreSQL Index Optimization for Date-First Queries
-- Purpose: Optimize queries that filter by date range first, then by symbols
--
-- Most queries in the system use pattern:
--   WHERE date >= '2020-01-01' AND date <= '2024-12-31' AND symbol IN (...)
--
-- Current indexes are (symbol, date) which is inefficient for this pattern.
-- New indexes (date, symbol) will dramatically improve performance.

-- =============================================================================
-- Add composite index for stock_history table
-- =============================================================================

-- Create index for date-first queries on stock_history
-- Uses CONCURRENTLY to avoid locking the table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_date_symbol
ON stock_history (date, symbol);

-- Add comment for documentation
COMMENT ON INDEX idx_stock_date_symbol IS
'Optimized index for date-range queries followed by symbol filtering';

-- =============================================================================
-- Add composite index for etf_history table
-- =============================================================================

-- Create index for date-first queries on etf_history
-- Uses CONCURRENTLY to avoid locking the table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_etf_date_symbol
ON etf_history (date, symbol);

-- Add comment for documentation
COMMENT ON INDEX idx_etf_date_symbol IS
'Optimized index for date-range queries followed by symbol filtering';

-- =============================================================================
-- Verify indexes created successfully
-- =============================================================================

-- Check index usage statistics
SELECT
    schemaname,
    relname::regclass AS tablename,
    indexrelname AS indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname IN ('stock_history', 'etf_history')
ORDER BY relname, indexrelname;

-- Expected output should show:
-- - idx_stock_symbol_date (existing index)
-- - idx_stock_date_symbol (new index)
-- - idx_etf_symbol_date (existing index)
-- - idx_etf_date_symbol (new index)

-- =============================================================================
-- Performance verification
-- =============================================================================

-- Test query with EXPLAIN ANALYZE to verify index usage
EXPLAIN ANALYZE
SELECT *
FROM stock_history
WHERE date >= '2020-01-01'
  AND date <= '2024-12-31'
  AND symbol IN ('000001.SZ', '000002.SZ', '600000.SH')
ORDER BY date, symbol;

-- Expected: Should use idx_stock_date_symbol with Bitmap Index Scan
-- or Index Scan depending on selectivity

-- =============================================================================
-- Monitor index effectiveness
-- =============================================================================

-- After running queries for some time, check index usage:
SELECT
    schemaname,
    relname::regclass AS tablename,
    indexrelname AS indexname,
    idx_scan AS index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND relname IN ('stock_history', 'etf_history')
ORDER BY idx_scan DESC;

-- This will show which indexes are actually being used
-- Unused indexes can be dropped to save space and improve write performance

-- =============================================================================
-- Cleanup (Optional - only if indexes are not used)
-- =============================================================================

-- If monitoring shows idx_stock_date or idx_etf_date are never used,
-- consider removing them to save disk space and reduce write overhead:
--
-- DROP INDEX CONCURRENTLY IF EXISTS idx_stock_date;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_etf_date;
