"""
多因子ETF筛选器 - Multi Factor ETF Filter

功能:
1. 综合多个维度筛选ETF: 动量、质量、技术面、流动性
2. 可配置的因子权重
3. 支持动态调整筛选条件

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from core.etf_universe import EtfUniverse
from database.pg_manager import get_db


@dataclass
class MultiFactorConfig:
    """多因子筛选配置"""
    # 动量因子权重
    momentum_weight: float = 0.35
    # 质量/风险因子权重
    quality_weight: float = 0.25
    # 技术面因子权重
    technical_weight: float = 0.20
    # 流动性因子权重
    liquidity_weight: float = 0.20

    # 动量因子配置
    momentum_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    min_trend_score: float = 0.0  # 最小趋势评分

    # 质量因子配置
    max_volatility_pct: float = 10.0  # 最大波动率百分比 (ATR/价格 * 100)
    max_drawdown_pct: float = 30.0  # 最大回撤百分比
    min_sharpe_estimate: float = -1.0  # 最小夏普估计

    # 技术面因子配置
    rsi_enabled: bool = True
    rsi_min: float = 30.0
    rsi_max: float = 70.0
    macd_enabled: bool = True  # MACD金叉
    bollinger_enabled: bool = True  # 布林带位置
    bollinger_min: float = 0.2  # 价格在布林带中的最小位置
    bollinger_max: float = 0.8  # 价格在布林带中的最大位置

    # 流动性因子配置
    min_avg_amount: float = 3000  # 最小日均成交额(万元)
    min_turnover_rate: float = 1.0  # 最小换手率(%)
    liquidity_days: int = 20

    # 数据质量
    min_data_days: int = 180

    # 目标数量
    target_count: int = 50

    # 相关性过滤
    max_correlation: float = 0.85  # 最大允许的成对相关系数

    def __post_init__(self):
        """验证配置参数"""
        total_weight = (self.momentum_weight + self.quality_weight +
                       self.technical_weight + self.liquidity_weight)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"因子权重总和={total_weight:.2f}, 建议调整为1.0")


class MultiFactorETFFilter:
    """
    多因子ETF筛选器

    核心功能:
    1. 综合评分: 动量 + 质量 + 技术面 + 流动性
    2. 可配置权重
    3. 支持多种因子组合
    """

    # 因子缓存
    _factor_cache: Dict[str, pd.DataFrame] = {}

    def __init__(self, config: MultiFactorConfig = None, db=None):
        """
        初始化多因子ETF筛选器

        Args:
            config: 筛选配置
            db: 数据库连接
        """
        self.config = config or MultiFactorConfig()
        self.db = db if db else get_db()
        self.universe = EtfUniverse(db=self.db)

        # 清空缓存
        self._factor_cache = {}

    def filter_etfs(self,
                   initial_symbols: List[str] = None,
                   end_date: str = None) -> List[str]:
        """
        执行多因子筛选

        Args:
            initial_symbols: 初始ETF列表 (如策略指定的ETF池)
            end_date: 截止日期 (YYYYMMDD, 默认当前日期)

        Returns:
            筛选后的ETF代码列表 (按综合评分排序)
        """
        import time
        start_time = time.time()

        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info("=" * 60)
        logger.info(f"多因子ETF筛选开始 - 截止日期: {end_date}")
        logger.info("=" * 60)

        # 第1步: 获取基础ETF池
        base_symbols = self._get_base_symbols(initial_symbols, end_date)
        logger.info(f"✓ 基础ETF池: {len(base_symbols)} 只")

        if not base_symbols:
            logger.warning("基础ETF池为空")
            return []

        # 第2步: 加载因子数据
        factor_data = self._load_factor_data(base_symbols, end_date)
        logger.info(f"✓ 因子数据加载完成")

        # 第3步: 计算各因子得分
        scores = self._calculate_factor_scores(factor_data, end_date)
        logger.info(f"✓ 因子得分计算完成")

        # 第4步: 计算综合得分并排序
        ranked_etfs = self._rank_by_composite_score(scores)

        # 第5步: 相关性过滤（剔除高度相关的ETF，保留评分更高的）
        if self.config.max_correlation < 1.0:
            ranked_etfs = self._apply_correlation_filter(ranked_etfs, factor_data)
            logger.info(f"✓ 相关性过滤完成 (阈值={self.config.max_correlation})")

        final_count = min(len(ranked_etfs), self.config.target_count)
        final_etfs = [s for s, _ in ranked_etfs[:final_count]]

        # 打印Top 10详情
        if final_etfs:
            logger.info(f"\n✓ 最终筛选结果 (Top 10):")
            for i, (symbol, score) in enumerate(ranked_etfs[:10], 1):
                detail = scores.get(symbol, {})
                logger.info(f"  {i}. {symbol}: 综合={score:.3f} | "
                          f"动量={detail.get('momentum', 0):.2f} | "
                          f"质量={detail.get('quality', 0):.2f} | "
                          f"技术={detail.get('technical', 0):.2f} | "
                          f"流动={detail.get('liquidity', 0):.2f}")

        elapsed = time.time() - start_time
        logger.success(f"✓ 筛选完成! 最终: {len(final_etfs)} 只ETF, 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return final_etfs

    def _get_base_symbols(self, initial_symbols: List[str], end_date: str) -> List[str]:
        """获取基础ETF池"""
        if initial_symbols:
            # 验证数据可用性
            all_etfs = self.universe.get_all_etfs(min_data_days=self.config.min_data_days)
            return list(set(initial_symbols) & set(all_etfs))
        else:
            # 使用全市场ETF
            return self.universe.get_all_etfs(min_data_days=self.config.min_data_days)

    def _load_factor_data(self, symbols: List[str], end_date: str) -> Dict[str, pd.DataFrame]:
        """
        加载因子数据

        Returns:
            {symbol: DataFrame包含所有需要的因子}
        """
        # 计算起始日期 (需要足够历史数据计算因子)
        max_period = max(self.config.momentum_periods + [60, 20])  # 额外缓冲
        start_date = (datetime.strptime(end_date, '%Y%m%d') -
                     timedelta(days=max_period * 2)).strftime('%Y%m%d')

        try:
            from datafeed.db_dataloader import DbDataLoader

            loader = DbDataLoader(auto_download=False)
            raw_dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            # 计算所有需要的因子
            factor_data = {}
            for symbol in symbols:
                if symbol not in raw_dfs or raw_dfs[symbol].empty:
                    continue

                df = raw_dfs[symbol].copy()
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date').sort_index()

                # 计算动量因子
                for period in self.config.momentum_periods:
                    df[f'roc_{period}'] = df['close'] / df['close'].shift(period) - 1

                # 计算趋势评分 (使用factor_extends)
                try:
                    from datafeed.factor_extends import trend_score
                    df['trend_score'] = trend_score(df['close'], 25)
                except:
                    df['trend_score'] = 0

                # 计算ATR (波动率)
                df['atr'] = self._calculate_atr(df)
                df['atr_pct'] = df['atr'] / df['close'] * 100

                # 计算RSI
                if self.config.rsi_enabled:
                    df['rsi'] = self._calculate_rsi(df['close'], 14)

                # 计算MACD
                if self.config.macd_enabled:
                    df['macd'], df['macd_signal'], _ = self._calculate_macd(df['close'])

                # 计算布林带
                if self.config.bollinger_enabled:
                    df['bb_upper'], df['bb_mid'], df['bb_lower'] = self._calculate_bollinger(df['close'])
                    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
                    df['bb_position'] = df['bb_position'].clip(0, 1)

                # 计算换手率均值
                if 'turnover_rate' in df.columns:
                    df['avg_turnover'] = df['turnover_rate'].rolling(self.config.liquidity_days).mean()
                else:
                    df['avg_turnover'] = 0

                # 计算成交额均值
                if 'amount' in df.columns:
                    df['avg_amount'] = df['amount'].rolling(self.config.liquidity_days).mean()
                else:
                    df['avg_amount'] = 0

                factor_data[symbol] = df

            return factor_data

        except Exception as e:
            logger.error(f"加载因子数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _calculate_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算ATR (平均真实波幅)"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

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
        signal = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal, macd - signal

    def _calculate_bollinger(self, close: pd.Series, period: int = 20, std_mult: int = 2):
        """计算布林带"""
        mid = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = mid + std_mult * std
        lower = mid - std_mult * std
        return upper, mid, lower

    def _calculate_factor_scores(self, factor_data: Dict[str, pd.DataFrame],
                                end_date: str) -> Dict[str, Dict[str, float]]:
        """
        计算各因子得分 (0-100标准化)

        Returns:
            {symbol: {'momentum': x, 'quality': x, 'technical': x, 'liquidity': x}}
        """
        scores = {}

        # 收集所有ETF的原始因子值，用于标准化
        all_momentum_raw = []
        all_quality_raw = []
        all_technical_raw = []
        all_liquidity_raw = []

        symbol_raw_values = {}

        for symbol, df in factor_data.items():
            if df.empty:
                continue

            # 获取最新值
            latest = df.iloc[-1]

            # 动量因子得分
            momentum_value = self._calc_momentum_score(df, latest)
            all_momentum_raw.append(momentum_value)

            # 质量/风险因子得分
            quality_value = self._calc_quality_score(df, latest)
            all_quality_raw.append(quality_value)

            # 技术面因子得分
            technical_value = self._calc_technical_score(df, latest)
            all_technical_raw.append(technical_value)

            # 流动性因子得分
            liquidity_value = self._calc_liquidity_score(df, latest)
            all_liquidity_raw.append(liquidity_value)

            symbol_raw_values[symbol] = {
                'momentum': momentum_value,
                'quality': quality_value,
                'technical': technical_value,
                'liquidity': liquidity_value
            }

        # 标准化到0-100
        def normalize(values):
            if not values or len(set(values)) <= 1:
                return {v: 50 for v in values}
            min_val, max_val = min(values), max(values)
            return {v: (v - min_val) / (max_val - min_val) * 100 if max_val > min_val else 50
                   for v in values}

        momentum_norm = normalize(all_momentum_raw)
        quality_norm = normalize(all_quality_raw)
        technical_norm = normalize(all_technical_raw)
        liquidity_norm = normalize(all_liquidity_raw)

        # 组装最终得分
        for symbol in symbol_raw_values:
            raw = symbol_raw_values[symbol]
            scores[symbol] = {
                'momentum': momentum_norm[raw['momentum']],
                'quality': quality_norm[raw['quality']],
                'technical': technical_norm[raw['technical']],
                'liquidity': liquidity_norm[raw['liquidity']]
            }

        return scores

    def _calc_momentum_score(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """计算动量因子得分 (原始值, 非标准化)"""
        score = 0.0
        weights = {5: 0.15, 10: 0.25, 20: 0.35, 60: 0.25}

        for period, weight in weights.items():
            col = f'roc_{period}'
            if col in df.columns and not pd.isna(latest[col]):
                score += latest[col] * weight * 100  # 转为百分比

        # 趋势评分加分（限制上界避免主导）
        if 'trend_score' in df.columns and not pd.isna(latest['trend_score']):
            capped_ts = np.clip(latest['trend_score'], -0.2, 0.2)  # 限制在[-0.2, 0.2]
            score += capped_ts * 50  # 最大贡献±10，与ROC项量级一致

        return score

    def _calc_quality_score(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """计算质量/风险因子得分 (原始值, 非标准化)"""
        score = 0.0

        # 波动率惩罚 (ATR% 越低越好)
        if 'atr_pct' in df.columns and not pd.isna(latest['atr_pct']):
            volatility_penalty = max(0, latest['atr_pct'] - 2)  # 2%以下不惩罚
            score -= volatility_penalty * 2

        # 年化夏普比率估计 (扣除无风险利率)
        if 'roc_20' in df.columns and 'atr_pct' in df.columns:
            if not pd.isna(latest['roc_20']) and not pd.isna(latest['atr_pct']) and latest['atr_pct'] > 0:
                # 年化收益估计
                annual_return_est = latest['roc_20'] * 252 / 20
                # 年化波动率估计
                annual_vol_est = latest['atr_pct'] * np.sqrt(252)
                # 扣除无风险利率 (~2.5% 中国国债)
                risk_free_rate = 0.025
                if annual_vol_est > 0:
                    sharpe_est = (annual_return_est - risk_free_rate) / annual_vol_est
                    score += np.clip(sharpe_est, -3, 3) * 2  # 限制极端值

        return score

    def _calc_technical_score(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """计算技术面因子得分 (原始值, 非标准化)"""
        score = 0.0

        # RSI得分 (30-70之间加分)
        if self.config.rsi_enabled and 'rsi' in df.columns:
            rsi = latest.get('rsi', 50)
            if 30 <= rsi <= 70:
                # 中性区域加分,越接近50越好
                score += (1 - abs(rsi - 50) / 20) * 30
            elif rsi > 70:
                score -= (rsi - 70) * 2  # 超买惩罚
            else:
                score -= (30 - rsi)  # 超卖小惩罚

        # MACD金叉加分
        if self.config.macd_enabled and 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = latest.get('macd', 0)
            signal = latest.get('macd_signal', 0)
            if macd > signal:
                score += 20

        # 布林带位置 (避免极端位置)
        if self.config.bollinger_enabled and 'bb_position' in df.columns:
            bb_pos = latest.get('bb_position', 0.5)
            if self.config.bollinger_min <= bb_pos <= self.config.bollinger_max:
                score += 15
            else:
                score -= abs(bb_pos - 0.5) * 30

        return score

    def _calc_liquidity_score(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """计算流动性因子得分 (原始值, 非标准化)"""
        score = 0.0

        # 成交额得分
        if 'avg_amount' in df.columns:
            amount = latest.get('avg_amount', 0)
            score += min(amount / 1000, 50)  # 每1000万加1分,最高50分

        # 换手率得分
        if 'avg_turnover' in df.columns:
            turnover = latest.get('avg_turnover', 0)
            score += min(turnover * 5, 50)  # 每1%换手率加5分

        return score

    def _rank_by_composite_score(self, scores: Dict[str, Dict[str, float]]) -> List[Tuple[str, float]]:
        """
        计算综合得分并排序

        Returns:
            [(symbol, composite_score), ...] 按综合得分降序
        """
        cfg = self.config

        ranked = []
        for symbol, factor_scores in scores.items():
            composite = (
                factor_scores['momentum'] * cfg.momentum_weight +
                factor_scores['quality'] * cfg.quality_weight +
                factor_scores['technical'] * cfg.technical_weight +
                factor_scores['liquidity'] * cfg.liquidity_weight
            )
            ranked.append((symbol, composite))

        # 按综合得分降序排序
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _apply_correlation_filter(
        self,
        ranked_etfs: List[Tuple[str, float]],
        factor_data: Dict[str, pd.DataFrame]
    ) -> List[Tuple[str, float]]:
        """
        相关性过滤：逐一选入ETF，跳过与已选集合高度相关的

        Args:
            ranked_etfs: 按综合得分排序的 [(symbol, score), ...]
            factor_data: {symbol: DataFrame} 因子数据

        Returns:
            过滤后的 [(symbol, score), ...]
        """
        if not ranked_etfs:
            return ranked_etfs

        max_corr = self.config.max_correlation
        selected = []
        selected_closes = {}  # {symbol: close_series}

        for symbol, score in ranked_etfs:
            if symbol not in factor_data:
                continue

            df = factor_data[symbol]
            if 'close' not in df.columns or len(df) < 20:
                continue

            close = df['close'].dropna()

            # 检查与已选集合的相关性
            is_correlated = False
            for sel_symbol, sel_close in selected_closes.items():
                # 对齐日期计算相关性
                aligned = pd.concat([close, sel_close], axis=1, join='inner')
                if len(aligned) < 20:
                    continue

                corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
                if not pd.isna(corr) and abs(corr) > max_corr:
                    logger.debug(f"跳过 {symbol}: 与 {sel_symbol} 相关性={corr:.3f} > {max_corr}")
                    is_correlated = True
                    break

            if not is_correlated:
                selected.append((symbol, score))
                selected_closes[symbol] = close

        logger.info(f"相关性过滤: {len(ranked_etfs)} → {len(selected)} 只ETF")
        return selected


# 预定义配置模板
class MultiFactorPresets:
    """预设多因子筛选配置"""

    @staticmethod
    def aggressive_growth() -> MultiFactorConfig:
        """激进成长型: 高动量权重"""
        return MultiFactorConfig(
            momentum_weight=0.50,
            quality_weight=0.15,
            technical_weight=0.15,
            liquidity_weight=0.20,
            min_trend_score=0.02,
            max_volatility_pct=15.0,
            target_count=50
        )

    @staticmethod
    def balanced() -> MultiFactorConfig:
        """平衡型: 均衡各因子 (默认)"""
        return MultiFactorConfig()

    @staticmethod
    def defensive_quality() -> MultiFactorConfig:
        """防御质量型: 高质量权重,低波动"""
        return MultiFactorConfig(
            momentum_weight=0.20,
            quality_weight=0.40,
            technical_weight=0.10,
            liquidity_weight=0.30,
            max_volatility_pct=5.0,
            rsi_min=40,
            rsi_max=60,
            min_avg_amount=10000,  # 更高流动性要求
            target_count=30
        )

    @staticmethod
    def technical_trend() -> MultiFactorConfig:
        """技术趋势型: 高技术面权重"""
        return MultiFactorConfig(
            momentum_weight=0.30,
            quality_weight=0.10,
            technical_weight=0.45,
            liquidity_weight=0.15,
            rsi_enabled=True,
            macd_enabled=True,
            bollinger_enabled=True,
            target_count=40
        )


if __name__ == '__main__':
    """测试代码"""
    from loguru import logger

    logger.info('多因子ETF筛选器测试')

    # 测试: 平衡型筛选
    config = MultiFactorPresets.balanced()
    filter_engine = MultiFactorETFFilter(config)

    # 测试: 从部分ETF池筛选
    test_symbols = [
        '510300.SH',  # 沪深300ETF
        '510500.SH',  # 中证500ETF
        '159915.SZ',  # 创业板ETF
        '512100.SH',  # 中证1000ETF
        '588000.SH',  # 科创50ETF
        '513100.SH',  # 纳指100ETF
        '518880.SH',  # 黄金ETF
    ]

    filtered_etfs = filter_engine.filter_etfs(initial_symbols=test_symbols)
    logger.info(f"筛选结果: {len(filtered_etfs)} 只ETF: {filtered_etfs}")
