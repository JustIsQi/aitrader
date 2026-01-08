"""
策略自动发现和加载器

功能:
1. 自动扫描 strategies/ 目录
2. 发现所有 stocks_*.py 策略文件
3. 导入模块并提取策略函数
4. 过滤出 ashare_mode=True 的A股策略
5. 返回策略配置列表

作者: AITrader
日期: 2026-01-06
"""

import sys
import importlib
from pathlib import Path
from typing import List, Tuple, Optional
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.backtrader_engine import Task


class StrategyLoader:
    """策略自动发现和加载器"""

    def __init__(self, strategies_dir: Optional[str] = None):
        """
        初始化策略加载器

        Args:
            strategies_dir: 策略目录路径，默认为项目根目录下的 strategies/
        """
        if strategies_dir is None:
            strategies_dir = project_root / "strategies"
        else:
            strategies_dir = Path(strategies_dir)

        self.strategies_dir = strategies_dir
        logger.debug(f'策略加载器初始化: {self.strategies_dir}')

    def load_ashare_strategies(self) -> List[Tuple[str, str, str, str]]:
        """
        自动加载所有A股策略

        Returns:
            List of tuples: (display_name, module_name, func_name, version)
            - display_name: 策略显示名称 (如 "多因子-周频")
            - module_name: 模块名 (如 "strategies.stocks_多因子智能选股策略")
            - func_name: 函数名 (如 "multi_factor_strategy_weekly")
            - version: 版本标识 (如 "weekly", "monthly", "conservative", "aggressive")
        """
        strategies = []

        # 查找所有 stocks_*.py 文件
        strategy_files = list(self.strategies_dir.glob("stocks_*.py"))

        if not strategy_files:
            logger.warning(f'未找到任何 stocks_*.py 策略文件在 {self.strategies_dir}')
            return strategies

        logger.debug(f'找到 {len(strategy_files)} 个策略文件')

        for py_file in strategy_files:
            module_name = f"strategies.{py_file.stem}"
            logger.debug(f'正在加载模块: {module_name}')

            try:
                # 导入模块
                module = importlib.import_module(module_name)

                # 扫描模块中的所有函数
                for func_name in dir(module):
                    # 跳过私有函数和非策略函数
                    if func_name.startswith('_'):
                        continue

                    # 匹配策略函数命名模式
                    if self._is_strategy_function(func_name):
                        logger.debug(f'  发现策略函数: {func_name}')

                        try:
                            # 获取策略函数
                            func = getattr(module, func_name)

                            # 调用函数获取 Task 对象
                            task = func()

                            # 检查是否为A股策略
                            if hasattr(task, 'ashare_mode') and task.ashare_mode:
                                display_name = task.name
                                version = self._extract_version(func_name)

                                strategies.append((
                                    display_name,
                                    module_name,
                                    func_name,
                                    version
                                ))

                                logger.debug(f'    ✓ 加载成功: {display_name} (version={version})')
                            else:
                                logger.debug(f'    ✗ 跳过非A股策略: {func_name}')

                        except Exception as e:
                            logger.warning(f'    ✗ 加载策略函数 {func_name} 失败: {e}')
                            continue

            except Exception as e:
                logger.error(f'导入模块 {module_name} 失败: {e}')
                continue

        logger.info(f'成功加载 {len(strategies)} 个A股策略')
        return strategies

    def _is_strategy_function(self, func_name: str) -> bool:
        """
        判断函数名是否为策略函数

        Args:
            func_name: 函数名

        Returns:
            是否为策略函数
        """
        # 匹配常见的策略函数命名模式
        strategy_patterns = [
            'multi_factor_',  # 多因子策略
            'momentum_',      # 动量策略
            'value_',         # 价值策略
            'quality_',       # 质量策略
            'low_vol_',       # 低波动策略
        ]

        for pattern in strategy_patterns:
            if func_name.startswith(pattern):
                return True

        return False

    def _extract_version(self, func_name: str) -> str:
        """
        从函数名提取版本信息

        Args:
            func_name: 函数名

        Returns:
            版本标识字符串
        """
        # 周频
        if 'weekly' in func_name:
            return 'weekly'

        # 月频
        if 'monthly' in func_name:
            return 'monthly'

        # 保守版
        if 'conservative' in func_name:
            return 'conservative'

        # 激进版
        if 'aggressive' in func_name:
            return 'aggressive'

        # 进取版
        if 'progressive' in func_name:
            return 'progressive'

        # 稳健版
        if 'stable' in func_name or 'steadfast' in func_name:
            return 'stable'

        # 默认
        return 'default'

    def load_ashare_strategies_by_version(self, version: str) -> List[Tuple[str, str, str, str]]:
        """
        加载指定版本的A股策略

        Args:
            version: 策略版本标识 (如 'weekly', 'monthly', 'conservative')

        Returns:
            List of tuples: (display_name, module_name, func_name, version)
        """
        all_strategies = self.load_ashare_strategies()
        filtered = [s for s in all_strategies if s[3] == version]
        logger.info(f'加载 {version} 策略: 找到 {len(filtered)} 个')
        return filtered

    def get_strategy_versions(self) -> set:
        """
        获取所有可用的策略版本

        Returns:
            set: 版本标识集合 (如 {'weekly', 'monthly', 'conservative'})
        """
        strategies = self.load_ashare_strategies()
        versions = {s[3] for s in strategies}
        logger.debug(f'可用策略版本: {versions}')
        return versions

    def list_strategies(self):
        """列出所有发现的A股策略（用于调试）"""
        strategies = self.load_ashare_strategies()

        if not strategies:
            logger.info('未发现任何A股策略')
            return

        logger.info('=' * 60)
        logger.info(f'发现 {len(strategies)} 个A股策略:')
        logger.info('=' * 60)

        for display_name, module_name, func_name, version in strategies:
            logger.info(f'  {display_name}')
            logger.info(f'    模块: {module_name}')
            logger.info(f'    函数: {func_name}')
            logger.info(f'    版本: {version}')
            logger.info('')

        logger.info('=' * 60)


if __name__ == '__main__':
    """测试代码"""
    loader = StrategyLoader()
    loader.list_strategies()
