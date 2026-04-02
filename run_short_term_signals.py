#!/usr/bin/env python3
"""
短线A股选股信号生成主程序
功能合并自:
- scripts/fetch_sector_data.py
- scripts/generate_short_term_signals.py

功能:
1. (自动) 获取板块数据（如不存在）
2. 筛选强势板块
3. 选股
4. 计算仓位和止盈止损
5. 输出到数据库

使用方法:
    python run_short_term_signals.py                    # 使用今天日期
    python run_short_term_signals.py 20240115           # 指定日期
    python run_short_term_signals.py 20240115 --fetch-only    # 仅获取板块数据
    python run_short_term_signals.py 20240115 --signals-only   # 仅生成信号
    python run_short_term_signals.py 20240115 --force-refresh   # 强制刷新板块数据

作者: AITrader
日期: 2026-01-21
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import Optional

# 第三方库
import pandas as pd
import numpy as np
from tqdm import tqdm

# 尝试导入 akshare
try:
    import akshare as ak
except ImportError:
    logger.error("akshare未安装，板块数据获取功能将不可用")
    ak = None

# 数据库和模型
from database.pg_manager import get_db
from database.models.models import SectorData, StockMetadata, StockHistory, DailyOperationList

# 核心分析模块
from core.sector_analyzer import SectorAnalyzer, SectorConfig
from core.stock_selector import StockSelector, ChaseStrategyConfig, DipStrategyConfig, RiskFilterConfig
from core.position_manager import PositionManager, PositionConfig, StopLossConfig, TakeProfitConfig, OpenTriggerConfig

# 配置
from short_term_config.short_term_config import get_config, ShortTermConfig


# ==================== SectorDataFetcher 类 (内嵌) ====================
class SectorDataFetcher:
    """板块数据获取器（内嵌版本，不再依赖外部模块）"""

    def __init__(self, db=None):
        """
        初始化板块数据获取器

        Args:
            db: 数据库连接
        """
        self.db = db if db else get_db()

    def check_data_exists(self, date: str) -> bool:
        """
        检查指定日期的板块数据是否存在

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            bool: 数据是否存在
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()

            with self.db.get_session() as session:
                count = session.query(SectorData).filter(
                    SectorData.date == date_obj
                ).count()

            return count > 0

        except Exception as e:
            logger.error(f"检查板块数据失败: {e}")
            return False

    def fetch_sector_fund_flow(self):
        """
        获取板块资金流数据

        Returns:
            DataFrame: 板块资金流数据
        """
        if ak is None:
            logger.error("akshare未安装")
            return pd.DataFrame()

        try:
            logger.info("正在获取行业板块资金流数据...")
            df = ak.stock_fund_flow_industry(symbol='即时')

            # 重命名列
            column_rename = {
                '行业': 'sector_name',
                '净额': 'main_net_inflow',
                '流入资金': 'main_inflow',
                '流出资金': 'main_outflow',
                '行业-涨跌幅': 'change_pct',
                '行业指数': 'sector_index'
            }

            existing_cols = {k: v for k, v in column_rename.items() if k in df.columns}
            df.rename(columns=existing_cols, inplace=True)

            # 单位转换: akshare返回的单位是"亿",转换为"万元"
            if 'main_net_inflow' in df.columns:
                df['main_net_inflow'] = df['main_net_inflow'] * 10000

            logger.info(f"✓ 获取到 {len(df)} 个行业板块资金流数据")
            return df

        except Exception as e:
            logger.error(f"获取行业资金流失败: {e}")
            return pd.DataFrame()

    def calculate_sector_indicators(
        self,
        date: str,
        sector_name: str
    ) -> Optional[dict]:
        """
        计算单个板块的技术指标

        Args:
            date: 日期 (YYYYMMDD)
            sector_name: 板块名称

        Returns:
            dict: 技术指标字典
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d')
            start_date_obj = date_obj - timedelta(days=60)

            with self.db.get_session() as session:
                # 获取板块内股票
                stocks = session.query(StockMetadata.symbol).filter(
                    StockMetadata.sector == sector_name
                ).all()

                stock_codes = [s[0] for s in stocks]

                if not stock_codes:
                    return None

                # 获取历史数据
                query = session.query(
                    StockHistory.symbol,
                    StockHistory.date,
                    StockHistory.close,
                    StockHistory.high,
                    StockHistory.amount,
                    StockHistory.change_pct
                ).filter(
                    StockHistory.symbol.in_(stock_codes),
                    StockHistory.date >= start_date_obj.date(),
                    StockHistory.date <= date_obj.date()
                ).order_by(StockHistory.date)

                df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                return None

            # 计算板块指数 (简单平均)
            daily_avg = df.groupby('date')['close'].mean().reset_index()
            daily_avg = daily_avg.sort_values('date')

            if len(daily_avg) < 10:
                return None

            # 计算技术指标
            close = daily_avg['close'].iloc[-1]
            ma5 = daily_avg['close'].tail(5).mean()
            ma10 = daily_avg['close'].tail(10).mean()

            # 计算RSI
            try:
                import talib
                closes = daily_avg['close'].values
                rsi = talib.RSI(closes, timeperiod=14)[-1]
                if np.isnan(rsi):
                    rsi = 50.0
            except:
                rsi = 50.0

            # 计算放量率
            daily_amount = df.groupby('date')['amount'].sum().reset_index()
            daily_amount = daily_amount.sort_values('date')

            if len(daily_amount) >= 6:
                today_amount = daily_amount['amount'].iloc[-1]
                avg_5d_amount = daily_amount['amount'].iloc[-6:-1].mean()
                volume_expansion_ratio = today_amount / avg_5d_amount if avg_5d_amount > 0 else 1.0
            else:
                volume_expansion_ratio = 1.0

            # 统计涨停家数
            date_str = date_obj.date()
            limit_up_count = int(df[(df['date'] == date_str) & (df['change_pct'] >= 9.5)]['symbol'].nunique())

            return {
                'close': float(close),
                'ma5': float(ma5),
                'ma10': float(ma10),
                'rsi': float(rsi),
                'volume_expansion_ratio': float(volume_expansion_ratio),
                'limit_up_count': int(limit_up_count)
            }

        except Exception as e:
            logger.error(f"计算板块 {sector_name} 技术指标失败: {e}")
            return None

    def fetch_and_save(self, date: str, force: bool = False) -> bool:
        """
        获取并保存板块数据到数据库

        Args:
            date: 日期 (YYYYMMDD)
            force: 是否强制刷新已存在的数据

        Returns:
            bool: 是否成功
        """
        logger.info("=" * 60)
        logger.info(f"开始获取板块数据: {date}")
        logger.info("=" * 60)

        date_obj = datetime.strptime(date, '%Y%m%d').date()

        # 检查是否已有数据
        if not force:
            if self.check_data_exists(date):
                logger.info(f"数据库中已有 {date} 的板块数据 (使用 --force-refresh 强制刷新)")
                return True

        # 1. 获取板块资金流数据
        fund_flow_df = self.fetch_sector_fund_flow()

        if fund_flow_df.empty:
            logger.warning("未获取到板块资金流数据")
            return False

        # 2. 获取所有板块名称
        with self.db.get_session() as session:
            sectors = session.query(StockMetadata.sector).filter(
                StockMetadata.sector.isnot(None)
            ).distinct().all()
            all_sector_names = [s[0] for s in sectors]

        logger.info(f"数据库中共有 {len(all_sector_names)} 个板块")

        # 3. 合并资金流数据
        sector_names = fund_flow_df['sector_name'].tolist()

        # 4. 计算每个板块的指标
        logger.info("正在计算各板块技术指标...")
        records = []

        for sector_name in tqdm(sector_names, desc="计算板块指标"):
            try:
                # 获取资金流数据
                sector_row = fund_flow_df[fund_flow_df['sector_name'] == sector_name]
                if sector_row.empty:
                    main_net_inflow_1d = 0.0
                else:
                    main_net_inflow_1d = sector_row['main_net_inflow'].iloc[0]

                # 计算技术指标
                indicators = self.calculate_sector_indicators(date, sector_name)

                if indicators is None:
                    continue

                # 创建记录
                record = SectorData(
                    date=date_obj,
                    sector_code=sector_name,
                    sector_name=sector_name,
                    main_net_inflow_1d=float(main_net_inflow_1d),
                    main_net_inflow_3d=0.0,
                    main_net_inflow_5d=0.0,
                    volume_expansion_ratio=indicators['volume_expansion_ratio'],
                    northbound_buy_ratio=0.0,
                    limit_up_count=indicators['limit_up_count'],
                    consecutive_board_count=0,
                    rank_3d_gain=None,
                    close=indicators['close'],
                    ma5=indicators['ma5'],
                    ma10=indicators['ma10'],
                    rsi=indicators['rsi'],
                    strength_score=0.0
                )

                records.append(record)

            except Exception as e:
                logger.error(f"处理板块 {sector_name} 失败: {e}")
                continue

        if not records:
            logger.warning("没有成功计算出任何板块数据")
            return False

        # 5. 计算综合得分
        logger.info("正在计算综合得分...")
        for record in records:
            fund_score = 0.0
            tech_score = 0.0
            sentiment_score = 0.0

            # 资金得分 (0-2分)
            if record.main_net_inflow_1d >= 300.0:
                fund_score += 1.0
            if record.volume_expansion_ratio >= 1.5:
                fund_score += 1.0

            # 技术得分 (0-2分)
            is_ma_bullish = (record.close > record.ma5) and (record.ma5 > record.ma10)
            if is_ma_bullish:
                tech_score += 1.0
            if 30.0 <= record.rsi <= 70.0:
                tech_score += 1.0

            # 情绪得分 (0-1分)
            if record.limit_up_count >= 3:
                sentiment_score += 1.0

            # 综合得分 (加权: 资金50%, 技术30%, 情绪20%)
            record.strength_score = (
                fund_score * 0.5 +
                tech_score * 0.3 +
                sentiment_score * 0.2
            )

        # 6. 保存到数据库
        logger.info("正在保存到数据库...")
        with self.db.get_session() as session:
            # 检查并删除当天旧数据，避免唯一约束冲突
            existing = session.query(SectorData).filter(
                SectorData.date == date_obj
            ).first()
            if existing:
                if force:
                    logger.info(f"强制刷新：删除 {date} 的旧数据")
                else:
                    logger.info(f"检测到已有数据：删除 {date} 的旧数据重新保存")
                session.query(SectorData).filter(SectorData.date == date_obj).delete()

            # 批量保存
            for record in records:
                session.merge(record)

            session.commit()

        logger.info(f"✓ 成功保存 {len(records)} 条板块数据")

        # 7. 显示Top板块
        records.sort(key=lambda x: x.strength_score, reverse=True)
        top_10 = records[:10]

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Top 10 强势板块 ({date}):")
        logger.info("=" * 60)
        for i, record in enumerate(top_10, 1):
            logger.info(
                f"  {i:2d}. {record.sector_name:8s} | "
                f"评分={record.strength_score:.2f} | "
                f"资金流入={record.main_net_inflow_1d/10000:.1f}亿 | "
                f"放量率={record.volume_expansion_ratio:.2f} | "
                f"涨停={record.limit_up_count} | "
                f"RSI={record.rsi:.1f}"
            )
        logger.info("=" * 60)

        return True


# ==================== 主函数 ====================
def generate_daily_signals(date: str = None, config: ShortTermConfig = None,
                           fetch_mode: str = 'auto', force_refresh: bool = False):
    """
    生成每日操作清单

    Args:
        date: 日期 (YYYYMMDD), 默认为今天
        config: 配置对象, 默认从文件加载
        fetch_mode: 'auto' | 'fetch-only' | 'signals-only'
        force_refresh: 是否强制刷新板块数据

    Returns:
        交易计划列表
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')

    # ==================== 步骤0: 板块数据准备 ====================
    if fetch_mode in ['auto', 'fetch-only']:
        logger.info("\n【步骤0/4】板块数据准备")
        logger.info("-" * 80)

        fetcher = SectorDataFetcher()

        # 检查数据是否存在
        data_exists = fetcher.check_data_exists(date)

        if force_refresh or not data_exists:
            if force_refresh:
                logger.info(f"强制刷新板块数据: {date}")
            else:
                logger.info(f"板块数据不存在，开始获取: {date}")

            success = fetcher.fetch_and_save(date, force=force_refresh)

            if not success:
                logger.error("✗ 板块数据获取失败，终止流程")
                return []
        else:
            logger.info(f"✓ 板块数据已存在: {date}")

        if fetch_mode == 'fetch-only':
            logger.info("\n仅获取板块数据模式，不生成信号")
            return []

    if config is None:
        config = get_config()

    logger.info("=" * 80)
    logger.info(f"开始生成 {date} 的短线交易信号")
    logger.info("=" * 80)

    db = get_db()

    # ==================== 步骤1: 板块量化筛选 ====================
    logger.info("\n【步骤1/4】板块量化筛选")
    logger.info("-" * 80)

    sector_analyzer = SectorAnalyzer(
        config=SectorConfig(
            min_main_net_inflow_1d=config.sector.min_main_net_inflow_1d,
            min_volume_expansion_ratio=config.sector.min_volume_expansion_ratio,
            require_ma_bullish=config.sector.require_ma_bullish,
            min_rsi=config.sector.min_rsi,
            max_rsi=config.sector.max_rsi,
            min_limit_up_count=config.sector.min_limit_up_count,
            require_top_10pct_3d=config.sector.require_top_10pct_3d,
            top_sectors=config.sector.top_sectors
        )
    )

    sector_scores = sector_analyzer.calculate_sector_scores(date)

    if not sector_scores:
        logger.error("✗ 未筛选出强势板块,终止流程")
        return []

    sector_names = [s.sector_name for s in sector_scores]
    logger.info(f"✓ 筛选出 {len(sector_names)} 个强势板块: {', '.join(sector_names)}")

    # ==================== 步骤2: 个股量化选股 ====================
    logger.info("\n【步骤2/4】个股量化选股")
    logger.info("-" * 80)

    stock_selector = StockSelector(
        chase_config=ChaseStrategyConfig(
            min_change_pct=config.chase.min_change_pct,
            max_change_pct=config.chase.max_change_pct,
            allow_failed_limit_up=config.chase.allow_failed_limit_up,
            min_turnover_rate=config.chase.min_turnover_rate,
            max_turnover_rate=config.chase.max_turnover_rate,
            min_volume_ratio=config.chase.min_volume_ratio,
            require_volume_step_up=config.chase.require_volume_step_up,
            breakout_lookback_days=config.chase.breakout_lookback_days,
            require_breakout_or_ma_diverge=config.chase.require_breakout_or_ma_diverge,
            ma_diverge_max_spread=config.chase.ma_diverge_max_spread,
            max_stocks_per_sector=config.chase.max_stocks_per_sector
        ),
        dip_config=DipStrategyConfig(
            max_close_ma_deviation=config.dip.max_close_ma_deviation,
            require_macd_golden_cross=config.dip.require_macd_golden_cross,
            max_volume_ratio_5d=config.dip.max_volume_ratio_5d,
            require_sector_inflow=config.dip.require_sector_inflow,
            max_stocks_per_sector=config.dip.max_stocks_per_sector,
            enable_rsi_oversold=config.dip.enable_rsi_oversold,
            rsi_oversold_threshold=config.dip.rsi_oversold_threshold
        ),
        risk_config=RiskFilterConfig(
            exclude_loss_maker=config.risk.exclude_loss_maker,
            exclude_reduction=config.risk.exclude_reduction,
            exclude_suspend=config.risk.exclude_suspend,
            min_market_cap=config.risk.min_market_cap,
            max_market_cap=config.risk.max_market_cap,
            exclude_non_main_board=config.risk.exclude_non_main_board
        )
    )

    selected_stocks = stock_selector.select_stocks(
        sector_names=sector_names,
        date=date,
        strategy_type='both'
    )

    chase_count = len(selected_stocks.get('chase', []))
    dip_count = len(selected_stocks.get('dip', []))
    logger.info(f"✓ 追涨策略: {chase_count} 只")
    logger.info(f"✓ 低吸策略: {dip_count} 只")

    if chase_count == 0 and dip_count == 0:
        logger.warning("✗ 未选出任何股票,终止流程")
        return []

    # ==================== 步骤3: 交易规则量化计算 ====================
    logger.info("\n【步骤3/4】交易规则量化计算")
    logger.info("-" * 80)

    position_manager = PositionManager(
        position_config=PositionConfig(
            max_sector_position=config.position.max_sector_position,
            max_stock_position=config.position.max_stock_position,
            max_total_position=config.position.max_total_position,
            sector_rank_1_2_position=config.position.sector_rank_1_2_position,
            sector_rank_3_5_position=config.position.sector_rank_3_5_position
        ),
        stop_loss_config=StopLossConfig(
            stop_loss_pct_close=config.stop_loss.stop_loss_pct_close,
            use_ma5_stop=config.stop_loss.use_ma5_stop,
            use_atr_stop=config.stop_loss.use_atr_stop,
            atr_multiplier=config.stop_loss.atr_multiplier,
            atr_period=config.stop_loss.atr_period,
            max_loss_pct=config.stop_loss.max_loss_pct
        ),
        take_profit_config=TakeProfitConfig(
            use_10d_high=config.take_profit.use_10d_high,
            take_profit_pct_close=config.take_profit.take_profit_pct_close,
            enable_gradient=config.take_profit.enable_gradient,
            gradient_10pct_sell_ratio=config.take_profit.gradient_10pct_sell_ratio,
            gradient_20pct_sell_ratio=config.take_profit.gradient_20pct_sell_ratio,
            use_atr_tp=config.take_profit.use_atr_tp,
            atr_tp_multiplier=config.take_profit.atr_tp_multiplier
        ),
        open_trigger_config=OpenTriggerConfig(
            min_high_open_pct=config.open_trigger.min_high_open_pct,
            max_high_open_pct=config.open_trigger.max_high_open_pct,
            min_seal_ratio=config.open_trigger.min_seal_ratio,
            min_auction_amount=config.open_trigger.min_auction_amount
        )
    )

    trading_plans = position_manager.generate_trading_plans(
        selected_stocks=selected_stocks,
        sector_scores=sector_scores,
        date=date
    )

    logger.info(f"✓ 生成 {len(trading_plans)} 个交易计划")

    # ==================== 步骤4: 保存到数据库 ====================
    logger.info("\n【步骤4/4】保存到数据库")
    logger.info("-" * 80)

    try:
        with db.get_session() as session:
            # 先删除当日旧数据 (如果存在)
            date_obj = datetime.strptime(date, '%Y%m%d').date()

            deleted_count = session.query(DailyOperationList).filter(
                DailyOperationList.date == date_obj
            ).delete()
            logger.debug(f"删除旧数据: {deleted_count} 条")

            # 插入新数据
            for plan in trading_plans:
                import numpy as np

                record = DailyOperationList(
                    date=date_obj,
                    sector_name=plan.sector_name,
                    sector_rank=plan.sector_rank,
                    stock_code=plan.stock_code,
                    stock_name=plan.stock_name,
                    strategy_type=plan.strategy_type,
                    position_ratio=float(plan.position_ratio),
                    stop_loss_price=float(plan.stop_loss_price) if plan.stop_loss_price else None,
                    take_profit_price=float(plan.take_profit_price) if plan.take_profit_price else None,
                    open_trigger_high_pct=float(plan.open_trigger_high_pct[0]),  # 保存最小值
                    open_trigger_seal_ratio=float(plan.open_trigger_seal_ratio),
                    open_trigger_auction_amount=float(plan.open_trigger_auction_amount),
                    strength_score=float(plan.strength_score),
                    is_executed=False
                )
                session.add(record)

            session.commit()

        logger.success(f"✓ 成功保存 {len(trading_plans)} 条交易计划到数据库")

    except Exception as e:
        logger.error(f"✗ 保存数据库失败: {e}")
        raise

    # ==================== 总结 ====================
    logger.info("\n" + "=" * 80)
    logger.success(f"✓✓✓ 每日操作清单生成完成!")
    logger.info("=" * 80)
    logger.info(f"日期: {date}")
    logger.info(f"强势板块: {len(sector_names)} 个")
    logger.info(f"选股数量: {chase_count + dip_count} 只 (追涨 {chase_count}, 低吸 {dip_count})")
    logger.info(f"交易计划: {len(trading_plans)} 个")

    # 显示部分交易计划
    logger.info("\n【交易计划预览】")
    for i, plan in enumerate(trading_plans[:10], 1):
        logger.info(
            f"  {i}. {plan.stock_code} {plan.stock_name} | "
            f"{plan.sector_name}(排名{plan.sector_rank}) | "
            f"{plan.strategy_type} | "
            f"仓位={plan.position_ratio*100:.1f}% | "
            f"止损={plan.stop_loss_price:.2f} | "
            f"止盈={plan.take_profit_price:.2f}"
        )

    if len(trading_plans) > 10:
        logger.info(f"  ... 还有 {len(trading_plans) - 10} 个交易计划")

    logger.info("=" * 80)

    return trading_plans


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='短线A股选股信号生成（合并版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                              # 使用今天日期（默认：获取板块数据+生成信号）
  %(prog)s 20240115                     # 指定日期
  %(prog)s 20240115 --fetch-only        # 仅获取板块数据
  %(prog)s 20240115 --signals-only      # 仅生成信号（假设板块数据已存在）
  %(prog)s 20240115 --force-refresh     # 强制刷新板块数据并生成信号
        '''
    )

    parser.add_argument(
        'date',
        nargs='?',
        help='日期 (YYYYMMDD), 默认为今天'
    )

    parser.add_argument(
        '--fetch-only',
        action='store_true',
        help='仅获取板块数据，不生成交易信号'
    )

    parser.add_argument(
        '--signals-only',
        action='store_true',
        help='仅生成交易信号，跳过板块数据获取'
    )

    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='强制刷新板块数据（即使数据已存在）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    # 处理日期
    if args.date:
        date = args.date
        # 验证日期格式
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            logger.error("日期格式错误，请使用 YYYYMMDD 格式，如: 20260120")
            sys.exit(1)
    else:
        date = datetime.now().strftime('%Y%m%d')

    # 配置日志
    if args.verbose:
        logger.remove()
        logger.add(lambda msg: print(msg, end=''), level="DEBUG")
    else:
        logger.remove()
        logger.add(
            lambda msg: print(msg, end=''),
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>\n"
        )

    # 加载配置
    config = get_config()

    # 确定运行模式
    if args.fetch_only:
        fetch_mode = 'fetch-only'
    elif args.signals_only:
        fetch_mode = 'signals-only'
    else:
        fetch_mode = 'auto'

    # 生成信号
    try:
        generate_daily_signals(
            date,
            config,
            fetch_mode=fetch_mode,
            force_refresh=args.force_refresh
        )
        logger.success("\n✓✓✓ 全部完成!")
        return 0
    except Exception as e:
        logger.error(f"\n✗✗✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
