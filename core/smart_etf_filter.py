"""
智能ETF筛选模块 - Smart ETF Filter

功能:
1. 多层级ETF筛选 (基础 → 流动性 → 数量限制)
2. 高性能预筛选,大幅减少计算量
3. 可配置的筛选条件
4. 与ETF信号生成器无缝集成

作者: AITrader
日期: 2026-01-16
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from core.etf_universe import EtfUniverse
from database.pg_manager import get_db


@dataclass
class EtfFilterConfig:
    """ETF筛选配置"""
    # 流动性筛选
    min_avg_amount: float = 5000  # 最小日均成交额(万元)
    min_turnover_rate: float = 1.5  # 最小换手率(%)
    liquidity_days: int = 20  # 流动性统计天数

    # 数据质量
    min_data_days: int = 180  # 最小历史数据天数

    # 目标数量
    target_count: int = 100  # 目标ETF数量

    # ========== 新增: 技术指标筛选 ==========
    # 是否启用技术指标筛选
    use_technical_filter: bool = False

    # RSI筛选 (None表示不限制)
    rsi_min: float = None  # RSI最小值
    rsi_max: float = None  # RSI最大值
    rsi_period: int = 14  # RSI周期

    # MACD筛选
    macd_golden_cross: bool = False  # 是否要求MACD金叉

    # 波动率筛选 (ATR/价格)
    max_volatility_pct: float = None  # 最大波动率百分比

    # 趋势筛选 (使用trend_score)
    min_trend_score: float = None  # 最小趋势评分

    # 动量筛选
    min_roc: float = None  # 最小收益率 (如0.02表示2%)
    roc_period: int = 20  # 动量周期

    def __post_init__(self):
        """验证配置参数的合理性"""
        if self.min_avg_amount < 0:
            raise ValueError(f"min_avg_amount必须>=0, 当前值: {self.min_avg_amount}")
        if self.min_turnover_rate < 0:
            raise ValueError(f"min_turnover_rate必须>=0, 当前值: {self.min_turnover_rate}")
        if self.min_data_days < 1:
            raise ValueError(f"min_data_days必须>=1, 当前值: {self.min_data_days}")
        if self.target_count < 1:
            raise ValueError(f"target_count必须>=1, 当前值: {self.target_count}")
        if self.liquidity_days < 1:
            raise ValueError(f"liquidity_days必须>=1, 当前值: {self.liquidity_days}")


class SmartETFFilter:
    """
    智能ETF筛选器

    核心功能:
    1. 多层级筛选: 基础 → 流动性 → 数量限制
    2. 性能优化: 快速过滤,减少后续计算量
    3. 灵活配置: 支持不同策略使用不同筛选条件
    """

    def __init__(self, config: EtfFilterConfig = None, db=None):
        """
        初始化智能ETF筛选器

        Args:
            config: 筛选配置
            db: 数据库连接
        """
        self.config = config or EtfFilterConfig()
        self.db = db if db else get_db()
        self.universe = EtfUniverse(db=self.db)

    def filter_etfs(self,
                   initial_symbols: List[str] = None) -> List[str]:
        """
        执行多层级筛选

        Args:
            initial_symbols: 初始ETF列表 (如策略指定的ETF池,为None则使用全部)

        Returns:
            筛选后的ETF代码列表
        """
        import time
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"智能ETF筛选开始 - 初始ETF数: {len(initial_symbols) if initial_symbols else '全市场'}")
        logger.info("=" * 60)

        # 第0层: 基础过滤 (数据可用性)
        symbols = self._layer0_base_filter(initial_symbols)
        logger.info(f"✓ 第0层(基础过滤): {len(symbols)} 只ETF")

        if not symbols:
            logger.warning("基础过滤后无ETF")
            return []

        # 第1层: 流动性筛选
        symbols = self._layer1_liquidity_filter(symbols)
        logger.info(f"✓ 第1层(流动性筛选): {len(symbols)} 只ETF")

        if not symbols:
            logger.warning("流动性筛选后无ETF")
            return []

        # 第1.5层: 技术指标筛选 (新增)
        if self.config.use_technical_filter:
            symbols = self._layer1_5_technical_filter(symbols)
            logger.info(f"✓ 第1.5层(技术指标筛选): {len(symbols)} 只ETF")

            if not symbols:
                logger.warning("技术指标筛选后无ETF")
                return []

        # 最终限制数量
        if len(symbols) > self.config.target_count:
            symbols = self._limit_by_amount(symbols)
            logger.info(f"✓ 最终限制: {len(symbols)} 只ETF (目标{self.config.target_count}只)")
        else:
            logger.info(f"✓ 筛选完成: {len(symbols)} 只ETF (无需限制)")

        elapsed = time.time() - start_time
        logger.success(f"✓ 筛选完成! 最终: {len(symbols)} 只ETF, 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return symbols

    def _layer0_base_filter(self, initial_symbols: List[str]) -> List[str]:
        """
        第0层: 基础过滤

        过滤条件:
        - 数据充足 (至少min_data_days天历史数据)
        """
        # 如果提供了初始ETF列表,需要验证数据可用性
        if initial_symbols:
            # 验证这些ETF是否有足够数据
            all_etfs = self.universe.get_all_etfs(min_data_days=self.config.min_data_days)
            # 取交集: 初始列表 ∩ 有足够数据的ETF
            base_symbols = list(set(initial_symbols) & set(all_etfs))
            logger.debug(f"基础过滤(数据可用性): {len(initial_symbols)} -> {len(base_symbols)}")
            return base_symbols
        else:
            # 使用全市场ETF
            base_symbols = self.universe.get_all_etfs(
                min_data_days=self.config.min_data_days
            )
            return base_symbols

    def _layer1_liquidity_filter(self, symbols: List[str]) -> List[str]:
        """
        第1层: 流动性筛选

        指标:
        - 成交额 (amount)
        - 换手率 (turnover_rate)
        """
        if not self.config.min_avg_amount and not self.config.min_turnover_rate:
            return symbols

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=self.config.liquidity_days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载流动性数据")
                return symbols

            # 计算流动性指标
            qualified = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty:
                    continue

                passed = True

                # 检查换手率
                if self.config.min_turnover_rate and 'turnover_rate' in df.columns:
                    recent_turnover = df['turnover_rate'].tail(self.config.liquidity_days)

                    # 检查数据是否为空或全为NaN
                    if not recent_turnover.empty and not recent_turnover.isna().all():
                        if recent_turnover.mean() < self.config.min_turnover_rate:
                            passed = False

                # 检查成交额
                if self.config.min_avg_amount and 'amount' in df.columns:
                    recent_amount = df['amount'].tail(self.config.liquidity_days)

                    # 检查数据是否为空或全为NaN
                    if not recent_amount.empty and not recent_amount.isna().all():
                        if recent_amount.mean() < self.config.min_avg_amount:
                            passed = False

                if passed:
                    qualified.append(symbol)

            logger.debug(f"流动性筛选: {len(symbols)} -> {len(qualified)}")
            return qualified

        except Exception as e:
            logger.error(f"流动性筛选失败: {e}")
            return symbols

    def _layer1_5_technical_filter(self, symbols: List[str]) -> List[str]:
        """
        第1.5层: 技术指标筛选 (新增)

        指标:
        - RSI (避免超买超卖)
        - MACD (金叉/死叉)
        - 波动率 (剔除极端波动)
        - 趋势评分 (trend_score)
        - 动量 (ROC)
        """
        cfg = self.config

        if not cfg.use_technical_filter:
            return symbols

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围 (需要足够历史数据计算指标)
            max_period = max(
                cfg.rsi_period or 14,
                cfg.roc_period or 20,
                60  # 趋势评分等
            )
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=max_period * 2)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载技术指标数据")
                return symbols

            qualified = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty or 'close' not in df.columns:
                    continue

                # 确保日期索引
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')

                passed = True

                # 1. RSI筛选
                if cfg.rsi_min is not None or cfg.rsi_max is not None:
                    rsi = self._calculate_rsi(df['close'], cfg.rsi_period)
                    latest_rsi = rsi.iloc[-1] if len(rsi) > 0 else None

                    if latest_rsi is not None and not pd.isna(latest_rsi):
                        if cfg.rsi_min is not None and latest_rsi < cfg.rsi_min:
                            passed = False
                        if cfg.rsi_max is not None and latest_rsi > cfg.rsi_max:
                            passed = False

                # 2. MACD金叉筛选
                if cfg.macd_golden_cross and passed:
                    macd, signal, _ = self._calculate_macd(df['close'])
                    if len(macd) >= 2:
                        # 金叉: MACD上穿信号线
                        latest_macd = macd.iloc[-1]
                        latest_signal = signal.iloc[-1]
                        prev_macd = macd.iloc[-2]
                        prev_signal = signal.iloc[-2]

                        # 最近出现金叉
                        is_golden_cross = (latest_macd > latest_signal and
                                        prev_macd <= prev_signal)

                        if not is_golden_cross:
                            passed = False

                # 3. 波动率筛选
                if cfg.max_volatility_pct is not None and passed:
                    atr = self._calculate_atr(df)
                    atr_pct = atr.iloc[-1] / df['close'].iloc[-1] * 100 if len(atr) > 0 else 0

                    if atr_pct > cfg.max_volatility_pct:
                        passed = False

                # 4. 趋势评分筛选
                if cfg.min_trend_score is not None and passed:
                    try:
                        from datafeed.factor_extends import trend_score
                        ts = trend_score(df['close'], 25)
                        latest_ts = ts.iloc[-1] if len(ts) > 0 else 0

                        if latest_ts < cfg.min_trend_score:
                            passed = False
                    except:
                        pass  # 计算失败则跳过

                # 5. 动量筛选
                if cfg.min_roc is not None and passed:
                    period = cfg.roc_period
                    if len(df['close']) > period:
                        roc = df['close'].iloc[-1] / df['close'].iloc[-period] - 1
                        if roc < cfg.min_roc:
                            passed = False

                if passed:
                    qualified.append(symbol)

            logger.debug(f"技术指标筛选: {len(symbols)} -> {len(qualified)}")
            return qualified

        except Exception as e:
            logger.error(f"技术指标筛选失败: {e}")
            return symbols

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD"""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line, macd - signal_line

    def _calculate_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算ATR"""
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _limit_by_amount(self, symbols: List[str]) -> List[str]:
        """
        按成交额限制数量

        策略: 按成交额排序,选择前N只
        """
        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=self.config.liquidity_days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载成交额数据,返回前{self.config.target_count}只")
                return symbols[:self.config.target_count]

            # 计算每个ETF的平均成交额并排序
            etf_amounts = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty or 'amount' not in df.columns:
                    continue

                # 计算平均成交额
                recent_amount = df['amount'].tail(self.config.liquidity_days)

                # 检查数据是否为空或全为NaN
                if recent_amount.empty or recent_amount.isna().all():
                    continue

                avg_amount = recent_amount.mean()

                if pd.notna(avg_amount):
                    etf_amounts.append((symbol, avg_amount))

            # 按成交额降序排序
            etf_amounts.sort(key=lambda x: x[1], reverse=True)

            # 取前N只
            result = [item[0] for item in etf_amounts[:self.config.target_count]]

            logger.debug(f"按成交额限制数量: {len(symbols)} -> {len(result)} (前{self.config.target_count}只)")
            return result

        except Exception as e:
            logger.error(f"数量限制失败: {e}")
            return symbols[:self.config.target_count]


# 预定义配置模板
class EtfFilterPresets:
    """预设ETF筛选配置"""

    @staticmethod
    def conservative() -> EtfFilterConfig:
        """保守型: 高流动性大ETF"""
        return EtfFilterConfig(
            min_avg_amount=10000,  # 1亿成交额
            min_turnover_rate=2.0,
            min_data_days=252,  # 1年数据
            liquidity_days=20,
            target_count=50
        )

    @staticmethod
    def balanced() -> EtfFilterConfig:
        """平衡型: 适中流动性 (默认)"""
        return EtfFilterConfig(
            min_avg_amount=5000,  # 5000万成交额
            min_turnover_rate=1.5,
            min_data_days=180,  # 半年数据
            liquidity_days=20,
            target_count=100
        )

    @staticmethod
    def aggressive() -> EtfFilterConfig:
        """激进型: 包含小ETF"""
        return EtfFilterConfig(
            min_avg_amount=3000,
            min_turnover_rate=1.0,
            min_data_days=180,
            liquidity_days=20,
            target_count=150
        )


if __name__ == '__main__':
    """测试代码"""
    logger.info('智能ETF筛选模块测试')

    # 测试: 平衡型筛选
    config = EtfFilterPresets.balanced()
    smart_filter = SmartETFFilter(config)

    filtered_etfs = smart_filter.filter_etfs()
    logger.info(f"筛选结果: {len(filtered_etfs)} 只ETF")
    if len(filtered_etfs) > 0:
        logger.info(f"前10只: {filtered_etfs[:10]}")
