---
name: arxiv-paper-pipeline
description: 从 arxiv q-fin 拉取最新论文并走完"下载→解析→A股适用性判断→策略/回测代码生成→回测→汇总"的完整流水线。当用户说"处理下一篇论文 / 跑一下 arxiv pipeline / 把这篇 arxiv 论文做成 A 股策略"时使用。
---

# arxiv-paper-pipeline

> **重要**：当前 skill 是历史保留的薄壳。完整 pipeline 已迁移到 Python 入口
> `aitrader.app.cli.arxiv_pipeline`，**LLM 自动判断 + 生成 select_fn**。

## 推荐用法

```bash
# 默认：拉近 14 天 q-fin 论文 → judge → generate → backtest → aggregate
python -m aitrader.app.cli.arxiv_pipeline

# 可选参数
python -m aitrader.app.cli.arxiv_pipeline --since 30d --max-papers 5
python -m aitrader.app.cli.arxiv_pipeline --paper 2604.99999 --rerun
python -m aitrader.app.cli.arxiv_pipeline --steps fetch,aggregate --no-llm
python -m aitrader.app.cli.arxiv_pipeline --rerun-legacy --steps generate,backtest,aggregate
python -m aitrader.app.cli.arxiv_pipeline --dry-run
```

或安装后直接：

```bash
pip install -e .
aitrader-arxiv --since 14d
```

## 产物落盘位置

```
papers/arxiv/<arxiv_id>.pdf
papers/arxiv/processed/<arxiv_id>/
  ├─ 00_meta.json            # pipeline 状态 + arxiv 元数据
  ├─ 01_paper.md             # PDF 解析全文
  ├─ 02_applicability.md     # LLM 判断
  ├─ 03_strategy_code.py     # LLM 生成（spec + run_research 调用）
  ├─ select_fn.py            # LLM 生成
  ├─ 04_backtest_summary.md  # run_research 输出
  └─ *.csv / *.json / *.png  # run_research 标准产物
papers/arxiv/processed/_aggregate/
  ├─ cross_paper_comparison.md
  └─ pipeline_status.json    # 各篇 status / last_error 摘要
```

## 配置

LLM 通过环境变量配置（参考根目录 `.env.example`）：

| 变量 | 默认值 |
|---|---|
| `LLM_API_KEY` | 兜底用 `model.py` 里的 hardcoded key |
| `LLM_BASE_URL` | `https://api.xiaocaseai.com/v1` |
| `LLM_MODEL` | `gpt-5.4` |
| `LLM_TIMEOUT` / `LLM_MAX_TOKENS` / `LLM_TEMPERATURE` | 600 / 32768 / 1.0 |

PDF 解析优先走 `docu_assistant`（`scripts/file_parse.py`），失败回落 `pdfplumber`。

## 遗留脚本

`scripts/arxiv_paper_pipeline.py` 已被新 pipeline 覆盖，仍可单独运行作为
"只拉取 + 只解析" 的快速调试入口；新工作请走 CLI。

`scripts/file_parse.py` / `scripts/us3_tools.py` 仍被新 pipeline 复用。

## 何时使用

触发词示例：

- "处理下一篇 arxiv 论文" / "跑一下 arxiv pipeline"
- "把 <arxiv URL / ID> 做成一个 A 股策略"
- "近 N 天的 q-fin 论文跑一遍"

直接调 CLI 即可，不需要 Claude 介入手写 select_fn。
