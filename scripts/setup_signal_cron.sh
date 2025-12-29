#!/bin/bash
# 设置多策略信号生成定时任务

SCRIPT_DIR="/data/home/yy/code/aitrader"
LOG_FILE="$SCRIPT_DIR/logs/signal_generation.log"
PYTHON_PATH="/root/miniconda3/bin/python"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 定时任务: 周一至周五 18:00 生成信号并保存到数据库
CRON_JOB="0 18 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH run_multi_strategy_signals.py --save-to-db >> $LOG_FILE 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "run_multi_strategy_signals.py"; then
    echo "检测到已存在的信号生成定时任务"
    echo "旧的任务内容:"
    crontab -l 2>/dev/null | grep "run_multi_strategy_signals.py"
    echo ""
    echo -n "是否要替换? (y/n): "
    read -r answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "取消操作"
        exit 0
    fi

    # 删除旧的定时任务
    crontab -l 2>/dev/null | grep -v "run_multi_strategy_signals.py" | crontab -
    echo "✓ 已删除旧的定时任务"
fi

# 添加新的定时任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✓ 定时任务设置成功！"
echo "执行时间: 周一至周五 18:00"
echo "日志文件: $LOG_FILE"
echo ""
echo "当前所有定时任务:"
crontab -l
echo ""
echo "提示: 使用 'crontab -e' 可以手动编辑定时任务"
echo "使用 'tail -f $LOG_FILE' 可以查看执行日志"
