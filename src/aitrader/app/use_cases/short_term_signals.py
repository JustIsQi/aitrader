"""
短线A股选股信号生成 Use Case

功能:
1. 获取板块数据（如不存在则自动拉取）
2. 筛选强势板块
3. 量化选股
4. 计算仓位和止盈止损
5. 输出到数据库
"""

from __future__ import annotations

import traceback
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd
from aitrader.infrastructure.config.logging import logger
from tqdm import tqdm

from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.db.models.models import (
    SectorData, StockMetadata, StockHistory, DailyOperationList,
)
from aitrader.domain.market.sector_analyzer import SectorAnalyzer, SectorConfig
from aitrader.domain.market.stock_selector import (
    StockSelector, ChaseStrategyConfig, DipStrategyConfig, RiskFilterConfig,
)
from aitrader.domain.market.position_manager import (
    PositionManager, PositionConfig, StopLossConfig, TakeProfitConfig, OpenTriggerConfig,
)
from aitrader.infrastructure.config.short_term import get_config, ShortTermConfig


class SectorDataFetcher:
    """板块数据获取器"""

    def __init__(self, db=None):
        self.db = db if db else get_db()

    def check_data_exists(self, date: str) -> bool:
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

    def fetch_sector_fund_flow(self) -> pd.DataFrame:
        try:
            with self.db.get_session() as session:
                sectors = session.query(StockMetadata.sector).filter(
                    StockMetadata.sector.isnot(None)
                ).distinct().all()

            sector_names = sorted({s[0] for s in sectors if s[0]})
            if not sector_names:
                return pd.DataFrame()

            df = pd.DataFrame({
                "sector_name": sector_names,
                # Wind 路径下暂未提供板块资金流字段，置 0 后继续走量价筛选
                "main_net_inflow": [0.0] * len(sector_names),
            })
            logger.info(f"✓ 从数据库加载到 {len(df)} 个行业板块")
            return df
        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return pd.DataFrame()

    def calculate_sector_indicators(self, date: str, sector_name: str) -> Optional[dict]:
        try:
            date_obj = datetime.strptime(date, '%Y%m%d')
            start_date_obj = date_obj - timedelta(days=60)

            with self.db.get_session() as session:
                stocks = session.query(StockMetadata.symbol).filter(
                    StockMetadata.sector == sector_name
                ).all()
                stock_codes = [s[0] for s in stocks]

                if not stock_codes:
                    return None

                query = session.query(
                    StockHistory.symbol,
                    StockHistory.date,
                    StockHistory.close,
                    StockHistory.high,
                    StockHistory.amount,
                    StockHistory.change_pct,
                ).filter(
                    StockHistory.symbol.in_(stock_codes),
                    StockHistory.date >= start_date_obj.date(),
                    StockHistory.date <= date_obj.date(),
                ).order_by(StockHistory.date)

                df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                return None

            daily_avg = df.groupby('date')['close'].mean().reset_index().sort_values('date')
            if len(daily_avg) < 10:
                return None

            close = daily_avg['close'].iloc[-1]
            ma5 = daily_avg['close'].tail(5).mean()
            ma10 = daily_avg['close'].tail(10).mean()

            try:
                import talib
                closes = daily_avg['close'].values
                rsi_vals = talib.RSI(closes, timeperiod=14)
                rsi = float(rsi_vals[-1]) if not np.isnan(rsi_vals[-1]) else 50.0
            except Exception:
                rsi = 50.0

            daily_amount = df.groupby('date')['amount'].sum().reset_index().sort_values('date')
            if len(daily_amount) >= 6:
                today_amount = daily_amount['amount'].iloc[-1]
                avg_5d_amount = daily_amount['amount'].iloc[-6:-1].mean()
                volume_expansion_ratio = today_amount / avg_5d_amount if avg_5d_amount > 0 else 1.0
            else:
                volume_expansion_ratio = 1.0

            date_str = date_obj.date()
            limit_up_count = int(
                df[(df['date'] == date_str) & (df['change_pct'] >= 9.5)]['symbol'].nunique()
            )

            return {
                'close': float(close),
                'ma5': float(ma5),
                'ma10': float(ma10),
                'rsi': float(rsi),
                'volume_expansion_ratio': float(volume_expansion_ratio),
                'limit_up_count': limit_up_count,
            }

        except Exception as e:
            logger.error(f"计算板块 {sector_name} 技术指标失败: {e}")
            return None

    def fetch_and_save(self, date: str, force: bool = False) -> bool:
        logger.info("=" * 60)
        logger.info(f"开始获取板块数据: {date}")
        logger.info("=" * 60)

        date_obj = datetime.strptime(date, '%Y%m%d').date()

        if not force and self.check_data_exists(date):
            logger.info(f"数据库中已有 {date} 的板块数据")
            return True

        fund_flow_df = self.fetch_sector_fund_flow()
        if fund_flow_df.empty:
            logger.warning("未获取到板块资金流数据")
            return False

        with self.db.get_session() as session:
            sectors = session.query(StockMetadata.sector).filter(
                StockMetadata.sector.isnot(None)
            ).distinct().all()
            all_sector_names = [s[0] for s in sectors]

        logger.info(f"数据库中共有 {len(all_sector_names)} 个板块")

        sector_names = fund_flow_df['sector_name'].tolist()
        records = []

        for sector_name in tqdm(sector_names, desc="计算板块指标"):
            try:
                sector_row = fund_flow_df[fund_flow_df['sector_name'] == sector_name]
                main_net_inflow_1d = (
                    sector_row['main_net_inflow'].iloc[0] if not sector_row.empty else 0.0
                )

                indicators = self.calculate_sector_indicators(date, sector_name)
                if indicators is None:
                    continue

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
                    strength_score=0.0,
                )
                records.append(record)

            except Exception as e:
                logger.error(f"处理板块 {sector_name} 失败: {e}")
                continue

        if not records:
            logger.warning("没有成功计算出任何板块数据")
            return False

        for record in records:
            fund_score = (
                (1.0 if record.main_net_inflow_1d >= 300.0 else 0.0)
                + (1.0 if record.volume_expansion_ratio >= 1.5 else 0.0)
            )
            is_ma_bullish = (record.close > record.ma5) and (record.ma5 > record.ma10)
            tech_score = (1.0 if is_ma_bullish else 0.0) + (1.0 if 30.0 <= record.rsi <= 70.0 else 0.0)
            sentiment_score = 1.0 if record.limit_up_count >= 3 else 0.0
            record.strength_score = fund_score * 0.5 + tech_score * 0.3 + sentiment_score * 0.2

        with self.db.get_session() as session:
            existing = session.query(SectorData).filter(SectorData.date == date_obj).first()
            if existing:
                session.query(SectorData).filter(SectorData.date == date_obj).delete()
            for record in records:
                session.merge(record)
            session.commit()

        logger.info(f"✓ 成功保存 {len(records)} 条板块数据")

        top_10 = sorted(records, key=lambda x: x.strength_score, reverse=True)[:10]
        logger.info(f"Top 10 强势板块 ({date}):")
        for i, r in enumerate(top_10, 1):
            logger.info(
                f"  {i:2d}. {r.sector_name:8s} | 评分={r.strength_score:.2f} | "
                f"资金流入={r.main_net_inflow_1d/10000:.1f}亿 | "
                f"放量率={r.volume_expansion_ratio:.2f} | "
                f"涨停={r.limit_up_count} | RSI={r.rsi:.1f}"
            )

        return True


def generate_daily_signals(
    date: str | None = None,
    config: ShortTermConfig | None = None,
    fetch_mode: str = 'auto',
    force_refresh: bool = False,
) -> list:
    """
    生成每日操作清单

    Args:
        date: 日期 (YYYYMMDD)，默认为今天
        config: 配置对象，默认从文件加载
        fetch_mode: 'auto' | 'fetch-only' | 'signals-only'
        force_refresh: 是否强制刷新板块数据

    Returns:
        交易计划列表
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')

    # ── 步骤0: 板块数据准备 ──────────────────────────────────
    if fetch_mode in ['auto', 'fetch-only']:
        logger.info("\n【步骤0/4】板块数据准备")

        fetcher = SectorDataFetcher()
        data_exists = fetcher.check_data_exists(date)

        if force_refresh or not data_exists:
            success = fetcher.fetch_and_save(date, force=force_refresh)
            if not success:
                logger.error("✗ 板块数据获取失败，终止流程")
                return []
        else:
            logger.info(f"✓ 板块数据已存在: {date}")

        if fetch_mode == 'fetch-only':
            return []

    if config is None:
        config = get_config()

    logger.info("=" * 80)
    logger.info(f"开始生成 {date} 的短线交易信号")
    logger.info("=" * 80)

    db = get_db()

    # ── 步骤1: 板块量化筛选 ──────────────────────────────────
    logger.info("\n【步骤1/4】板块量化筛选")
    sector_analyzer = SectorAnalyzer(
        config=SectorConfig(
            min_main_net_inflow_1d=config.sector.min_main_net_inflow_1d,
            min_volume_expansion_ratio=config.sector.min_volume_expansion_ratio,
            require_ma_bullish=config.sector.require_ma_bullish,
            min_rsi=config.sector.min_rsi,
            max_rsi=config.sector.max_rsi,
            min_limit_up_count=config.sector.min_limit_up_count,
            require_top_10pct_3d=config.sector.require_top_10pct_3d,
            top_sectors=config.sector.top_sectors,
        )
    )
    sector_scores = sector_analyzer.calculate_sector_scores(date)
    if not sector_scores:
        logger.error("✗ 未筛选出强势板块，终止流程")
        return []

    sector_names = [s.sector_name for s in sector_scores]
    logger.info(f"✓ 筛选出 {len(sector_names)} 个强势板块")

    # ── 步骤2: 个股量化选股 ──────────────────────────────────
    logger.info("\n【步骤2/4】个股量化选股")
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
            max_stocks_per_sector=config.chase.max_stocks_per_sector,
        ),
        dip_config=DipStrategyConfig(
            max_close_ma_deviation=config.dip.max_close_ma_deviation,
            require_macd_golden_cross=config.dip.require_macd_golden_cross,
            max_volume_ratio_5d=config.dip.max_volume_ratio_5d,
            require_sector_inflow=config.dip.require_sector_inflow,
            max_stocks_per_sector=config.dip.max_stocks_per_sector,
            enable_rsi_oversold=config.dip.enable_rsi_oversold,
            rsi_oversold_threshold=config.dip.rsi_oversold_threshold,
        ),
        risk_config=RiskFilterConfig(
            exclude_loss_maker=config.risk.exclude_loss_maker,
            exclude_reduction=config.risk.exclude_reduction,
            exclude_suspend=config.risk.exclude_suspend,
            min_market_cap=config.risk.min_market_cap,
            max_market_cap=config.risk.max_market_cap,
            exclude_non_main_board=config.risk.exclude_non_main_board,
        ),
    )
    selected_stocks = stock_selector.select_stocks(
        sector_names=sector_names, date=date, strategy_type='both'
    )
    chase_count = len(selected_stocks.get('chase', []))
    dip_count = len(selected_stocks.get('dip', []))
    logger.info(f"✓ 追涨策略: {chase_count} 只  低吸策略: {dip_count} 只")

    if chase_count == 0 and dip_count == 0:
        logger.warning("✗ 未选出任何股票，终止流程")
        return []

    # ── 步骤3: 交易规则量化计算 ──────────────────────────────
    logger.info("\n【步骤3/4】交易规则量化计算")
    position_manager = PositionManager(
        position_config=PositionConfig(
            max_sector_position=config.position.max_sector_position,
            max_stock_position=config.position.max_stock_position,
            max_total_position=config.position.max_total_position,
            sector_rank_1_2_position=config.position.sector_rank_1_2_position,
            sector_rank_3_5_position=config.position.sector_rank_3_5_position,
        ),
        stop_loss_config=StopLossConfig(
            stop_loss_pct_close=config.stop_loss.stop_loss_pct_close,
            use_ma5_stop=config.stop_loss.use_ma5_stop,
            use_atr_stop=config.stop_loss.use_atr_stop,
            atr_multiplier=config.stop_loss.atr_multiplier,
            atr_period=config.stop_loss.atr_period,
            max_loss_pct=config.stop_loss.max_loss_pct,
        ),
        take_profit_config=TakeProfitConfig(
            use_10d_high=config.take_profit.use_10d_high,
            take_profit_pct_close=config.take_profit.take_profit_pct_close,
            enable_gradient=config.take_profit.enable_gradient,
            gradient_10pct_sell_ratio=config.take_profit.gradient_10pct_sell_ratio,
            gradient_20pct_sell_ratio=config.take_profit.gradient_20pct_sell_ratio,
            use_atr_tp=config.take_profit.use_atr_tp,
            atr_tp_multiplier=config.take_profit.atr_tp_multiplier,
        ),
        open_trigger_config=OpenTriggerConfig(
            min_high_open_pct=config.open_trigger.min_high_open_pct,
            max_high_open_pct=config.open_trigger.max_high_open_pct,
            min_seal_ratio=config.open_trigger.min_seal_ratio,
            min_auction_amount=config.open_trigger.min_auction_amount,
        ),
    )
    trading_plans = position_manager.generate_trading_plans(
        selected_stocks=selected_stocks, sector_scores=sector_scores, date=date
    )
    logger.info(f"✓ 生成 {len(trading_plans)} 个交易计划")

    # ── 步骤4: 保存到数据库 ──────────────────────────────────
    logger.info("\n【步骤4/4】保存到数据库")
    try:
        with db.get_session() as session:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            session.query(DailyOperationList).filter(
                DailyOperationList.date == date_obj
            ).delete()

            for plan in trading_plans:
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
                    open_trigger_high_pct=float(plan.open_trigger_high_pct[0]),
                    open_trigger_seal_ratio=float(plan.open_trigger_seal_ratio),
                    open_trigger_auction_amount=float(plan.open_trigger_auction_amount),
                    strength_score=float(plan.strength_score),
                    is_executed=False,
                )
                session.add(record)
            session.commit()

        logger.success(f"✓ 成功保存 {len(trading_plans)} 条交易计划")

    except Exception as e:
        logger.error(f"✗ 保存数据库失败: {e}")
        raise

    logger.success(f"✓✓✓ 每日操作清单生成完成! 日期={date} 板块={len(sector_names)} 选股={chase_count+dip_count} 计划={len(trading_plans)}")
    return trading_plans
