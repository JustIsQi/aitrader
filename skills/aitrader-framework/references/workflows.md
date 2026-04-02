# 常用工作流

## 环境与数据库

最小运行前提：

```bash
pip install -r requirements.txt
python scripts/init_postgres_db.py init
```

数据库通常通过 `.env` 里的 `DATABASE_URL` 提供，例如：

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/aitrader
```

## 通用回测工作流

1. 准备或确认数据库里已有行情数据
2. 编写或修改返回 `Task` 的策略函数
3. 用 `Engine().run(task)` 跑单策略回测
4. 需要批量运行时，再接入策略发现器和信号流水线

示例命令：

```bash
python examples/ashare_strategy_example.py ashare_multifactor
```

## A股信号流水线

入口：

```bash
python run_ashare_signals.py
python run_ashare_signals.py --workers 3
python run_ashare_signals.py --force-backtest --workers 3
```

关键信息：

- 脚本会先加载 A股策略，再并发回测，再保存指标，再生成信号
- 当前实现优先线程池而不是进程池，因为数据库连接池需要共享
- 默认并发数较小，目的是控制 8GB 机器上的内存占用
- 自定义并发数时要注意代码里对 `workers` 的上限限制

## 短线 A股选股流水线

入口：

```bash
python run_short_term_signals.py
python run_short_term_signals.py 20260120
python run_short_term_signals.py 20260120 --fetch-only
python run_short_term_signals.py 20260120 --signals-only
python run_short_term_signals.py 20260120 --force-refresh
```

主链路：

1. 获取或复用板块资金流数据
2. 计算板块评分
3. 在强势板块内做追涨和低吸选股
4. 计算仓位、止损、止盈和开仓触发条件
5. 写入数据库操作清单

调阈值时优先改 `short_term_config/short_term_config.py`，不要把阈值硬编码回脚本。

## 数据层约束

- AITrader 是 PostgreSQL first 设计，不是 CSV first
- `DbDataLoader` 支持批量读和缺数自动补下载
- 如果发现 `adjust_type` 不一致，先统一 loader、pipeline、strategy 的传递链路，再怀疑指标逻辑
- 批量查询或自动下载问题，先看数据层，不要先改策略

## 迁移到别的仓库时的建议

- 保留数据库门面层，哪怕底层换成别的数据库
- 保留批量读接口，不要退化成逐标的循环查询
- 如果目标仓库不用 AKShare，先抽象出统一的数据提供接口，再替换实现
