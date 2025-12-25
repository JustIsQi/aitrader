#!/bin/bash
# 设置ETF数据自动更新定时任务

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 日志文件
LOG_FILE="$SCRIPT_DIR/logs/etf_update.log"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 设置定时任务：每个交易日收盘后一小时更新（周一至周五 16:00）
# 注意：这里假设每天16:00执行，实际可能需要根据节假日调整
CRON_JOB="0 16 * * 1-5 cd $SCRIPT_DIR && /usr/bin/python3 auto_update_etf_data.py >> $LOG_FILE 2>&1"

# 检查是否已存在相同的定时任务
if crontab -l 2>/dev/null | grep -q "auto_update_etf_data.py"; then
    echo "检测到已存在的ETF更新定时任务"
    echo "是否要替换？(y/n)"
    read -r answer
    if [ "$answer" != "y" ]; then
        echo "取消操作"
        exit 0
    fi

    # 删除旧的定时任务
    crontab -l 2>/dev/null | grep -v "auto_update_etf_data.py" | crontab -
fi

# 添加新的定时任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "定时任务设置成功！"
echo "执行时间: 周一至周五 16:00"
echo "日志文件: $LOG_FILE"
echo ""
echo "当前所有定时任务:"
crontab -l
echo ""
echo "你可以使用以下命令管理定时任务:"
echo "  查看定时任务: crontab -l"
echo "  编辑定时任务: crontab -e"
echo "  删除定时任务: crontab -r"
echo "  查看日志: tail -f $LOG_FILE"
