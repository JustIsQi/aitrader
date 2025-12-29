#!/bin/bash

# AITrader 信号生成脚本 - 带 Web 服务重启
# 功能：停止 Web 服务 -> 生成信号 -> 启动 Web 服务
# 使用：可手动运行或通过 cron 定时执行

set -e  # 遇到错误立即退出

# 配置
PROJECT_DIR="/data/home/yy/code/aitrader"
SERVICE_NAME="aitrader-web"
PYTHON_CMD="/root/miniconda3/bin/python"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/signal_generation.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 创建日志目录
mkdir -p "$LOG_DIR"

# 开始日志
echo "" | tee -a "$LOG_FILE"
echo "====================================================================================================" | tee -a "$LOG_FILE"
echo "信号生成任务开始: $TIMESTAMP" | tee -a "$LOG_FILE"
echo "====================================================================================================" | tee -a "$LOG_FILE"

# 切换到项目目录
cd "$PROJECT_DIR" || {
    log_error "无法切换到项目目录: $PROJECT_DIR"
    exit 1
}

# 1. 检查并停止 Web 服务
log_info "检查 Web 服务状态..."

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "Web 服务正在运行，准备停止..."
    sudo systemctl stop "$SERVICE_NAME"

    # 等待服务完全停止
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_error "Web 服务停止失败"
        exit 1
    else
        log_info "Web 服务已成功停止"
    fi
else
    log_warn "Web 服务未运行，跳过停止步骤"
fi

# 2. 生成交易信号
log_info "开始生成交易信号..."
echo "" | tee -a "$LOG_FILE"

if $PYTHON_CMD run_multi_strategy_signals.py --save-to-db >> "$LOG_FILE" 2>&1; then
    log_info "交易信号生成成功"
else
    log_error "交易信号生成失败，请检查日志: $LOG_FILE"

    # 即使信号生成失败，也尝试重启 Web 服务
    log_warn "尝试重启 Web 服务..."
    sudo systemctl start "$SERVICE_NAME"

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Web 服务已重启"
    else
        log_error "Web 服务重启失败"
    fi

    exit 1
fi

echo "" | tee -a "$LOG_FILE"

# 3. 重新启动 Web 服务
log_info "准备启动 Web 服务..."

if sudo systemctl start "$SERVICE_NAME"; then
    # 等待服务启动
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Web 服务已成功启动"

        # 显示服务状态
        log_info "服务状态:"
        sudo systemctl status "$SERVICE_NAME" --no-pager | tee -a "$LOG_FILE"
    else
        log_error "Web 服务启动失败"
        exit 1
    fi
else
    log_error "Web 服务启动命令执行失败"
    exit 1
fi

# 完成
TIMESTAMP_END=$(date '+%Y-%m-%d %H:%M:%S')
echo "" | tee -a "$LOG_FILE"
echo "====================================================================================================" | tee -a "$LOG_FILE"
echo "信号生成任务完成: $TIMESTAMP_END" | tee -a "$LOG_FILE"
echo "====================================================================================================" | tee -a "$LOG_FILE"

log_info "所有操作已完成！"
