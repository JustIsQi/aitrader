"""
短线选股配置系统

所有阈值可配置,支持从JSON文件加载
作者: AITrader
日期: 2026-01-21
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional
import json
from pathlib import Path
from aitrader.infrastructure.config.logging import logger


@dataclass
class SectorThresholds:
    """板块筛选阈值"""
    # 资金阈值
    min_main_net_inflow_1d: float = 300.0  # 1日主力净流入≥3亿(万元)
    min_volume_expansion_ratio: float = 1.5  # 成交额放量率≥1.5

    # 技术阈值
    require_ma_bullish: bool = True  # 要求站上5+10日线
    min_rsi: float = 30.0
    max_rsi: float = 70.0

    # 情绪阈值
    min_limit_up_count: int = 3  # 当日涨停家数≥3
    require_top_10pct_3d: bool = True  # 要求3日涨跌幅排名前10%

    # 输出数量
    top_sectors: int = 5  # 输出前5个板块


@dataclass
class ChaseThresholds:
    """追涨策略阈值 (动量突破5步Pipeline)"""
    # 第1步：涨幅筛选
    min_change_pct: float = 5.0         # 最小涨幅5%
    max_change_pct: float = 7.0         # 最大涨幅7%
    allow_failed_limit_up: bool = True  # 允许曾涨停未封住（盘中触板回落）
    limit_up_threshold: float = 9.5    # 涨停判定阈值（主板9.5%，创业板/科创板可调至19.5%）

    # 第2步：量能验证
    min_turnover_rate: float = 5.0      # 最小换手率5%
    max_turnover_rate: float = 10.0     # 最大换手率10%
    min_volume_ratio: float = 1.0       # 量比>1
    require_volume_step_up: bool = True # 要求成交量阶梯放大

    # 第4步：形态关键
    breakout_lookback_days: int = 20    # 突破回看天数
    require_breakout_or_ma_diverge: bool = True  # 突破平台或均线发散
    ma_diverge_max_spread: float = 8.0  # 均线发散最大价差%（超过视为高位）

    # 通用
    max_stocks_per_sector: int = 5      # 每板块最多选5只股票


@dataclass
class DipThresholds:
    """低吸策略阈值"""
    max_close_ma_deviation: float = 5.0  # 收盘价偏离均线≤5%（从3%放宽）
    require_macd_golden_cross: bool = True  # MACD金叉
    max_volume_ratio_5d: float = 0.9  # 成交额≤5日均值的0.9（从0.8放宽）
    require_sector_inflow: bool = True  # 要求板块资金净流入
    max_stocks_per_sector: int = 5  # 每板块最多选5只股票
    enable_rsi_oversold: bool = True  # 启用RSI超卖条件
    rsi_oversold_threshold: float = 40.0  # RSI超卖阈值


@dataclass
class RiskThresholds:
    """风险过滤阈值"""
    exclude_loss_maker: bool = True  # 排除业绩亏损
    exclude_reduction: bool = True  # 排除减持公告
    exclude_suspend: bool = True  # 排除停牌
    min_market_cap: float = 50.0  # 最小市值50亿(亿元)
    max_market_cap: float = 200.0  # 最大市值200亿(亿元)
    exclude_non_main_board: bool = True  # 排除非主板股票（科创板、创业板、北交所）


@dataclass
class PositionThresholds:
    """仓位管理阈值"""
    max_sector_position: float = 0.30  # 单板块最大仓位30%
    max_stock_position: float = 0.15  # 单股最大仓位15%
    max_total_position: float = 0.70  # 总仓位上限70%

    # 板块排名对应的仓位
    sector_rank_1_2_position: float = 0.10  # 排名1-2: 10%
    sector_rank_3_5_position: float = 0.08  # 排名3-5: 8%


@dataclass
class StopLossThresholds:
    """止损阈值"""
    stop_loss_pct_close: float = -0.03  # 前一日收盘价-3%
    use_ma5_stop: bool = True  # 使用5日线止损
    use_atr_stop: bool = True  # 使用ATR自适应止损
    atr_multiplier: float = 2.0  # ATR止损倍数
    atr_period: int = 14  # ATR计算周期
    max_loss_pct: float = -0.10  # 绝对最大止损幅度（10%）


@dataclass
class TakeProfitThresholds:
    """止盈阈值"""
    use_10d_high: bool = True  # 使用10日高点
    take_profit_pct_close: float = 0.10  # 收盘价+10%
    enable_gradient: bool = True  # 启用梯度止盈（默认开启）
    gradient_10pct_sell_ratio: float = 0.50  # 10%时卖出50%
    gradient_20pct_sell_ratio: float = 1.00  # 20%时全部卖出
    use_atr_tp: bool = True  # 使用ATR止盈
    atr_tp_multiplier: float = 3.0  # ATR止盈倍数


@dataclass
class OpenTriggerThresholds:
    """开盘触发阈值"""
    min_high_open_pct: float = 2.0  # 最小高开幅度(%) - 高开2%
    max_high_open_pct: float = 4.0  # 最大高开幅度(%) - 不超过4%
    min_seal_ratio: float = 0.01  # 封单量占流通盘比例≥1%
    min_auction_amount: float = 500.0  # 竞价成交额≥500万(万元)


@dataclass
class BacktestThresholds:
    """回测配置阈值"""
    max_holding_days: int = 3  # 最大持仓天数
    initial_capital: float = 1000000.0  # 初始资金
    commission_rate: float = 0.0003  # 手续费率(万三)


@dataclass
class ShortTermConfig:
    """总配置"""
    sector: SectorThresholds = field(default_factory=SectorThresholds)
    chase: ChaseThresholds = field(default_factory=ChaseThresholds)
    dip: DipThresholds = field(default_factory=DipThresholds)
    risk: RiskThresholds = field(default_factory=RiskThresholds)
    position: PositionThresholds = field(default_factory=PositionThresholds)
    stop_loss: StopLossThresholds = field(default_factory=StopLossThresholds)
    take_profit: TakeProfitThresholds = field(default_factory=TakeProfitThresholds)
    open_trigger: OpenTriggerThresholds = field(default_factory=OpenTriggerThresholds)
    backtest: BacktestThresholds = field(default_factory=BacktestThresholds)

    @classmethod
    def from_json(cls, file_path: str) -> 'ShortTermConfig':
        """
        从JSON文件加载配置

        兼容旧版JSON: 自动忽略已废弃的字段，缺失的新字段使用默认值

        Args:
            file_path: JSON配置文件路径

        Returns:
            ShortTermConfig实例
        """
        import dataclasses

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        def _safe_init(dc_class, raw_dict):
            """安全初始化dataclass，忽略未知字段"""
            valid_fields = {f.name for f in dataclasses.fields(dc_class)}
            filtered = {k: v for k, v in raw_dict.items() if k in valid_fields}
            return dc_class(**filtered)

        return cls(
            sector=_safe_init(SectorThresholds, data.get('sector', {})),
            chase=_safe_init(ChaseThresholds, data.get('chase', {})),
            dip=_safe_init(DipThresholds, data.get('dip', {})),
            risk=_safe_init(RiskThresholds, data.get('risk', {})),
            position=_safe_init(PositionThresholds, data.get('position', {})),
            stop_loss=_safe_init(StopLossThresholds, data.get('stop_loss', {})),
            take_profit=_safe_init(TakeProfitThresholds, data.get('take_profit', {})),
            open_trigger=_safe_init(OpenTriggerThresholds, data.get('open_trigger', {})),
            backtest=_safe_init(BacktestThresholds, data.get('backtest', {}))
        )

    def to_json(self, file_path: str):
        """
        保存配置到JSON文件

        Args:
            file_path: JSON配置文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        logger.info(f"配置已保存到: {file_path}")

    @classmethod
    def get_default(cls) -> 'ShortTermConfig':
        """获取默认配置"""
        return cls()

    def validate(self) -> bool:
        """
        验证配置合理性

        Returns:
            配置是否合法
        """
        # 验证仓位配置
        if self.position.max_total_position > 1.0:
            logger.error("总仓位不能超过100%")
            return False

        if self.position.sector_rank_1_2_position > self.position.max_stock_position:
            logger.error("板块1-2名单股仓位不能超过单股最大仓位")
            return False

        if self.position.sector_rank_3_5_position > self.position.max_stock_position:
            logger.error("板块3-5名单股仓位不能超过单股最大仓位")
            return False

        # 验证止损止盈
        if self.stop_loss.stop_loss_pct_close >= 0:
            logger.error("止损比例必须为负数")
            return False

        if self.take_profit.take_profit_pct_close <= 0:
            logger.error("止盈比例必须为正数")
            return False

        # 验证追涨策略
        if self.chase.min_change_pct >= self.chase.max_change_pct:
            logger.error("追涨策略: 最小涨幅必须小于最大涨幅")
            return False

        if self.chase.min_turnover_rate >= self.chase.max_turnover_rate:
            logger.error("追涨策略: 最小换手率必须小于最大换手率")
            return False

        if self.chase.min_volume_ratio <= 0:
            logger.error("追涨策略: 量比阈值必须为正数")
            return False

        # 验证开盘触发
        if self.open_trigger.min_high_open_pct >= self.open_trigger.max_high_open_pct:
            logger.error("开盘触发: 最小高开幅度必须小于最大高开幅度")
            return False

        logger.info("配置验证通过")
        return True


# 配置文件路径
CONFIG_FILE = Path(__file__).parent / 'short_term_config.json'

# 全局配置实例
config: Optional[ShortTermConfig] = None


def load_config(file_path: str = None) -> ShortTermConfig:
    """
    加载配置

    Args:
        file_path: 配置文件路径,默认使用CONFIG_FILE

    Returns:
        ShortTermConfig实例
    """
    global config

    config_path = file_path or str(CONFIG_FILE)

    if Path(config_path).exists():
        try:
            config = ShortTermConfig.from_json(config_path)
            logger.info(f"✓ 加载配置文件: {config_path}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
            config = ShortTermConfig.get_default()
    else:
        config = ShortTermConfig.get_default()
        config.to_json(config_path)
        logger.info(f"✓ 创建默认配置文件: {config_path}")

    # 验证配置
    config.validate()

    return config


def save_config(file_path: str = None):
    """
    保存当前配置

    Args:
        file_path: 配置文件路径,默认使用CONFIG_FILE
    """
    global config

    if config is None:
        logger.error("配置未初始化")
        return

    config_path = file_path or str(CONFIG_FILE)
    config.to_json(config_path)


def get_config() -> ShortTermConfig:
    """
    获取当前配置

    Returns:
        ShortTermConfig实例
    """
    global config

    if config is None:
        config = load_config()

    return config


# 模块初始化时自动加载配置
if __name__ != '__main__':
    load_config()


if __name__ == '__main__':
    """测试配置系统"""

    # 1. 创建默认配置
    print("=== 创建默认配置 ===")
    config = ShortTermConfig.get_default()
    print(f"板块筛选: {config.sector}")
    print(f"追涨策略: {config.chase}")
    print(f"仓位管理: {config.position}")

    # 2. 保存配置
    print("\n=== 保存配置 ===")
    test_config_file = '/tmp/test_short_term_config.json'
    config.to_json(test_config_file)
    print(f"配置已保存到: {test_config_file}")

    # 3. 加载配置
    print("\n=== 加载配置 ===")
    loaded_config = ShortTermConfig.from_json(test_config_file)
    print(f"板块筛选阈值: {loaded_config.sector.min_main_net_inflow_1d}")

    # 4. 验证配置
    print("\n=== 验证配置 ===")
    is_valid = config.validate()
    print(f"配置合法: {is_valid}")

    # 5. 修改配置
    print("\n=== 修改配置 ===")
    config.sector.min_main_net_inflow_1d = 500.0
    config.position.max_total_position = 0.80
    print(f"修改后的最小净流入: {config.sector.min_main_net_inflow_1d}")
    print(f"修改后的总仓位: {config.position.max_total_position}")
