# 脚本使用说明

本目录包含 AITrader 系统的自动化脚本。

## 📋 可用脚本

### 1. `run_signal_with_service_restart.sh` - 信号生成（带服务重启）

**功能**: 自动停止 Web 服务 → 生成交易信号 → 重启 Web 服务

**特点**:
- ✅ 避免 DuckDB 并发冲突
- ✅ 完整的日志记录
- ✅ 错误处理和状态检查
- ✅ 彩色终端输出

**手动运行**:
```bash
./scripts/run_signal_with_service_restart.sh
```

**日志位置**: `/data/home/yy/code/aitrader/logs/signal_generation.log`

---

### 2. `setup_daily_cron.sh` - 配置每日定时任务

**功能**: 自动配置 cron 定时任务（每个工作日 20:00 执行信号生成）

**使用方法**:
```bash
cd /data/home/yy/code/aitrader/scripts
sudo ./setup_daily_cron.sh
```

**配置详情**:
- **执行时间**: 每个工作日（周一到周五）下午 8:00
- **执行内容**: 运行 `run_signal_with_service_restart.sh`
- **日志文件**: `/data/home/yy/code/aitrader/logs/cron_task.log`

---

### 3. `setup_signal_cron.sh` - 配置定时任务（不带服务重启）

**功能**: 配置 cron 定时任务直接运行信号生成（不重启服务）

**使用方法**:
```bash
cd /data/home/yy/code/aitrader/scripts
./setup_signal_cron.sh
```

**配置详情**:
- **执行时间**: 每个工作日（周一到周五）下午 6:00
- **执行内容**: 运行 `run_multi_strategy_signals.py --save-to-db`
- **特点**: 使用内置的重试机制，不停止 Web 服务

---

## 🚀 快速开始

### 方案 A: 带服务重启的定时任务（推荐）

适合需要确保写入成功的场景。

```bash
# 1. 配置定时任务（每天 20:00）
cd /data/home/yy/code/aitrader/scripts
sudo ./setup_daily_cron.sh

# 2. 验证配置
crontab -l

# 3. 查看日志
tail -f /data/home/yy/code/aitrader/logs/cron_task.log
```

### 方案 B: 不重启服务的定时任务

适合希望 Web 服务持续运行的场景。

```bash
# 1. 配置定时任务（每天 18:00）
cd /data/home/yy/code/aitrader/scripts
./setup_signal_cron.sh

# 2. 验证配置
crontab -l

# 3. 查看日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log
```

### 方案 C: 手动运行

```bash
# 带服务重启
./scripts/run_signal_with_service_restart.sh

# 不带服务重启
cd /data/home/yy/code/aitrader
python run_multi_strategy_signals.py --save-to-db
```

---

## 📊 监控和管理

### 查看定时任务
```bash
crontab -l
```

### 查看执行日志
```bash
# 方案 A 日志
tail -f /data/home/yy/code/aitrader/logs/cron_task.log

# 方案 B 日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log

# 信号生成详细日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log
```

### 管理 Web 服务
```bash
# 查看服务状态
sudo systemctl status aitrader-web

# 停止服务
sudo systemctl stop aitrader-web

# 启动服务
sudo systemctl start aitrader-web

# 重启服务
sudo systemctl restart aitrader-web

# 查看服务日志
sudo journalctl -u aitrader-web -f
```

### 删除定时任务
```bash
# 编辑 crontab
crontab -e

# 删除对应的行，保存退出
```

---

## 🔧 故障排除

### 问题 1: 定时任务未执行

**检查步骤**:
```bash
# 1. 检查 cron 服务
sudo systemctl status cron

# 2. 验证定时任务
crontab -l

# 3. 查看执行日志
tail -f /data/home/yy/code/aitrader/logs/cron_task.log
```

### 问题 2: Web 服务重启失败

**检查步骤**:
```bash
# 1. 查看脚本日志
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log

# 2. 检查服务状态
sudo systemctl status aitrader-web

# 3. 查看服务日志
sudo journalctl -u aitrader-web -n 50
```

### 问题 3: 信号生成失败

**检查步骤**:
```bash
# 1. 查看详细错误
tail -f /data/home/yy/code/aitrader/logs/signal_generation.log

# 2. 手动测试
cd /data/home/yy/code/aitrader
python run_multi_strategy_signals.py --save-to-db

# 3. 检查数据库
ls -la /data/home/yy/data/duckdb/trading.db
```

---

## 📝 自定义配置

### 修改执行时间

编辑 crontab:
```bash
crontab -e
```

Cron 时间格式:
```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 7，0 和 7 都是周日)
│ │ │ │ │
* * * * * 命令
```

示例:
```bash
# 每天下午 8 点
0 20 * * * /path/to/script.sh

# 每个工作日晚上 9 点半
30 21 * * 1-5 /path/to/script.sh

# 每周一、三、五下午 6 点
0 18 * * 1,3,5 /path/to/script.sh
```

### 修改日志位置

编辑 `run_signal_with_service_restart.sh`:
```bash
LOG_DIR="${PROJECT_DIR}/logs"  # 改为你想要的日志目录
```

---

## 🎯 推荐配置

### 个人开发环境
- **方案**: 方案 B（不重启服务）
- **原因**: Web 服务持续可用，内置重试机制足够

### 生产环境
- **方案**: 方案 A（重启服务）
- **原因**: 确保每次写入成功，避免并发问题

### 高频交易
- **方案**: 方案 A + 手动触发
- **原因**: 精确控制执行时机，确保数据一致性

---

## 📞 支持

如遇问题，请查看:
1. 脚本日志文件
2. 主项目 README.md
3. Web 部署指南
