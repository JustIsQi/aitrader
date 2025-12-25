from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# 操作符映射字典，将中文操作符转换为对应的符号
OP_MAP = {
    '大于': '>',
    '小于': '<',
    '大于等于': '>=',
    '小于等于': '<=',
    '等于': '==',
    '不等于': '!=',
    '包含': 'in',
    '不包含': 'not in'
}

from collections import OrderedDict
# 因子表达式映射，包含表达式模板和参数描述
FACTOR_EXPRS = {
    '动量': {
        'expr': 'roc(close,{})',
        'params': OrderedDict([(20,'周期'),]),
        'category':'量价及技术因子'
    },
    '流通市值': {
        'expr': 'circ_mv',
        'params': {},
        'is_base':True,
        'category':'量价及技术因子'
    },
    # 可以添加更多因子表达式
    '收盘价': {
        'expr': 'real_close',
        'params': {},
        'is_base':True,
        'category':'量价及技术因子'
    },
    '净资产收益率': {
        'expr': 'roe',
        'params': {},
        'is_base':True,
    'category':'基本面因子'
    },
    'pe-ttm': {
        'expr': 'pe-ttm',

        'params': {},
        'is_base':True,
    'category':'基本面因子'
    },
    # 更多因子...
}

def get_factors():
    from collections import defaultdict
    factors = defaultdict(list)
    for factor, params in FACTOR_EXPRS.items():
        params['name'] = factor

        show_name = factor
        if len(params['params']):
            keys =  [str(k) for k in list(params['params'].keys())]
            p = ','.join(keys)
            show_name = f'{factor}({p})'
        params['show_name'] = show_name
        params['op'] = '>'
        params['value'] = 0
        params['params'] = dict(params['params'])
        factors[params['category']].append(params)
    print(factors)
    return factors


@dataclass
class Rule:
    factor_name: str = ''
    params: List[int] = field(default_factory=lambda: [20])
    op: str = '大于'
    value: float = 0.0

@dataclass
class SortRule:
    factor_name: str = ''
    params: List[int] = field(default_factory=lambda: [20])
    desc: bool = True
    weight: float = 1.0  # 修正了拼写错误

from datetime import datetime
@dataclass
class StockTask:
    name: str = '股票策略'

    period: str = 'RunDaily'
    period_days: Optional[int] = None

    start_date: str = '20100101'
    end_date: Optional[str] = datetime.now().strftime('%Y%m%d')

    benchmark: str = '510300.SH'


    filters_rules: List[Rule] = field(default_factory=list)  # 明确指定为Rule列表
    orderby_rules: Optional[List[SortRule]] = field(default_factory=list)  # 明确指定为SortRule列表
    topK: int = 20

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockTask':
        """
        从字典创建 StockTask 实例

        Args:
            data: 包含 StockTask 数据的字典

        Returns:
            StockTask 实例
        """
        # 处理 filters_rules
        filters_rules = []
        if 'filters_rules' in data and data['filters_rules']:
            for rule_data in data['filters_rules']:
                if isinstance(rule_data, Rule):
                    filters_rules.append(rule_data)
                else:
                    filters_rules.append(Rule(**rule_data))

        # 处理 orderby_rules
        orderby_rules = []
        if 'orderby_rules' in data and data['orderby_rules']:
            for rule_data in data['orderby_rules']:
                if isinstance(rule_data, SortRule):
                    orderby_rules.append(rule_data)
                else:
                    orderby_rules.append(SortRule(**rule_data))

        # 创建 StockTask 实例
        return cls(
            name=data.get('name', '股票策略'),
            period=data.get('period', 'RunDaily'),
            period_days=data.get('period_days'),
            start_date=data.get('start_date', '20100101'),
            end_date=data.get('end_date', datetime.now().strftime('%Y%m%d')),
            benchmark=data.get('benchmark', '000300.SH'),
            filters_rules=filters_rules,
            orderby_rules=orderby_rules,
            topK=data.get('topK', 20)
        )


    def get_filter_rules(self):
        """
        根据filters生成过滤条件表达式列表
        例如：['roc(close,20) > 0.08', 'ts_min(close,20) < 10.5']
        """
        if not self.filters_rules:
            return []

        filter_expressions = []
        base_expressions = []

        for rule in self.filters_rules:
            # 获取因子表达式信息
            factor_info = FACTOR_EXPRS.get(rule.factor_name)
            if not factor_info:
                continue

            # 使用参数展开替换表达式中的占位符
            expr_template = factor_info['expr']
            try:
                # 使用*params展开参数列表
                if len(rule.params) == 0:
                    expr = expr_template
                else:
                    expr = expr_template.format(*rule.params)
            except (IndexError, ValueError):
                # 如果参数数量不匹配，跳过这个规则
                print('参数不匹配，跳过')
                continue

            # 获取对应的操作符
            op_symbol = OP_MAP.get(rule.op, rule.op)

            # 构建过滤表达式
            if isinstance(rule.value, str) and (rule.op == '包含' or rule.op == '不包含'):
                # 处理字符串值的包含/不包含操作
                filter_expr = f"{expr}{op_symbol}({rule.value})"
            else:
                # 处理数值比较操作
                filter_expr = f"{expr}{op_symbol}{rule.value}"

            is_base = factor_info.get('is_base', False)
            if is_base:
                base_expressions.append(filter_expr)
            filter_expressions.append(filter_expr)

        return filter_expressions,base_expressions

    def get_order_by_factor(self) -> str:
        """
        根据orderby_rules生成排序因子表达式
        规则：按weight加权，如果desc=True，则权重乘以-1
        例如：roc(close,20)*0.8 + ts_min(close,20)*0.6
        """
        if not self.orderby_rules:
            return ""

        expressions = []

        for rule in self.orderby_rules:
            # 获取因子表达式信息
            factor_info = FACTOR_EXPRS.get(rule.factor_name)
            if not factor_info:
                continue

            # 使用参数展开替换表达式中的占位符
            expr_template = factor_info['expr']
            try:
                # 使用*params展开参数列表
                expr = expr_template.format(*rule.params)
            except (IndexError, ValueError):
                # 如果参数数量不匹配，跳过这个规则
                continue

            # 应用权重（如果desc为True，则权重取负）
            weight = rule.weight * (1 if rule.desc else -1)
            weighted_expr = f"({expr}) * {weight}"
            expressions.append(weighted_expr)

        # 组合所有表达式
        return " + ".join(expressions) if expressions else ""

    def get_orderby_rule_name(self):
        return '排序因子'

    def get_filter_rules_names(self) -> List[str]:
        """
        根据filters生成过滤规则名称列表
        格式：['因子名_参数1_参数2', ...]
        例如：['动量_20', '最小值_22_23']
        """
        if not self.filters_rules:
            return []

        rule_names = []

        for rule in self.filters_rules:
            # 构建基础名称（因子名）
            name_parts = [rule.factor_name]

            # 添加参数部分
            if rule.params:
                # 将参数转换为字符串并用下划线连接
                param_str = "_".join(str(p) for p in rule.params)
                name_parts.append(param_str)

            # 组合成完整的规则名称
            rule_name = "_".join(name_parts)
            rule_names.append(rule_name)

        return rule_names




if __name__ == '__main__':
    task = StockTask()
    task.filters_rules.append(Rule(
        factor_name='动量',
        params=[5,],
        op='大于',
        value=0.08
    ))

    task.filters_rules.append(Rule(
        factor_name='最大值',
        params=[21,],
        op='小于等于',
        value=0
    ))


    task.orderby_rules.append(SortRule(
        factor_name='动量',
        params=[21,],
        weight=1.0
    ))
    task.orderby_rules.append(SortRule(
        factor_name='最小值',
        params=[3, ],
        weight=0.6,
        desc=False
    ))


    print(task.get_order_by_factor())
    print(task.get_filter_rules())
    print(task.get_filter_rules_names())
