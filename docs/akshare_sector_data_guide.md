# akshare板块数据获取说明

## ✅ 可用功能

akshare **可以**成功获取板块数据,但有以下限制:

### 1. 实时板块资金流数据 ✅

**函数**: `ak.stock_fund_flow_industry(symbol='即时')`

**返回数据**:
- 90个行业板块
- 包含: 行业名称、行业指数、涨跌幅、流入资金、流出资金、净额、公司家数、领涨股等

**示例**:
```python
import akshare as ak
df = ak.stock_fund_flow_industry(symbol='即时')
print(df.head())
```

**输出**:
```
   序号     行业    行业指数  行业-涨跌幅    流入资金  流出资金     净额  ...
0   1    贵金属   6128.47    9.24  127.96  114.48   13.47  ...
1   2  能源金属  33247.40    4.01   90.82   67.04   23.78  ...
```

### 2. 概念板块资金流 ✅

**函数**: `ak.stock_fund_flow_concept(symbol='即时')`

**返回数据**:
- 387个概念板块
- 包含类似的资金流数据

### 3. 板块列表 ✅

**函数**: `ak.stock_sector_spot(indicator='新浪行业')`

**返回数据**:
- 49个行业板块
- 包含板块名称、公司家数、平均价格、涨跌幅等

---

## ⚠️ 重要限制

### 1. 不支持历史数据查询

akshare的板块资金流API **只支持"即时"数据**,不支持历史日期查询!

**错误示例**:
```python
# ❌ 这样不行 - 不支持历史日期
df = ak.stock_fund_flow_industry(symbol='20240115')
```

**正确示例**:
```python
# ✅ 只能这样 - 获取即时数据
df = ak.stock_fund_flow_industry(symbol='即时')
```

---

## 🔧 当前系统的工作方式

### 实时模式 (收盘后运行)

在交易日收盘后(如下午3点后)运行:

```bash
python scripts/generate_short_term_signals.py
```

**流程**:
1. 获取当日板块资金流数据 (即时)
2. 结合数据库中的历史价格数据计算技术指标
3. 生成交易计划
4. 保存到数据库

### 历史回测模式

对于历史日期,系统会使用"全市场"模式:

```bash
python scripts/generate_short_term_signals.py 20240115  # 历史日期
```

**流程**:
1. akshare无法获取历史板块数据 → 返回空
2. 自动切换到"全市场"模式
3. 使用全市场的技术指标进行选股
4. 生成交易计划

---

## 💡 建议

### 方案1: 收盘后运行 (推荐)

设置定时任务,在每个交易日收盘后(如15:30或16:00)自动运行:

```bash
# 编辑crontab
crontab -e

# 添加以下行
30 15 * * 1-5 cd /home/code/aitrader && python scripts/generate_short_term_signals.py >> logs/daily_signals.log 2>&1
```

### 方案2: 手动运行

在每个交易日收盘后手动运行:

```bash
python scripts/generate_short_term_signals.py
```

### 方案3: 建立板块数据库

如果需要支持历史回测,可以:

1. **每日保存板块数据到数据库**
   - 收盘后运行脚本,保存当日板块资金流数据
   - 积累历史板块数据

2. **使用数据库中的板块数据进行回测**
   - 修改`sector_analyzer.py`,优先从数据库读取历史板块数据
   - 只有数据库中没有时才调用akshare

---

## 📊 数据字段映射

### akshare → 系统字段

| akshare字段 | 系统字段 | 说明 |
|------------|---------|------|
| 行业 | sector_name | 板块名称 |
| 净额 | main_net_inflow | 主力净流入(单位:亿) |
| 流入资金 | main_inflow | 主力流入(单位:亿) |
| 流出资金 | main_outflow | 主力流出(单位:亿) |
| 行业-涨跌幅 | change_pct | 涨跌幅(%) |
| 行业指数 | sector_index | 板块指数 |

### 单位转换

```python
# akshare返回单位是"亿",系统使用"万元"
main_net_inflow_wan = main_net_inflow_yi * 10000
```

---

## ✅ 总结

1. **akshare可以获取板块数据** - 功能正常!
2. **仅支持即时数据** - 不支持历史日期查询
3. **系统已实现fallback** - 历史日期自动使用"全市场"模式
4. **推荐使用方式** - 收盘后运行,获取当日板块数据进行选股

**系统已完全可用!** 🎉
