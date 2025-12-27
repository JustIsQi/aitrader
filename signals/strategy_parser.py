"""
策略文件解析器
用于解析 strategy/ 目录下的策略文件,提取 Task 配置
"""
import ast
import importlib.util
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
from enum import Enum
import sys


class StrategyType(Enum):
    """策略类型枚举"""
    BT = "bt"
    BACKTRADER = "backtrader"
    CUSTOM = "custom"


@dataclass
class ParsedStrategy:
    """解析后的策略配置"""
    filename: str
    filepath: str
    strategy_type: StrategyType
    task: Optional['Task']  # 延迟导入
    is_valid: bool = True
    parse_error: Optional[str] = None
    function_name: Optional[str] = None


class StrategyParser:
    """策略解析器"""

    def __init__(self, strategy_dir: str = "strategy"):
        """
        初始化策略解析器

        Args:
            strategy_dir: 策略目录路径
        """
        self.strategy_dir = Path(strategy_dir)
        if not self.strategy_dir.exists():
            raise FileNotFoundError(f"策略目录不存在: {strategy_dir}")

    def parse_all_strategies(self) -> List[ParsedStrategy]:
        """
        解析策略目录下所有 .py 文件

        Returns:
            解析后的策略列表
        """
        strategies = []

        for py_file in self.strategy_dir.glob("*.py"):
            # 跳过缓存文件和隐藏文件
            if "__pycache__" in str(py_file) or py_file.name.startswith("."):
                continue

            parsed = self.parse_strategy_file(py_file)
            if parsed and parsed.is_valid:
                strategies.append(parsed)
            elif parsed:
                # 解析失败但仍然记录
                print(f"⚠️  跳过策略 {parsed.filename}: {parsed.parse_error}")

        return strategies

    def parse_strategy_file(self, filepath: Path) -> Optional[ParsedStrategy]:
        """
        解析单个策略文件

        Args:
            filepath: 策略文件路径

        Returns:
            解析后的策略对象
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            # 使用 AST 解析
            tree = ast.parse(source)

            # 检测策略类型
            strategy_type = self._detect_strategy_type(tree)

            # 提取 Task 配置
            task, function_name = self._extract_task_config(tree, source, strategy_type, filepath)

            if task is None:
                return ParsedStrategy(
                    filename=filepath.stem,
                    filepath=str(filepath),
                    strategy_type=strategy_type,
                    task=None,
                    is_valid=False,
                    parse_error="无法提取 Task 配置"
                )

            return ParsedStrategy(
                filename=filepath.stem,
                filepath=str(filepath),
                strategy_type=strategy_type,
                task=task,
                is_valid=True,
                function_name=function_name
            )

        except SyntaxError as e:
            return ParsedStrategy(
                filename=filepath.stem,
                filepath=str(filepath),
                strategy_type=StrategyType.CUSTOM,
                task=None,
                is_valid=False,
                parse_error=f"语法错误: {e}"
            )
        except Exception as e:
            return ParsedStrategy(
                filename=filepath.stem,
                filepath=str(filepath),
                strategy_type=StrategyType.CUSTOM,
                task=None,
                is_valid=False,
                parse_error=str(e)
            )

    def _detect_strategy_type(self, tree: ast.AST) -> StrategyType:
        """
        检测策略类型 (bt 或 backtrader)

        Args:
            tree: AST 树

        Returns:
            策略类型
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'bt_engine' in alias.name:
                        return StrategyType.BT
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if 'bt_engine' in node.module:
                        return StrategyType.BT
                    elif 'backtrader_engine' in node.module:
                        return StrategyType.BACKTRADER

        return StrategyType.CUSTOM

    def _extract_task_config(self, tree: ast.AST, source: str,
                            strategy_type: StrategyType,
                            filepath: Path) -> Tuple[Optional['Task'], Optional[str]]:
        """
        提取 Task 配置

        Args:
            tree: AST 树
            source: 源代码
            strategy_type: 策略类型
            filepath: 文件路径

        Returns:
            (Task对象, 函数名) 元组
        """
        # 动态导入 Task 类（从 core 模块）
        if strategy_type == StrategyType.BT:
            from core.bt_engine import Task
        elif strategy_type == StrategyType.BACKTRADER:
            from core.backtrader_engine import Task
        else:
            return None, None

        # 查找 Task 实例化
        for node in ast.walk(tree):
            # 模式1: 直接实例化 t = Task()
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Task':
                        # 提取属性赋值
                        task = self._extract_from_task_instantiation(tree, Task)
                        if task:
                            return task, None

                    # 模式2: 函数返回 Task
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id
                        # 检查是否有对应的函数定义
                        for func_node in ast.walk(tree):
                            if isinstance(func_node, ast.FunctionDef) and func_node.name == func_name:
                                task = self._extract_from_function(func_node, Task)
                                if task:
                                    return task, func_name

        # 如果静态解析失败,尝试动态执行
        return self._extract_by_dynamic_execution(source, filepath, Task)

    def _extract_from_task_instantiation(self, tree: ast.AST, TaskClass) -> Optional['Task']:
        """
        从 Task 实例化中提取配置

        Args:
            tree: AST 树
            TaskClass: Task 类

        Returns:
            Task 对象
        """
        task = TaskClass()

        # 查找所有属性赋值
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        if target.value.id == 't' and hasattr(task, target.attr):
                            try:
                                value = ast.literal_eval(node.value)
                                setattr(task, target.attr, value)
                            except (ValueError, SyntaxError):
                                # 无法直接求值的表达式,尝试字符串
                                if isinstance(node.value, ast.Constant):
                                    setattr(task, target.attr, node.value.value)

        # 检查是否有 symbols 列表
        if not task.symbols:
            return None

        return task

    def _extract_from_function(self, func_node: ast.FunctionDef, TaskClass) -> Optional['Task']:
        """
        从函数中提取 Task 配置

        Args:
            func_node: 函数 AST 节点
            TaskClass: Task 类

        Returns:
            Task 对象
        """
        task = TaskClass()

        # 遍历函数体,查找 Task 实例化和属性赋值
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                # Task 属性赋值: t.name = 'xxx'
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                            if target.value.id == 't' and hasattr(task, target.attr):
                                try:
                                    value = ast.literal_eval(node.value)
                                    setattr(task, target.attr, value)
                                except (ValueError, SyntaxError):
                                    if isinstance(node.value, ast.Constant):
                                        setattr(task, target.attr, node.value.value)

        # 检查是否有 symbols 列表
        if not task.symbols:
            return None

        return task

    def _extract_by_dynamic_execution(self, source: str, filepath: Path, TaskClass) -> Tuple[Optional['Task'], Optional[str]]:
        """
        通过动态执行提取 Task 配置

        Args:
            source: 源代码
            filepath: 文件路径
            TaskClass: Task 类

        Returns:
            (Task对象, 函数名) 元组
        """
        try:
            # 创建安全的执行环境
            # 注意：需要保留 __import__ 以支持 from core.xxx import
            # __builtins__ 可能是 dict 或 module，需要兼容处理
            import builtins
            safe_builtins = {
                '__import__': builtins.__import__,
                'len': builtins.len,
                'range': builtins.range,
            }
            safe_globals = {
                '__builtins__': safe_builtins,
                'Task': TaskClass,
                'list': list,
                'dict': dict,
                '__name__': '__not_main__',  # 防止 if __name__ == '__main__' 执行
            }

            # 执行代码
            exec(source, safe_globals)

            # 查找 Task 实例或返回 Task 的函数
            task = None
            func_name = None

            for name, value in safe_globals.items():
                # 跳过 Task 类本身和内置类型
                if isinstance(value, type) and value.__name__ == 'Task':
                    continue
                if name in ['Task', 'list', 'dict']:
                    continue

                # 检查是否是 Task 实例
                if hasattr(value, 'symbols') and hasattr(value, 'name'):
                    task = value
                    break

                # 查找返回 Task 的函数
                elif callable(value):
                    try:
                        result = value()
                        if hasattr(result, 'symbols') and hasattr(result, 'name'):
                            task = result
                            func_name = name
                            break
                    except:
                        continue

            return task, func_name

        except Exception as e:
            return None, None


if __name__ == '__main__':
    # 测试策略解析器
    parser = StrategyParser('strategies')
    strategies = parser.parse_all_strategies()

    print(f"成功解析 {len(strategies)} 个策略:")
    for s in strategies:
        print(f"  - {s.filename} ({s.strategy_type.value})")
        if s.task:
            print(f"    标的数: {len(s.task.symbols)}")
            print(f"    买入条件: {len(s.task.select_buy)}")
            print(f"    卖出条件: {len(s.task.select_sell)}")
