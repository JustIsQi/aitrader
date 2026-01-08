# AITrader 数据管理指南

## 目录
1. [数据库架构](#1-数据库架构)
2. [数据更新流程](#2-数据更新流程)
   - [2.0 历史数据下载脚本（首次使用）](#20-历史数据下载脚本首次使用)
   - [2.1 统一更新脚本（日常增量更新）](#21-统一更新脚本日常增量更新)
   - [2.2 专用更新脚本](#22-专用更新脚本)
   - [2.3 数据下载器详解](#23-数据下载器详解)
3. [定时任务配置](#3-定时任务配置)
4. [Python API 使用](#4-python-api-使用)
5. [数据库维护](#5-数据库维护)
6. [基本面数据系统](#6-基本面数据系统)
7. [故障排除](#7-故障排除)
8. [附录](#8-附录)

---

## 1. 数据库架构

### 1.1 为什么选择 PostgreSQL

AITrader 使用 PostgreSQL 作为主数据库，具有以下优势：

- ✅ **企业级数据库**: 成熟稳定，支持 ACID 事务
- ✅ **高并发**: 支持真正的并发读写访问
- ✅ **高性能**: 优化的查询引擎，索引加速
- ✅ **持久化**: 磁盘存储，重启不丢失数据
- ✅ **ORM 支持**: SQLAlchemy 提供类型安全的数据操作

### 1.2 数据库表结构

PostgreSQL 数据库: `aitrader`

#### 核心表（历史行情）

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| **etf_history** | ETF 历史行情 | symbol, date, open, high, low, close, volume |
| **stock_history** | 股票历史行情 | symbol, date, open, high, low, close, volume |
| **stock_fundamental_daily** | 基本面数据 | symbol, date, pe_ratio, pb_ratio, roe, total_mv |

#### 配置表（代码清单）

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| **etf_codes** | ETF 代码清单 | symbol, name, list_date, fund_type |
| **stock_codes** | 股票代码清单 | symbol, name, list_date, industry, market |
| **stock_metadata** | 股票元数据 | symbol, name, sector, industry, is_st |

#### 交易表

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| **transactions** | 交易记录 | symbol, buy_sell, quantity, price, trade_date |
| **positions** | 当前持仓 | symbol, quantity, avg_cost, current_price |
| **trader** | 交易信号 | symbol, signal_type, price, create_date |

#### 缓存表

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| **factor_cache** | 因子值缓存 | symbol, date, factor_name, factor_value |

### 1.3 数据库连接配置

**配置文件**: `database/models/base.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 数据库连接
DATABASE_URL = "postgresql://user:password@localhost:5432/aitrader"
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine)
```

**使用示例**:
```python
from database.pg_manager import get_db

db = get_db()
```

---

## 2. 数据更新流程

### 2.0 历史数据下载脚本（首次使用）

**脚本文件**: `scripts/download_historical_data.py`

#### 概述

这是一个独立的脚本,用于下载过去N年的ETF历史数据、A股历史数据和A股基本面数据快照。

#### 功能特性

1. **自动初始化**: 自动检查代码表,如果为空则自动初始化
2. **智能下载**: 只下载缺失的数据,支持断点续传
3. **进度跟踪**: 使用tqdm显示实时进度
4. **错误处理**: 单个symbol失败不影响其他,失败代码自动记录
5. **灵活配置**: 支持自定义年份、数据类型和强制重新下载

#### 基本用法

```bash
# 下载默认5年所有数据(ETF + 股票 + 基本面)
python scripts/download_historical_data.py

# 下载3年历史数据
python scripts/download_historical_data.py --years 3

# 只下载ETF和股票历史数据(不下载基本面)
python scripts/download_historical_data.py --data-types etf stock

# 只下载基本面快照
python scripts/download_historical_data.py --data-types fundamental

# 强制重新下载所有数据(覆盖已有数据)
python scripts/download_historical_data.py --force
```

#### 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--years N` | `-y N` | 历史数据年数 | 5 |
| `--data-types` | `-t` | 数据类型: etf, stock, fundamental, all | all |
| `--force` | `-f` | 强制重新下载已有数据 | False |

#### 数据类型说明

- **etf**: ETF历史日线数据
- **stock**: A股历史日线数据
- **fundamental**: A股基本面数据快照(仅最新,不下载历史)
- **all**: 所有数据类型(默认)

#### 智能下载决策

脚本会对每个symbol进行智能判断:

1. **强制模式** (`--force`): 从目标起始日期重新下载所有数据
2. **首次下载**: 数据库无数据,从目标起始日期下载
3. **补充数据**: 数据库有数据但不足N年,补充缺失部分
4. **增量更新**: 数据库有完整历史数据,只下载最新增量
5. **跳过**: 数据库已有完整数据且最新,跳过下载

#### 日期范围

- 默认下载过去5年的数据
- 起始日期对齐到1月1日,使数据更整洁
- 例如: 2026-01-07运行,默认下载2021-01-01至2026-01-07的数据

#### 输出示例

```
************************************************************
历史数据下载流程启动 - 2026-01-07 10:00:00
************************************************************

[阶段0] 检查代码表状态...
  etf_codes:   850 条
  stock_codes: 5234 条
✓ 代码表状态正常

目标日期范围: 2021-01-01 至 2026-01-07 (5年)

============================================================
[阶段1] 下载ETF历史数据
============================================================

待检查: 850 个 ETF
ETF下载: 100%|████████████████████| 850/850 [02:30<00:00, 5.62个/s]

✓ ETF 下载完成!
  总数: 850
  已下载: 0
  跳过: 850
  失败: 0
  新增记录: 0
  耗时: 150.23 秒 (2.5 分钟)
```

#### 断点续传

脚本天然支持断点续传:

1. **中断后重跑**: 如果脚本被中断(Ctrl+C),重新运行会自动跳过已下载的数据
2. **失败重试**: 失败的symbol会在下次运行时自动重试
3. **失败记录**: 所有失败的symbol会保存到 `logs/failed_symbols_*.txt` 文件

#### 数据库表

脚本会操作以下数据库表:

- `etf_history` - ETF历史数据
- `stock_history` - A股历史数据
- `stock_fundamental_daily` - A股基本面数据
- `etf_codes` - ETF代码列表
- `stock_codes` - A股代码列表
- `stock_metadata` - A股元数据

#### 性能说明

- **ETF**: 约850个,预计2-5分钟
- **股票**: 约5000+只,预计30-60分钟
- **基本面**: 约5000+只,预计1分钟

总耗时取决于网络速度和数据量。

#### 常见问题

**Q: 如何只更新最新数据?**

A: 脚本默认就是增量更新模式,只下载缺失的数据。运行即可。

**Q: 如何强制重新下载所有数据?**

A: 使用 `--force` 参数: `python scripts/download_historical_data.py --force`

**Q: 下载中断了怎么办?**

A: 直接重新运行脚本,会自动跳过已下载的数据。

**Q: 基本面数据为什么不下载历史?**

A: 免费数据源(AkShare)不提供历史PE/PB数据。基本面因子主要用于横截面比较,最新数据即可满足需求。

**Q: 如何查看下载进度?**

A: 脚本使用tqdm显示实时进度条,股票下载时每100只还会输出日志。

#### 对比: 与unified_update.py的区别

| 特性 | unified_update.py | download_historical_data.py |
|------|-------------------|----------------------------|
| 用途 | 日常增量更新 | 首次/批量下载历史数据 |
| 日期范围 | 从最新日期开始 | 可配置历史年数(默认5年) |
| 基本面数据 | 最新快照 | 最新快照 |
| 代码表检查 | 支持 | 支持 |
| 强制下载 | 不支持 | 支持(`--force`) |
| 失败记录 | 不保存 | 保存到文件 |

**建议**:
- 首次使用或数据库为空: 运行 `download_historical_data.py`
- 日常更新: 运行 `unified_update.py`

---

### 2.1 统一更新脚本（日常增量更新）

**脚本文件**: `scripts/unified_update.py`

#### 基本用法

```bash
# 完整更新（ETF → 基本面 → 股票）
python scripts/unified_update.py

# 仅更新特定阶段
python scripts/unified_update.py --stage etf
python scripts/unified_update.py --stage fundamental
python scripts/unified_update.py --stage stock

# 组合更新
python scripts/unified_update.py --stage etf --stage fundamental
```

#### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--stage` | 指定阶段（可多次使用） | 全部 |
| `--skip-code-check` | 跳过代码表检查 | False |

> **注意**: 基本面数据只更新最新快照，不下载历史数据。估值因子(PE/PB)主要用于横截面比较，最新数据即可满足需求。

### 2.2 专用更新脚本

#### ETF 数据更新

```bash
# 仅更新 ETF
python scripts/auto_update_etf_data.py --type etf
```

#### 股票数据更新

```bash
# 仅更新股票
python scripts/auto_update_etf_data.py --type stock
```

#### 基本面数据更新

```bash
# 使用模块方式
python -m datafeed.downloaders.fundamental_downloader
```

### 2.3 数据下载器详解

#### EtfDownloader

**文件**: `datafeed/downloaders/etf_downloader.py`

```python
from datafeed.downloaders.etf_downloader import EtfDownloader

downloader = EtfDownloader()
downloader.update_etf_data('510300.SH')  # 更新单个
downloader.update_all_etf_data()          # 更新全部
```

**更新逻辑**:
1. 从 `etf_codes` 表获取代码列表
2. 调用 `akshare` 接口获取最新数据
3. 批量插入数据库（每 100 条提交一次）
4. 自动处理增量更新

#### StockDownloader

**文件**: `datafeed/downloaders/stock_downloader.py`

```python
from datafeed.downloaders.stock_downloader import StockDownloader

downloader = StockDownloader()
downloader.update_stock_data('000001.SZ')  # 更新单个
downloader.update_all_stock_data()         # 更新全部
```

**更新逻辑**:
1. 从 `stock_codes` 表获取代码列表
2. 调用 `akshare` 接口获取历史数据
3. 批量插入数据库
4. 处理停牌、退市等异常情况

#### FundamentalDownloader

**文件**: `datafeed/downloaders/fundamental_downloader.py`

```python
from datafeed.downloaders.fundamental_downloader import FundamentalDownloader

downloader = FundamentalDownloader()

# 更新最新基本面快照数据
downloader.update_fundamental_data()
```

**更新逻辑**:
1. 调用 `ak.stock_zh_a_spot_em()` 一次获取全市场快照
2. 提取 PE、PB、市值等指标
3. 批量插入数据库

**重要说明**:
- ✅ **只更新最新快照**: 估值因子(PE/PB)主要用于横截面比较，最新数据即可满足需求
- ❌ **不下载历史数据**: AkShare 的 `stock_zh_a_hist()` 接口不返回历史 PE/PB 数据
- 💡 **历史数据需求**: 如需历史基本面数据，建议使用 Tushare 等付费数据源

---

## 3. 定时任务配置

### 3.1 统一定时任务（推荐）

#### 一键配置

```bash
cd scripts
chmod +x setup_unified_cron.sh
./setup_unified_cron.sh
```

#### 配置内容

```bash
# 15:30 - 更新ETF和基本面数据
30 15 * * 1-5 cd /path/to/aitrader && python scripts/unified_update.py --stage etf --stage fundamental >> logs/unified_update.log 2>&1

# 16:00 - 更新股票交易数据
0 16 * * 1-5 cd /path/to/aitrader && python scripts/unified_update.py --stage stock >> logs/unified_update.log 2>&1
```

**说明**:
- 每周一至周五执行
- 15:30: ETF + 基本面数据（预计 20-30 分钟）
- 16:00: 股票交易数据（预计 45-60 分钟）

### 3.2 信号生成定时任务

#### 配置脚本

```bash
cd scripts
chmod +x setup_signal_cron.sh
./setup_signal_cron.sh
```

#### 手动配置

```bash
# 编辑定时任务
crontab -e

# 添加以下行（每个交易日 18:00 生成ETF信号）
0 18 * * 1-5 cd /path/to/aitrader && python run_etf_signals.py --save-to-db >> logs/signal_generation.log 2>&1

# 或生成A股信号（需要回测，建议在收盘后运行）
0 20 * * 1-5 cd /path/to/aitrader && python run_ashare_signals.py >> logs/ashare_pipeline.log 2>&1
```

### 3.3 其他定时任务脚本

- **setup_fundamental_cron.sh**: 基本面数据更新定时任务
- **setup_daily_cron.sh**: 每日数据更新定时任务

### 3.4 Cron 基础命令

```bash
# 查看当前定时任务
crontab -l

# 编辑定时任务
crontab -e

# 删除所有定时任务
crontab -r

# 查看 Cron 服务状态
sudo systemctl status cron

# 重启 Cron 服务
sudo systemctl restart cron
```

---

## 4. Python API 使用

### 4.1 下载数据

```python
from datafeed.downloaders.etf_downloader import EtfDownloader
from datafeed.downloaders.stock_downloader import StockDownloader
from datafeed.downloaders.fundamental_downloader import FundamentalDownloader

# ETF 数据
etf_dl = EtfDownloader()
etf_dl.update_etf_data('510300.SH')
etf_dl.update_all_etf_data()

# 股票数据
stock_dl = StockDownloader()
stock_dl.update_stock_data('000001.SZ')
stock_dl.update_all_stock_data()

# 基本面数据
fund_dl = FundamentalDownloader()
fund_dl.update_fundamental_data(['000001.SZ', '000002.SZ'])
fund_dl.update_fundamental_data()  # 全市场
```

### 4.2 查询数据库

```python
from database.pg_manager import get_db
from datetime import date

db = get_db()

# 获取 ETF 历史
df = db.get_etf_history('510300.SH', start_date=date(2025, 1, 1))

# 获取最新信号
signals = db.get_latest_trader_signals(limit=20)

# 获取持仓
positions = db.get_positions()

# 获取基本面数据
fund = db.get_fundamental_daily('000001.SZ')
```

### 4.3 因子计算

```python
from datafeed.factor_fundamental import quality_score, pe_score, pb_score

# PE 评分
pe_scores = pe_score(pe_series)

# PB 评分
pb_scores = pb_score(pb_series)

# 综合质量评分
quality = quality_score(pe, pb, roe)
```

---

## 5. 数据库维护

### 5.1 备份与恢复

#### 备份

```bash
# PostgreSQL 数据库备份
docker exec pg pg_dump -U postgres aitrader > backup_$(date +%Y%m%d).sql
```

#### 恢复

```bash
# 从备份恢复
docker exec -i pg psql -U postgres aitrader < backup_20260101.sql
```

### 5.2 监控数据库大小

```bash
# 查看各表大小
docker exec pg psql -U postgres -d aitrader -c "
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### 5.3 清理旧数据

```python
from database.pg_manager import get_db

db = get_db()

# 清理旧基本面数据（保留最近30天）
db.cleanup_old_fundamental(keep_days=30)

# 清理因子缓存
db.clear_factor_cache()
```

### 5.4 性能优化

**已启用的优化**:
- ✅ **连接池**: pool_size=10, max_overflow=20
- ✅ **索引**: symbol, date 列自动创建索引
- ✅ **批量操作**: 使用批量方法插入数据
- ✅ **因子缓存**: 常用因子计算结果缓存

**查询优化建议**:
- 使用日期范围限制查询
- 避免全表扫描
- 使用批量方法而非循环单条查询

---

## 6. 基本面数据系统

### 6.1 系统简介

基本面数据系统提供 A 股财务数据获取、存储和因子计算功能。

**特性**:
- **覆盖范围**: 全市场 5700+ 只 A 股
- **数据类型**: 最新快照数据（每日更新）
- **更新频率**: 每个交易日收盘后自动更新
- **更新速度**: 约 10-15 秒完成全市场更新

**重要说明**:
- ✅ **只存储最新快照**: 保留最近几天的数据用于回测和信号生成
- ❌ **不提供历史估值**: 免费数据源(AkShare)不支持历史 PE/PB 下载
- 💡 **适用场景**: 横截面选股、实时估值排序、因子打分

### 6.2 数据字段

| 字段 | 说明 | 数据来源 | 更新频率 |
|-----|------|---------|---------|
| pe_ratio | 市盈率(动态) | stock_zh_a_spot_em | 每日 |
| pb_ratio | 市净率 | stock_zh_a_spot_em | 每日 |
| total_mv | 总市值(亿) | stock_zh_a_spot_em | 每日 |
| circ_mv | 流通市值(亿) | stock_zh_a_spot_em | 每日 |
| roe | 净资产收益率 | 待补充 | - |
| roa | 总资产收益率 | 待补充 | - |
| profit_margin | 利润率 | 待补充 | - |

**注意**: ROE、ROA 等财务指标需要额外的财务数据接口，目前版本暂未实现。

### 6.3 为什么不需要历史 PE/PB 数据？

1. **估值因子是横截面比较**: 在某个时间点比较所有股票的PE/PB，选出相对低估的股票
2. **回测时使用历史快照即可**: 回测时只需要"回测当天的"最新基本面数据
3. **估值变化快**: PE/PB 随股价每日变化，历史数据参考价值有限
4. **数据源限制**: 免费数据源（AkShare）不提供历史估值数据

如果确实需要历史基本面数据，建议：
- 使用 **Tushare** 等付费数据源（提供完整历史财务数据）
- 使用 **JoinQuant** 聚宽平台（提供高质量基本面数据）
- 自己计算：从历史行情获取收盘价和市值，配合财报数据计算 PB = 总市值 / 净资产

### 6.4 可用基本面因子

#### 估值因子

| 因子 | 说明 | 使用示例 |
|-----|------|---------|
| `pe` | 市盈率 | `pe < 20` |
| `pb` | 市净率 | `pb < 2` |
| `pe_score()` | PE 评分（倒数） | `pe_score(pe) > 0.05` |
| `pb_score()` | PB 评分（倒数） | `pb_score(pb) > 0.5` |

#### 综合因子

| 因子 | 说明 | 使用示例 |
|-----|------|---------|
| `quality_score(pe, pb, roe)` | 综合质量评分 | `quality_score(pe,pb,roe) > 0.5` |
| `value_score(pe, pb, ps)` | 价值评分 | `value_score(pe,pb,ps) > 0.3` |

**注意**: ROE 等财务指标暂不可用，建议仅使用 PE、PB、市值等估值因子。

### 6.5 使用示例

#### 更新基本面数据

```bash
# 更新全市场A股最新快照
python scripts/unified_update.py --stage fundamental
```

#### 在策略中使用

```python
from core.backtrader_engine import Task, Engine

t = Task()
t.name = '价值选股策略'
t.ashare_mode = True

# 使用估值因子筛选
t.select_buy = [
    'pe < 20',           # PE < 20
    'pb < 2',            # PB < 2
    'total_mv > 100'     # 市值 > 100亿
]
t.buy_at_least_count = 2

# 使用估值因子排序（低估值优先）
t.order_by_signal = 'pe_score(pe) + pb_score(pb)'
t.order_by_topK = 5

e = Engine()
e.run(t)
```

**推荐策略**:
- ✅ 使用 PE、PB、市值等估值因子进行选股和排序
- ✅ 结合动量、趋势等因子构建多因子策略
- ❌ 暂不使用 ROE、ROA 等财务指标（数据暂不可用）

---

## 7. 故障排除

### 7.1 数据库连接失败

**症状**: 无法连接到 PostgreSQL

**解决方案**:

```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 重启数据库
docker restart pg

# 检查数据库日志
docker logs pg
```

### 7.2 数据下载失败

**症状**: 更新数据时没有下载到新数据

**可能原因**:
1. 市场休市（周末、节假日）
2. 网络连接问题
3. AkShare API 限制

**解决方案**:

```bash
# 查看更新日志
tail -f logs/unified_update.log

# 检查网络连接
ping api.akshare.xyz

# 手动测试单个标的
python scripts/get_data.py 510300
```

### 7.3 定时任务未执行

**症状**: Cron 定时任务没有运行

**解决方案**:

```bash
# 检查 Cron 服务状态
sudo systemctl status cron

# 查看当前定时任务
crontab -l

# 查看 Cron 日志
sudo grep CRON /var/log/syslog
```

### 7.4 数据库查询缓慢

**症状**: 数据库查询响应时间长

**解决方案**:

```bash
# 检查是否启用了 PostgreSQL
python -c "from database.pg_manager import get_db; print(get_db())"

# 重建索引
docker exec pg psql -U postgres -d aitrader -c "REINDEX DATABASE aitrader;"

# 清理缓存
db.clear_factor_cache()
```

---

## 8. 附录

### 8.1 数据文件位置

| 类型 | 路径 |
|------|------|
| 数据库模型 | `database/models/` |
| 下载器 | `datafeed/downloaders/` |
| 更新脚本 | `scripts/` |
| 日志 | `logs/` |
| 配置 | `.env` |

### 8.2 日志文件

| 日志类型 | 路径 |
|---------|------|
| 统一更新 | `logs/unified_update.log` |
| ETF 更新 | `logs/etf_update.log` |
| 股票更新 | `logs/stock_update.log` |
| 基本面更新 | `logs/fundamental_update.log` |
| 信号生成 | `logs/signal_generation.log` |

### 8.3 环境配置

**.env 文件示例**:

```bash
# PostgreSQL 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=aitrader

# 数据路径
DATA_DIR=/data/home/yy/code/aitrader/data
LOG_DIR=/data/home/yy/code/aitrader/logs
```

### 8.4 基本面数据下载优化

#### 8.4.1 优化概述

基本面数据下载系统经过全面优化，实现了显著的性能提升：

**核心改进**:
- ✅ **一次请求获取全部历史数据**：不再按日期逐个请求
- ✅ **并发下载**：使用 `ThreadPoolExecutor` 实现 10 线程并发
- ✅ **智能去重**：下载前查询最新日期，只下载缺失部分
- ✅ **限流保护**：通过 `RateLimiter` 控制请求频率（10 次/秒）
- ✅ **自动重试**：失败后自动重试 5 次，使用指数退避策略
- ✅ **批量插入**：每 100 只股票批量插入一次

#### 8.4.2 性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 请求数（5447只×5年） | ~7,000,000 | ~5,447 | **99.92% ↓** |
| 预计耗时 | ~8 天 | ~30 分钟 | **99.74% ↓** |
| 重复数据插入 | 是（覆盖） | 否（跳过） | ✓ |
| 并发能力 | 无 | 10 线程 | ✓ |
| 失败重试 | 无 | 5 次 | ✓ |
| 请求频率控制 | 无 | 10 次/秒 | ✓ |

#### 8.4.3 新增组件

##### 限流器 (`datafeed/downloaders/rate_limiter.py`)

实现令牌桶算法，确保每秒不超过 10 次请求：

```python
from datafeed.downloaders.rate_limiter import RateLimiter

# 使用限流器
limiter = RateLimiter(rate=10)  # 每秒10次
with limiter:
    # 执行请求
    pass
```

**特性**:
- 线程安全，使用 `threading.Lock()` 保护共享状态
- 测试通过：10次请求耗时 0.90 秒，符合预期

##### 重试装饰器 (`datafeed/downloaders/retry.py`)

支持失败后自动重试：

```python
from datafeed.downloaders.retry import retry_on_failure

@retry_on_failure(max_attempts=5)
def fetch_data():
    # 可能失败的操作
    pass
```

**特性**:
- 使用指数退避策略：每次重试延迟递增（1s, 2s, 3s, 4s, 5s）
- 测试通过：函数在第 3 次尝试后成功返回

#### 8.4.4 数据库优化

##### 新增查询方法 (`database/pg_manager.py`)

```python
from database.pg_manager import get_db

db = get_db()

# 查询指定股票的基本面数据最新日期
latest_date = db.get_stock_latest_fundamental_date('000001.SZ')
# 返回: '2026-01-01'
```

##### 批量插入优化

```python
# 批量插入，自动跳过重复数据
inserted_count = db.batch_insert_fundamental_if_not_exists(data_list)
# 返回实际插入的新记录数
```

**特性**:
- 使用 `ON CONFLICT DO NOTHING` 跳过重复数据
- 返回实际插入的新记录数

#### 8.4.5 使用方法

##### 下载历史基本面数据

```bash
# 下载 5 年历史数据（首次运行）
python scripts/unified_update.py --stage fundamental --download-history --history-years 5

# 增量更新（后续运行，只下载缺失数据）
python scripts/unified_update.py --stage fundamental --download-history --history-years 5
```

首次运行会下载全部 5 年历史数据，后续运行只会下载缺失的数据。

##### 测试验证

```bash
# 运行测试套件
python tests/test_fundamental_optimized.py
```

测试结果：
- ✅ 限流器测试通过
- ✅ 重试装饰器测试通过
- ✅ 数据库查询方法测试通过

#### 8.4.6 注意事项

1. **线程安全**：所有组件均已考虑线程安全
2. **数据类型**：日期和数值字段自动转换和清洗
3. **错误处理**：单只股票失败不影响整体
4. **日志输出**：详细的进度和统计信息

#### 8.4.7 文件清单

##### 新增文件
- `datafeed/downloaders/rate_limiter.py` - 限流器
- `datafeed/downloaders/retry.py` - 重试装饰器
- `tests/test_fundamental_optimized.py` - 测试套件

##### 修改文件
- `database/pg_manager.py` - 新增 2 个方法
- `datafeed/downloaders/fundamental_downloader.py` - 重构历史下载函数
- `datafeed/downloaders/__init__.py` - 导出新模块

### 8.5 相关文档

- [项目主文档](README.md)
- [使用指南](GUIDE.md)
- [实施计划](PLAN.md)
- [数据库模型](database/models/models.py)

---

**最后更新**: 2026-01-04
