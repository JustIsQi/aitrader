"""研究产物输出器。"""

from .csv_writer import dump_artifacts
from .report_writer import write_summary_markdown
from .chart_writer import save_equity_drawdown_chart, save_signal_timeline_chart

__all__ = [
    "dump_artifacts",
    "write_summary_markdown",
    "save_equity_drawdown_chart",
    "save_signal_timeline_chart",
]
