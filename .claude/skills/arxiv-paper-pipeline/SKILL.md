---
name: arxiv-paper-pipeline
description: 从 arxiv q-fin 拉取最新论文并走完"下载→解析→A股适用性判断→策略/回测代码生成"的完整流水线。当用户说"处理下一篇论文 / 跑一下 arxiv pipeline / 把这篇 arxiv 论文做成 A 股策略"时使用。
---

# arxiv-paper-pipeline

把一篇 arxiv q-fin 论文从 URL 走到"可在仓库里跑的 A 股策略"的完整流程。

## 背景

- `scripts/arxiv_paper_pipeline.py` 负责搜索 → 下载 PDF → 解析为 Markdown → 写入索引。
- `scripts/file_parse.py` 封装 `docu_assistant` HTTP 接口 + US3 中转（上传→解析→删除）。
- PDF 解析策略：**docu_assistant API 优先 → pdfplumber fallback**（API 在含大量公式/表格的金融论文上效果明显更好）。
- 产物落盘位置（由脚本自动向上找 `pyproject.toml` 定位仓库根）：
  - PDF：`<repo>/papers/arxiv/<id>.pdf`
  - Markdown：`<repo>/outputs/arxiv/<id>.md`
  - 索引：`<repo>/outputs/arxiv/processed.json`
- 判断 A 股适用性 + 生成策略代码由 Claude 完成，不在脚本内。

### 依赖

- `scripts/us3_tools.py` 封装 US3（Ucloud 对象存储）客户端；skill 内自包含，无需额外路径配置。
- 环境变量（可选覆盖默认值）：
  - `DOCU_API_URL`（默认内网 `http://10.100.0.24:60307/docu_assistant`）
  - `DOCU_API_TOKEN`
  - `DOCU_US3_PREFIX`（默认 `doc_parser/arxiv_pipeline`）

## 何时使用

触发词示例：
- "处理下一篇 arxiv 论文"、"跑一下 arxiv pipeline"
- "把 <arxiv URL / ID> 做成一个 A 股策略"
- "列出 / 重置已处理的 arxiv 论文"

## 流程

### Step 1 — 拉取并解析一篇论文

```bash
python .claude/skills/arxiv-paper-pipeline/scripts/arxiv_paper_pipeline.py
```

默认行为：按 `SEARCH_QUERIES` 搜索 q-fin 下的 AI/ML/因子/强化学习相关论文，按发布日期降序挑出第一篇**未处理**且日期 ≥ `2026-03` 的，下载 PDF、解析为 Markdown、写入 `processed.json`，最后打印 Markdown 路径与摘要。

可选参数：
- `--list`：列出 `processed.json` 中已处理的论文
- `--reset <arxiv_id>`：从索引里删除某篇，让下次运行重新处理
- `--start 2026-01`：覆盖起始年月（默认 `2026-03`）
- `--no-api`：跳过 docu_assistant，直接用 pdfplumber（调试内网不通时用）

处理单篇指定论文（arxiv URL 或 ID）目前**未实现 CLI**——如需要，直接读取已生成的 md 或手工用 `arxiv.Search(id_list=[...])` 调脚本内函数。

### Step 2 — 判断 A 股适用性

读取 Step 1 打印的 Markdown 路径（或 `outputs/arxiv/<id>.md`），给出如下结构化判断，并把结论写进 Claude 的回复里：

- **论文核心**：信号/因子/模型 是什么，用什么数据，OOS 区间与指标。
- **是否适合 A 股**：yes / no / maybe。
- **理由**（逐条）：
  - 数据可得性：是否只需日频 OHLCV / 换手率 / 估值？需不需要新闻、期权、tick？
  - 市场结构匹配：A 股散户主导、T+1、涨跌停、做空受限——论文假设是否冲突？
  - 信号复现复杂度：是否能用仓库 DSL（`ma`、`roc`、`normalize_score` 等）表达？
- **改造建议**：若 maybe/yes，给出最小可行的 A 股版本（简化版因子、权重、持仓数）。

判断时参考仓库里已有的两个范例 —— `src/aitrader/domain/strategy/agentic_turnover.py`（论文 2603.14288v2 的 A 股落地）就是一篇 yes 案例。

### Step 3 — 生成策略 + 回测代码（仅当 Step 2 结论是 yes）

按 `templates/strategy_template.md` 的骨架新建：

1. `src/aitrader/domain/strategy/<slug>.py` — 实现复合信号 + `<slug>_strategy_weekly()`、可选 monthly/conservative 变体。
2. `strategies/stocks_<slug>_selection.py` — 入口 shim，`from aitrader.domain.strategy.<slug> import *`。

关键注意点：
- docstring 第一段必须标明 **ArXiv ID + 论文标题 + 发布日期**（方便后续溯源）。
- `start_date` / `end_date` 沿用现有策略（`20190101` → `20241231`）以便横向对比。
- `t.ashare_mode = True`、`t.ashare_commission = 'v2'` 必填。
- `select_buy` 用 2–4 个**宽松**约束 + `buy_at_least_count`，避免候选池被打空。
- 只用仓库已支持的 DSL（模板第 4 节列出），不要臆造函数。

生成后用 `python -m compileall` 或直接 `python src/aitrader/domain/strategy/<slug>.py` 快速跑一下 `__main__` 段（会真的跑回测，耗时较长，确认要跑再执行）。

### Step 4 — 管理命令速查

| 目的 | 命令 |
|---|---|
| 处理下一篇 | `python .claude/skills/arxiv-paper-pipeline/scripts/arxiv_paper_pipeline.py` |
| 列出已处理 | `... arxiv_paper_pipeline.py --list` |
| 重置某篇 | `... arxiv_paper_pipeline.py --reset 2604.13458v1` |
| 改起始月份 | `... arxiv_paper_pipeline.py --start 2026-01` |
| 跳过 API（调试） | `... arxiv_paper_pipeline.py --no-api` |
| 单文件解析测试 | `python .claude/skills/arxiv-paper-pipeline/scripts/file_parse.py <pdf>` |

## 依赖

`requirements.txt` 只列出本 skill 特有依赖（`arxiv`、`pdfplumber`）。首次使用：

```bash
pip install -r .claude/skills/arxiv-paper-pipeline/requirements.txt
```

## 已知限制

- arxiv API 偶尔 503，脚本已设 `num_retries=3`，若仍失败直接重跑即可。
- `docu_assistant` 接口目前是内网地址；在外网环境需要先把 `DOCU_API_URL` 改成公网接口 `http://docu.rtclouddata.cn/docu_assistant`，或加 `--no-api` 走 pdfplumber。
- US3 密钥硬编码在 `scripts/us3_tools.py` 中；切账号时改那一处即可。
- Step 2/3 由 Claude 主观完成，不同会话输出可能不同；把判断结论写进生成策略的 docstring 里作为固化记录。
