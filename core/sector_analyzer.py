"""
板块量化分析模块

功能:
1. 从akshare获取板块资金流数据
2. 计算技术指标(MA5/10, RSI)
3. 统计涨停家数、连板家数
4. 综合评分排序

作者: AITrader
日期: 2026-01-21
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

try:
    import akshare as ak
except ImportError:
    logger.warning("akshare未安装,部分功能将不可用")
    ak = None

from database.pg_manager import get_db
from database.models.models import SectorData, StockHistory, StockMetadata


@dataclass
class SectorConfig:
    """板块筛选配置"""
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
class SectorScore:
    """板块评分结果"""
    sector_code: str
    sector_name: str
    date: str

    # 分项得分
    fund_score: float  # 资金得分 (0-2)
    tech_score: float  # 技术得分 (0-2)
    sentiment_score: float  # 情绪得分 (0-1)

    # 综合得分
    total_score: float  # 加权总分

    # 详细数据
    main_net_inflow_1d: float
    volume_expansion_ratio: float
    is_ma_bullish: bool
    rsi: float
    limit_up_count: int
    rank_3d_gain: Optional[int]


class SectorAnalyzer:
    """
    板块量化分析器

    工作流程:
    1. 获取板块资金流数据 (akshare)
    2. 计算技术指标 (MA5/10, RSI)
    3. 统计涨停家数、连板家数
    4. 综合评分排序
    """

    def __init__(self, config: SectorConfig = None, db=None):
        """
        初始化板块分析器

        Args:
            config: 板块筛选配置
            db: 数据库连接
        """
        self.config = config or SectorConfig()
        self.db = db if db else get_db()

        if ak is None:
            logger.error("akshare未安装,无法获取板块数据")

    def fetch_sector_data(self, date: str) -> pd.DataFrame:
        """
        从akshare获取板块资金流数据

        Args:
            date: 日期 (YYYYMMDD) - 注意: akshare只支持"即时"数据

        Returns:
            板块数据DataFrame
        """
        if ak is None:
            logger.error("akshare未安装")
            return pd.DataFrame()

        try:
            # 注意: akshare只支持"即时"数据,不支持历史日期查询
            # 对于历史日期,将返回空DataFrame,后续会使用数据库fallback
            logger.info(f"正在获取行业板块资金流数据...")

            # 使用 stock_fund_flow_industry (行业资金流)
            try:
                df = ak.stock_fund_flow_industry(symbol='即时')

                # 重命名列以匹配我们的命名
                column_rename = {
                    '行业': 'sector_name',
                    '净额': 'main_net_inflow',
                    '流入资金': 'main_inflow',
                    '流出资金': 'main_outflow',
                    '行业-涨跌幅': 'change_pct',
                    '行业指数': 'sector_index'
                }

                # 只保留需要的列
                existing_cols = {k: v for k, v in column_rename.items() if k in df.columns}
                df.rename(columns=existing_cols, inplace=True)

                # 单位转换: akshare返回的单位是"亿",转换为"万元"
                if 'main_net_inflow' in df.columns:
                    df['main_net_inflow'] = df['main_net_inflow'] * 10000

                logger.info(f"✓ 获取到 {len(df)} 个行业板块数据")
                return df

            except Exception as e:
                logger.warning(f"获取行业资金流失败: {e}")

                # Fallback: 使用板块列表
                try:
                    df_sectors = ak.stock_sector_spot(indicator='新浪行业')

                    # 创建基础数据框架
                    df = pd.DataFrame({
                        'sector_name': df_sectors['板块'],
                        'main_net_inflow': 0.0,
                        'sector_index': df_sectors.get('平均价格', 0),
                        'change_pct': df_sectors.get('涨跌幅', 0)
                    })

                    logger.info(f"✓ 获取到 {len(df)} 个板块列表(无资金流数据)")
                    return df

                except Exception as e2:
                    logger.warning(f"获取板块列表也失败: {e2}")
                    return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return pd.DataFrame()

    def _standardize_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        标准化列名映射

        Args:
            columns: 原始列名列表

        Returns:
            列名映射字典
        """
        mapping = {}

        # 常见的列名变体
        sector_name_variants = ['板块名称', '行业名称', 'name', 'sector_name']
        main_net_inflow_variants = ['主力净流入', '净流入', 'main_net_inflow', 'net_inflow']
        amount_variants = ['成交额', '总成交额', 'amount', 'turnover']

        for col in columns:
            for variant in sector_name_variants:
                if variant in str(col):
                    mapping[col] = 'sector_name'
                    break
            for variant in main_net_inflow_variants:
                if variant in str(col):
                    mapping[col] = 'main_net_inflow'
                    break
            for variant in amount_variants:
                if variant in str(col):
                    mapping[col] = 'amount'
                    break

        return mapping

    def calculate_technical_indicators_from_stocks(
        self,
        sector_name: str,
        end_date: str
    ) -> Dict[str, float]:
        """
        通过板块内股票数据计算技术指标

        Args:
            sector_name: 板块名称
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            技术指标字典 {'close': xxx, 'ma5': xxx, 'ma10': xxx, 'rsi': xxx}
        """
        try:
            end_date_obj = datetime.strptime(end_date, '%Y%m%d')
            start_date_obj = end_date_obj - timedelta(days=60)

            with self.db.get_session() as session:
                # 特殊处理: "全市场"获取所有股票
                if sector_name == "全市场":
                    # 获取该日期有数据的前500只股票
                    query = session.query(
                        StockHistory.symbol,
                        StockHistory.date,
                        StockHistory.close
                    ).filter(
                        StockHistory.date == end_date_obj.date()
                    ).order_by(
                        StockHistory.amount.desc()
                    ).limit(500)

                    df = pd.read_sql(query.statement, session.bind)

                    if df.empty:
                        logger.warning(f"全市场无数据")
                        return {}

                    stock_codes = df['symbol'].unique().tolist()
                    logger.debug(f"全市场有 {len(stock_codes)} 只股票")

                    # 获取历史数据
                    query_history = session.query(
                        StockHistory.symbol,
                        StockHistory.date,
                        StockHistory.close
                    ).filter(
                        StockHistory.symbol.in_(stock_codes),
                        StockHistory.date >= start_date_obj.date(),
                        StockHistory.date <= end_date_obj.date()
                    ).order_by(StockHistory.date)

                    df = pd.read_sql(query_history.statement, session.bind)

                else:
                    # 正常板块筛选
                    stocks = session.query(StockMetadata.symbol).filter(
                        StockMetadata.sector == sector_name
                    ).all()

                    stock_codes = [s[0] for s in stocks]

                    if not stock_codes:
                        logger.warning(f"板块 {sector_name} 内无股票")
                        return {}

                    logger.debug(f"板块 {sector_name} 有 {len(stock_codes)} 只股票")

                    # 获取历史数据
                    query = session.query(
                        StockHistory.symbol,
                        StockHistory.date,
                        StockHistory.close
                    ).filter(
                        StockHistory.symbol.in_(stock_codes),
                        StockHistory.date >= start_date_obj.date(),
                        StockHistory.date <= end_date_obj.date()
                    ).order_by(StockHistory.date)

                    df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                logger.warning(f"板块 {sector_name} 无历史数据")
                return {}

            # 计算板块指数 (简单平均)
            # 先按日期分组,计算每日收盘价均值
            daily_avg = df.groupby('date')['close'].mean().reset_index()
            daily_avg = daily_avg.sort_values('date')

            if len(daily_avg) < 10:
                logger.warning(f"板块 {sector_name} 数据不足10天")
                return {}

            # 计算技术指标
            close = daily_avg['close'].iloc[-1]
            ma5 = daily_avg['close'].tail(5).mean()
            ma10 = daily_avg['close'].tail(10).mean()

            # 判断是否站上均线
            is_ma_bullish = (close > ma5) and (ma5 > ma10)

            # 计算RSI (使用talib)
            try:
                import talib
                closes = daily_avg['close'].values
                rsi = talib.RSI(closes, timeperiod=14)[-1]
                if np.isnan(rsi):
                    rsi = 50.0  # 默认值
            except:
                rsi = 50.0  # 默认值

            return {
                'close': close,
                'ma5': ma5,
                'ma10': ma10,
                'is_ma_bullish': is_ma_bullish,
                'rsi': rsi
            }

        except Exception as e:
            logger.error(f"计算板块 {sector_name} 技术指标失败: {e}")
            return {}

    def count_limit_up_stocks(self, sector_name: str, date: str) -> int:
        """
        统计板块内涨停家数

        Args:
            sector_name: 板块名称
            date: 日期 (YYYYMMDD)

        Returns:
            涨停家数
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()

            with self.db.get_session() as session:
                # 获取该板块的所有股票
                stocks = session.query(StockMetadata.symbol).filter(
                    StockMetadata.sector == sector_name
                ).all()

                stock_codes = [s[0] for s in stocks]

                if not stock_codes:
                    return 0

                # 统计涨停家数 (涨幅≥9.5%)
                limit_up_count = session.query(StockHistory).filter(
                    StockHistory.symbol.in_(stock_codes),
                    StockHistory.date == date_obj,
                    StockHistory.change_pct >= 9.5
                ).count()

                return limit_up_count

        except Exception as e:
            logger.error(f"统计涨停家数失败: {e}")
            return 0

    def calculate_volume_expansion_ratio(
        self,
        sector_name: str,
        date: str
    ) -> float:
        """
        计算成交额放量率

        Args:
            sector_name: 板块名称
            date: 日期 (YYYYMMDD)

        Returns:
            放量率 (当日成交额 / 近5日平均成交额)
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            start_date_obj = date_obj - timedelta(days=10)

            with self.db.get_session() as session:
                # 获取板块内股票
                stocks = session.query(StockMetadata.symbol).filter(
                    StockMetadata.sector == sector_name
                ).all()

                stock_codes = [s[0] for s in stocks]

                if not stock_codes:
                    return 0.0

                # 获取近10日成交额
                query = session.query(
                    StockHistory.date,
                    StockHistory.amount
                ).filter(
                    StockHistory.symbol.in_(stock_codes),
                    StockHistory.date >= start_date_obj,
                    StockHistory.date <= date_obj
                )

                df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                return 0.0

            # 按日期汇总成交额
            daily_amount = df.groupby('date')['amount'].sum().reset_index()
            daily_amount = daily_amount.sort_values('date')

            if len(daily_amount) < 6:
                return 1.0

            # 当日成交额
            today_amount = daily_amount['amount'].iloc[-1]

            # 近5日平均成交额 (不含当日)
            avg_5d_amount = daily_amount['amount'].iloc[-6:-1].mean()

            if avg_5d_amount == 0:
                return 1.0

            return today_amount / avg_5d_amount

        except Exception as e:
            logger.error(f"计算放量率失败: {e}")
            return 1.0

    def calculate_sector_scores(self, date: str) -> List[SectorScore]:
        """
        计算板块综合评分

        优先从数据库读取板块数据，如果没有则调用akshare获取

        Args:
            date: 日期 (YYYYMMDD)

        Returns:
            板块评分列表 (已排序)
        """
        logger.info("=" * 60)
        logger.info(f"开始板块量化筛选: {date}")
        logger.info("=" * 60)

        # 1. 优先从数据库加载板块数据
        date_obj = datetime.strptime(date, '%Y%m%d').date()

        with self.db.get_session() as session:
            sector_data_records = session.query(SectorData).filter(
                SectorData.date == date_obj
            ).order_by(SectorData.strength_score.desc()).all()

            if sector_data_records:
                logger.info(f"✓ 从数据库加载到 {len(sector_data_records)} 条板块数据")

                # 直接从数据库记录转换为评分对象（在session上下文中访问所有属性）
                scores = [
                    SectorScore(
                        sector_code=record.sector_code,
                        sector_name=record.sector_name,
                        date=date,
                        fund_score=0.0,  # 可以根据需要计算
                        tech_score=0.0,
                        sentiment_score=0.0,
                        total_score=record.strength_score,
                        main_net_inflow_1d=record.main_net_inflow_1d,
                        volume_expansion_ratio=record.volume_expansion_ratio,
                        is_ma_bullish=(record.close > record.ma5 and record.ma5 > record.ma10),
                        rsi=record.rsi,
                        limit_up_count=record.limit_up_count,
                        rank_3d_gain=record.rank_3d_gain
                    )
                    for record in sector_data_records
                ]

        if sector_data_records:

            # 只返回前N个
            top_scores = scores[:self.config.top_sectors]

            logger.info("=" * 60)
            logger.info(f"板块筛选完成, Top {len(top_scores)}:")
            for i, score in enumerate(top_scores, 1):
                logger.info(
                    f"  {i}. {score.sector_name}: {score.total_score:.3f} "
                    f"(资金={score.main_net_inflow_1d/10000:.1f}亿, "
                    f"放量={score.volume_expansion_ratio:.2f}, "
                    f"涨停={score.limit_up_count}, "
                    f"RSI={score.rsi:.1f})"
                )
            logger.info("=" * 60)

            return top_scores

        # 2. 如果数据库没有数据，则使用实时计算（fallback）
        logger.info("数据库中无板块数据，尝试实时计算...")

        df_sector = self.fetch_sector_data(date)

        if df_sector.empty:
            logger.warning("未获取到板块数据,尝试从数据库加载")
            # Fallback: 从数据库获取所有板块
            with self.db.get_session() as session:
                sectors = session.query(
                    StockMetadata.sector
                ).distinct().all()
                sector_names = [s[0] for s in sectors if s[0]]
                logger.info(f"从数据库获取到 {len(sector_names)} 个板块")
        else:
            sector_names = df_sector['sector_name'].tolist()

        if not sector_names:
            logger.warning("数据库中无板块数据,使用全市场模式")
            # 使用全市场作为单一板块
            sector_names = ["全市场"]
            logger.info("使用'全市场'作为单一板块进行选股")

        # 2. 计算每个板块的得分
        scores = []

        for sector_name in sector_names:
            try:
                logger.debug(f"分析板块: {sector_name}")

                # 从DataFrame获取资金数据 (如果可用)
                if not df_sector.empty and 'sector_name' in df_sector.columns:
                    sector_row = df_sector[df_sector['sector_name'] == sector_name]
                    if not sector_row.empty:
                        main_net_inflow_1d = sector_row['main_net_inflow'].iloc[0]
                        # 单位转换: akshare返回的单位可能是"亿",转换为"万元"
                        if abs(main_net_inflow_1d) < 1000:  # 如果小于1000,认为是"亿"
                            main_net_inflow_1d = main_net_inflow_1d * 10000
                    else:
                        main_net_inflow_1d = 0.0
                else:
                    main_net_inflow_1d = 0.0

                # 计算放量率
                volume_expansion_ratio = self.calculate_volume_expansion_ratio(
                    sector_name, date
                )

                # 计算技术指标
                tech_indicators = self.calculate_technical_indicators_from_stocks(
                    sector_name, date
                )

                if not tech_indicators:
                    continue

                is_ma_bullish = tech_indicators.get('is_ma_bullish', False)
                rsi = tech_indicators.get('rsi', 50.0)

                # 统计涨停家数
                limit_up_count = self.count_limit_up_stocks(sector_name, date)

                # === 资金得分 (0-2分) ===
                fund_score = 0.0
                if main_net_inflow_1d >= self.config.min_main_net_inflow_1d:
                    fund_score += 1.0
                    logger.debug(f"  ✓ 资金流入: {main_net_inflow_1d:.0f}万 ≥ {self.config.min_main_net_inflow_1d:.0f}万")

                if volume_expansion_ratio >= self.config.min_volume_expansion_ratio:
                    fund_score += 1.0
                    logger.debug(f"  ✓ 放量率: {volume_expansion_ratio:.2f} ≥ {self.config.min_volume_expansion_ratio}")

                # === 技术得分 (0-2分) ===
                tech_score = 0.0
                if is_ma_bullish:
                    tech_score += 1.0
                    logger.debug(f"  ✓ 均线多头排列")

                if self.config.min_rsi <= rsi <= self.config.max_rsi:
                    tech_score += 1.0
                    logger.debug(f"  ✓ RSI: {rsi:.1f} ∈ [{self.config.min_rsi}, {self.config.max_rsi}]")

                # === 情绪得分 (0-1分) ===
                sentiment_score = 0.0
                if limit_up_count >= self.config.min_limit_up_count:
                    sentiment_score += 1.0
                    logger.debug(f"  ✓ 涨停家数: {limit_up_count} ≥ {self.config.min_limit_up_count}")

                # === 综合得分 (加权) ===
                # 资金50%, 技术30%, 情绪20%
                total_score = (
                    fund_score * 0.5 +
                    tech_score * 0.3 +
                    sentiment_score * 0.2
                )

                scores.append(SectorScore(
                    sector_code=sector_name,  # 使用名称作为代码
                    sector_name=sector_name,
                    date=date,
                    fund_score=fund_score,
                    tech_score=tech_score,
                    sentiment_score=sentiment_score,
                    total_score=total_score,
                    main_net_inflow_1d=main_net_inflow_1d,
                    volume_expansion_ratio=volume_expansion_ratio,
                    is_ma_bullish=is_ma_bullish,
                    rsi=rsi,
                    limit_up_count=limit_up_count,
                    rank_3d_gain=None  # 暂不计算
                ))

            except Exception as e:
                logger.error(f"分析板块 {sector_name} 失败: {e}")
                continue

        # 3. 按综合得分排序
        scores.sort(key=lambda x: x.total_score, reverse=True)

        # 4. 返回前N个
        top_scores = scores[:self.config.top_sectors]

        logger.info("=" * 60)
        logger.info(f"板块筛选完成, Top {len(top_scores)}:")
        for i, score in enumerate(top_scores, 1):
            logger.info(
                f"  {i}. {score.sector_name}: {score.total_score:.3f} "
                f"(资金={score.fund_score:.1f}, 技术={score.tech_score:.1f}, 情绪={score.sentiment_score:.1f})"
            )
        logger.info("=" * 60)

        return top_scores

    def save_sector_data(self, scores: List[SectorScore]):
        """
        保存板块数据到数据库

        Args:
            scores: 板块评分列表
        """
        if not scores:
            logger.warning("无板块数据可保存")
            return

        try:
            with self.db.get_session() as session:
                for score in scores:
                    # 获取技术指标
                    tech_indicators = self.calculate_technical_indicators_from_stocks(
                        score.sector_name, score.date
                    )

                    # 转换numpy类型为Python原生类型
                    record = SectorData(
                        date=datetime.strptime(score.date, '%Y%m%d').date(),
                        sector_code=score.sector_code,
                        sector_name=score.sector_name,
                        main_net_inflow_1d=float(score.main_net_inflow_1d),
                        main_net_inflow_3d=0.0,  # 暂未计算
                        main_net_inflow_5d=0.0,  # 暂未计算
                        volume_expansion_ratio=float(score.volume_expansion_ratio),
                        northbound_buy_ratio=0.0,  # 暂未计算
                        limit_up_count=int(score.limit_up_count),
                        consecutive_board_count=0,  # 暂未计算
                        rank_3d_gain=score.rank_3d_gain,
                        close=float(tech_indicators.get('close', 0.0)),
                        ma5=float(tech_indicators.get('ma5', 0.0)),
                        ma10=float(tech_indicators.get('ma10', 0.0)),
                        rsi=float(score.rsi),
                        strength_score=float(score.total_score)
                    )
                    session.merge(record)

                session.commit()
                logger.info(f"✓ 保存 {len(scores)} 个板块数据到数据库")

        except Exception as e:
            logger.error(f"保存板块数据失败: {e}")


if __name__ == '__main__':
    """测试板块分析器"""
    from loguru import logger

    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level="INFO")

    # 创建分析器
    analyzer = SectorAnalyzer(
        config=SectorConfig(
            min_main_net_inflow_1d=100.0,  # 降低阈值用于测试
            min_limit_up_count=1,  # 降低阈值用于测试
            top_sectors=3
        )
    )

    # 测试日期 (使用最近的交易日)
    test_date = "20240115"

    # 计算板块得分
    scores = analyzer.calculate_sector_scores(test_date)

    # 保存到数据库
    analyzer.save_sector_data(scores)

    print("\n✓ 测试完成")
