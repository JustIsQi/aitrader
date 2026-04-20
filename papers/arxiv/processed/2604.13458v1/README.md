# 总结说明：2604.13458v1

## 论文信息
- **标题**: Interpretable Systematic Risk around the Clock
- **作者**: Songrun He
- **ArXiv ID**: 2604.13458v1
- **发布日期**: 2026-04-15
- **适用性**: ❌ 不适用于A股市场

## 不适用原因

该论文需要：
1. 15分钟高频tick数据（仓库仅有日频数据）
2. 24小时市场覆盖（A股缺乏夜盘期货整合）
3. 高频新闻流（无对应数据源）
4. LLM基础设施（Qwen3-235B-A22B on 4×H100）
5. 连续时间Fama-MacBeth回归（超出仓库DSL能力）

此外，A股10%涨跌停限制会扭曲跳跃识别，做空限制使零成本多空组合无法实施。

## 文件说明

- `applicability_judgment.md`: 详细的适用性分析（由agent生成）
- `02_parsed_content.md`: 论文原文解析
- `03_strategy_code.py`: 未生成（不适用）
- `04_backtest_summary.md`: 未生成（不适用）

## 论文核心方法

使用LLM将市场跳跃分类为5类（宏观、公司、国际、政策、地缘），构建纯因子模拟组合。在美股1997-2020实现Sharpe 0.95。

## 建议

该方法不适合A股。如对系统性风险感兴趣，建议使用A股可用的方法：
1. Fama-French三因子/五因子
2. 行业轮动因子
3. 宏观经济指标（PMI、CPI等）
4. 政策事件研究
