import backtrader as bt
import numpy as np


class TrendScore(bt.Indicator):
    lines = ('trend_score',)
    params = (('period', 25),)

    def __init__(self):
        super().__init__()
        print(f"TrendScore 初始化 - 周期: {self.p.period}")

        self.addminperiod(self.p.period)

    def next(self):
        if len(self.data) < self.p.period:
            self.lines.trend_score[0] = np.nan
            return

        # 获取窗口数据
        window_data = self.data.get(size=self.p.period)

        # 检查数据有效性
        if np.any(np.isnan(window_data)) or np.any(np.isinf(window_data)):
            self.lines.trend_score[0] = np.nan
            return

        try:
            # 对数转换
            y_raw = np.array(window_data)
            y = np.log(y_raw)
            x = np.arange(len(y))
            n = len(x)

            if n < 2:
                self.lines.trend_score[0] = 0.0
                return

            # 计算回归统计量
            sum_x = x.sum()
            sum_y = y.sum()
            sum_x2 = (x ** 2).sum()
            sum_xy = (x * y).sum()
            denominator = n * sum_x2 - sum_x ** 2

            # 处理零分母
            if abs(denominator) <= 1e-9:
                self.lines.trend_score[0] = 0.0
                return

            # 计算斜率和截距
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n

            # 计算R平方
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum(y ** 2) - (sum_y ** 2) / n

            if abs(ss_tot) <= 1e-9:
                r_squared = 0.0
            else:
                r_squared = 1 - ss_res / ss_tot
                r_squared = max(0.0, min(r_squared, 1.0))  # 限制在[0,1]范围

            # 计算年化收益率
            annualized_return = np.exp(slope * 250) - 1

            # 综合评分
            trend_score = annualized_return * r_squared

            # 处理异常值
            if np.isinf(trend_score) or np.isnan(trend_score):
                self.lines.trend_score[0] = 0.0
            else:
                self.lines.trend_score[0] = trend_score

        except (ValueError, ZeroDivisionError):
            self.lines.trend_score[0] = 0.0