#!/bin/bash
# DuckDB 集成快速启动脚本

echo "======================================================================"
echo "DuckDB 集成 - 快速启动"
echo "======================================================================"

# 1. 安装依赖
echo ""
echo "[1/3] 安装 Python 依赖包..."
pip install duckdb tqdm -q
echo "✅ 依赖安装完成"

# 2. 创建数据库目录
echo ""
echo "[2/3] 创建数据库目录..."
mkdir -p /data/home/yy/data/duckdb
echo "✅ 目录创建完成"

# 3. 导入历史数据
echo ""
echo "[3/3] 导入历史数据到 DuckDB..."
echo "提示: 首次导入可能需要几分钟..."
python import_to_duckdb.py

# 4. 测试数据库
echo ""
echo "======================================================================"
echo "测试数据库连接..."
echo "======================================================================"
python test_duckdb.py

echo ""
echo "======================================================================"
echo "🎉 DuckDB 集成设置完成！"
echo "======================================================================"
echo ""
echo "数据库文件: /data/home/yy/data/duckdb/trading.db"
echo ""
echo "后续操作:"
echo "  1. 日常更新: python auto_update_etf_data.py"
echo "  2. 查看文档: cat DUCKDB_GUIDE.md"
echo "  3. 测试功能: python test_duckdb.py"
echo ""
