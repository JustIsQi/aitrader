# ETF数据自动更新系统

## 功能说明

本系统用于自动更新ETF历史数据，每天收盘后一小时（16:00）自动获取最新的ETF行情数据并追加到数据文件中。

## 文件说明

- **auto_update_etf_data.py** - ETF数据更新主脚本
- **setup_cron.sh** - Linux/Mac定时任务设置脚本
- **setup_scheduled_task.ps1** - Windows定时任务设置脚本
- **etf_symbols.txt** - ETF代码列表（自动生成）

## 使用方法

### 方法一：手动运行

直接运行更新脚本：

```bash
python auto_update_etf_data.py
```

### 方法二：Linux/Mac 设置定时任务

1. 给脚本添加执行权限：

```bash
chmod +x setup_cron.sh
```

2. 运行设置脚本：

```bash
./setup_cron.sh
```

3. 查看定时任务：

```bash
crontab -l
```

4. 查看日志：

```bash
tail -f logs/etf_update.log
```

### 方法三：Windows 设置定时任务

1. 以管理员身份打开PowerShell

2. 运行设置脚本：

```powershell
.\setup_scheduled_task.ps1
```

如果遇到执行策略限制，先运行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

3. 在任务计划程序中查看任务（Win+R 输入 taskschd.msc）

## ETF列表

当前包含以下26个ETF（来自backtrader_engine.py）：

```
563300.SH  - 中证2000ETF
159509.SZ  - 中证2000ETF(华夏)
518880.SH  - 黄金ETF
513100.SH  - 纳指ETF
513520.SH  - 纳指ETF(华夏)
588000.SH  - 科创50ETF
513330.SH  - 德国ETF
512100.SH  - 中证1000ETF
162719.SZ  - 跨境ETF
513030.SH  - 德国30(DAX)
513380.SH  - 香港ETF
513290.SH  - 红利ETF
159560.SZ  - 豆粕ETF
588100.SH  - 科创100ETF
513040.SH  - H股ETF
561600.SH  - REITs基金
515880.SH  - 通信ETF
513090.SH  - 日本ETF
159819.SZ  - 新能源车ETF
515790.SH  - 光伏ETF
515030.SH  - 新能源车ETF
159752.SZ  - 光伏ETF(广发)
159761.SZ  - 新能源ETF
512480.SH  - 半导体ETF
560800.SH  - 红利低波ETF
513500.SH  - 标普500
```

## 数据存储

数据保存在 `./data/akshare_data/` 目录下，文件命名格式：`{代码}_history.csv`

例如：
- `510300.SH_history.csv`
- `513100.SH_history.csv`

## 更新逻辑

1. **首次运行**：如果数据文件不存在，会下载全部历史数据
2. **增量更新**：如果文件已存在，只下载并追加新的数据
3. **智能跳过**：如果数据已是最新的（最后日期为今天或昨天），会跳过更新
4. **错误处理**：单个ETF更新失败不影响其他ETF的更新

## 定时任务管理

### Linux/Mac

```bash
# 查看定时任务
crontab -l

# 编辑定时任务
crontab -e

# 删除所有定时任务
crontab -r

# 查看日志
tail -f logs/etf_update.log

# 手动运行
python auto_update_etf_data.py
```

### Windows

```powershell
# 查看任务详情
Get-ScheduledTask -TaskName "ETF数据自动更新"

# 查看任务历史
Get-ScheduledTaskInfo -TaskName "ETF数据自动更新"

# 手动运行任务
Start-ScheduledTask -TaskName "ETF数据自动更新"

# 禁用任务
Disable-ScheduledTask -TaskName "ETF数据自动更新"

# 启用任务
Enable-ScheduledTask -TaskName "ETF数据自动更新"

# 删除任务
Unregister-ScheduledTask -TaskName "ETF数据自动更新" -Confirm:$false

# 或者在任务计划程序中手动管理 (Win+R 输入 taskschd.msc)
```

## 注意事项

1. **网络连接**：需要稳定的网络连接来获取数据
2. **代理设置**：如果使用代理，请确保 `get_data.py` 中的代理配置正确
3. **节假日**：脚本会在每个工作日16:00运行，即使在非交易日也会执行（会自动跳过）
4. **数据质量**：数据来源于akshare，可能与实际交易数据有延迟
5. **磁盘空间**：确保有足够的磁盘空间存储数据

## 测试

首次设置后，建议先手动运行一次测试：

```bash
python auto_update_etf_data.py
```

检查是否正常下载数据，然后再设置定时任务。

## 故障排除

### 问题：无法获取数据

**解决方案**：
1. 检查网络连接
2. 检查代理配置（`get_data.py` 中的 PROXY_POOL）
3. 查看日志文件了解具体错误

### 问题：定时任务未执行

**解决方案**：
1. Linux: 检查cron服务是否运行 `systemctl status cron`
2. Windows: 检查任务计划程序服务是否运行
3. 检查系统时间是否正确

### 问题：数据未更新

**解决方案**：
1. 检查数据文件路径是否正确
2. 手动运行脚本查看详细输出
3. 确认akshare接口是否正常

## 自定义配置

如需修改ETF列表，编辑 `auto_update_etf_data.py` 中的 `ETF_SYMBOLS` 列表。

如需修改执行时间，编辑 `setup_cron.sh` 或 `setup_scheduled_task.ps1` 中的时间设置。
