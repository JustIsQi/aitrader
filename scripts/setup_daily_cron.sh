#!/bin/bash

# 配置每日信号生成定时任务（下午8点）
# 使用方式: sudo ./setup_daily_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_SCRIPT="${SCRIPT_DIR}/run_signal_with_service_restart.sh"
PROJECT_DIR="/data/home/yy/code/aitrader"

echo "=========================================="
echo "配置每日信号生成定时任务"
echo "=========================================="
echo ""

# 检查脚本是否存在
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "错误: 找不到脚本 $CRON_SCRIPT"
    exit 1
fi

# 检查脚本是否有执行权限
if [ ! -x "$CRON_SCRIPT" ]; then
    echo "添加执行权限..."
    chmod +x "$CRON_SCRIPT"
fi

# 创建 cron 任务
# 每天 20:00 (工作日: 周一到周五)
CRON_JOB="0 20 * * 1-5 ${CRON_SCRIPT} >> ${PROJECT_DIR}/logs/cron_task.log 2>&1"

echo "计划添加的 cron 任务:"
echo "$CRON_JOB"
echo ""

# 询问用户是否继续
read -p "是否添加此定时任务? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 检查是否已存在相同的任务
if crontab -l 2>/dev/null | grep -q "run_signal_with_service_restart.sh"; then
    echo "警告: 检测到已存在的信号生成任务"
    echo ""
    echo "当前相关任务:"
    crontab -l 2>/dev/null | grep "run_signal_with_service_restart.sh" || true
    echo ""
    read -p "是否要替换现有任务? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi

    # 删除旧任务
    echo "删除旧任务..."
    crontab -l 2>/dev/null | grep -v "run_signal_with_service_restart.sh" | crontab -
fi

# 添加新的 cron 任务
echo "添加新的定时任务..."
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "=========================================="
echo "✓ 定时任务配置成功!"
echo "=========================================="
echo ""
echo "任务详情:"
echo "  - 执行时间: 每个工作日 20:00"
echo "  - 执行脚本: $CRON_SCRIPT"
echo "  - 日志文件: ${PROJECT_DIR}/logs/cron_task.log"
echo ""
echo "查看当前所有定时任务:"
echo "  crontab -l"
echo ""
echo "查看任务日志:"
echo "  tail -f ${PROJECT_DIR}/logs/cron_task.log"
echo ""
echo "手动测试脚本:"
echo "  $CRON_SCRIPT"
echo ""
