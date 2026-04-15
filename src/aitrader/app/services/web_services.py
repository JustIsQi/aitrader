from __future__ import annotations

from aitrader.infrastructure.repositories import (
    AnalyticsRepository,
    ShortTermRepository,
    SignalsRepository,
    TradingRepository,
)
from aitrader.shared.utils.serialization import clean_dataframe, dataframe_to_records, format_record_dates, safe_float, safe_value


class SignalsService:
    def __init__(self, repo: SignalsRepository | None = None):
        self.repo = repo or SignalsRepository()

    def latest(self, limit: int = 10):
        return dataframe_to_records(self.repo.latest(limit=limit), {'signal_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})

    def by_date(self, signal_date: str):
        return dataframe_to_records(self.repo.by_date(signal_date), {'signal_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})

    def by_symbol(self, symbol: str, start_date: str | None = None, end_date: str | None = None):
        records = dataframe_to_records(self.repo.by_symbol(symbol), {'signal_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})
        if start_date:
            records = [record for record in records if record.get('signal_date') >= start_date]
        if end_date:
            records = [record for record in records if record.get('signal_date') <= end_date]
        return records

    def grouped_history(self, start_date: str | None = None, end_date: str | None = None):
        signals_df = clean_dataframe(self.repo.grouped_history(start_date=start_date, end_date=end_date))
        if signals_df.empty:
            return {'ashare': {'weekly': {'dates': []}, 'monthly': {'dates': []}}}
        company_abbr_map = self.repo.company_names(signals_df['symbol'].unique().tolist())
        ashare_signals = []
        for record in signals_df.to_dict('records'):
            cleaned = format_record_dates(record, {'signal_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})
            cleaned['zh_company_abbr'] = company_abbr_map.get(record['symbol'], '')
            if cleaned.get('asset_type') == 'ashare':
                ashare_signals.append(cleaned)
        return {
            'ashare': {
                'weekly': {'dates': self._group_by_frequency(ashare_signals, '周频')},
                'monthly': {'dates': self._group_by_frequency(ashare_signals, '月频')},
            }
        }

    def latest_ashare(self, limit: int = 50):
        signals_df = clean_dataframe(self.repo.latest_ashare(limit=limit))
        if signals_df.empty:
            return {'weekly': {'date': None, 'signals': []}, 'monthly': {'date': None, 'signals': []}}
        company_abbr_map = self.repo.company_names(signals_df['symbol'].unique().tolist())
        weekly_signals = []
        monthly_signals = []
        for record in signals_df.to_dict('records'):
            cleaned = format_record_dates(record, {'signal_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})
            cleaned['zh_company_abbr'] = company_abbr_map.get(record['symbol'], '')
            cleaned['backtest'] = self.repo.signal_backtest(record['id'])
            strategies = cleaned.get('strategies', '') or ''
            if '月频' in strategies:
                monthly_signals.append(cleaned)
            else:
                weekly_signals.append(cleaned)
        latest_weekly_date = weekly_signals[0]['signal_date'] if weekly_signals else None
        latest_monthly_date = monthly_signals[0]['signal_date'] if monthly_signals else None
        return {
            'weekly': {'date': latest_weekly_date, 'signals': [item for item in weekly_signals if item['signal_date'] == latest_weekly_date]},
            'monthly': {'date': latest_monthly_date, 'signals': [item for item in monthly_signals if item['signal_date'] == latest_monthly_date]},
        }

    def backtest_detail(self, backtest_id: int):
        return self.repo.backtest_by_id(backtest_id)

    @staticmethod
    def _group_by_frequency(signals: list[dict], marker: str):
        filtered = []
        for signal in signals:
            strategies = signal.get('strategies', '') or ''
            if marker in strategies or (marker == '周频' and '月频' not in strategies):
                filtered.append(signal)
        grouped = {}
        for signal in filtered:
            grouped.setdefault(signal['signal_date'], []).append(signal)
        return [{'date': key, 'signals': value} for key, value in sorted(grouped.items(), key=lambda item: item[0], reverse=True)]


class TradingService:
    def __init__(self, repo: TradingRepository | None = None):
        self.repo = repo or TradingRepository()

    def add_record(self, record):
        self.repo.insert_transaction(
            symbol=record.symbol,
            buy_sell=record.buy_sell,
            quantity=record.quantity,
            price=record.price,
            trade_date=record.trade_date.strftime('%Y-%m-%d'),
            strategy_name=record.strategy_name,
        )
        positions = self.repo.get_positions()
        current_position = None
        if not positions.empty:
            position_rows = positions[positions['symbol'] == record.symbol]
            if not position_rows.empty:
                current_position = position_rows.iloc[0]
        if record.buy_sell == 'buy':
            if current_position is not None:
                total_quantity = float(current_position['quantity'] + record.quantity)
                total_cost = float(current_position['avg_cost']) * float(current_position['quantity']) + float(record.price) * float(record.quantity)
                self.repo.update_position(symbol=record.symbol, quantity=total_quantity, avg_cost=float(total_cost / total_quantity), current_price=float(record.price))
            else:
                self.repo.update_position(symbol=record.symbol, quantity=float(record.quantity), avg_cost=float(record.price), current_price=float(record.price))
        elif current_position is not None:
            new_quantity = float(current_position['quantity'] - record.quantity)
            self.repo.update_position(symbol=record.symbol, quantity=max(new_quantity, 0.0), avg_cost=float(current_position['avg_cost']), current_price=float(record.price))
        return {'status': 'success', 'message': f'交易记录已添加: {record.buy_sell} {record.quantity}股 {record.symbol} @ {record.price}'}

    def transactions(self, symbol=None, start_date=None, end_date=None, limit: int = 100):
        return dataframe_to_records(self.repo.get_transactions(symbol, start_date, end_date).head(limit), {'trade_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})

    def positions(self):
        return dataframe_to_records(self.repo.get_positions(), {'updated_at': '%Y-%m-%d %H:%M:%S'})

    def strategies(self):
        strategy_dir = self.repo.strategy_dir()
        if not strategy_dir.exists():
            return []
        return sorted([path.stem for path in strategy_dir.glob('*.py') if '__pycache__' not in str(path) and not path.name.startswith('.')])

    def recalculate_positions(self):
        result = self.repo.recalculate_positions()
        return {
            'status': 'success',
            'message': f'重新计算完成: 更新 {result["updated_count"]} 个持仓, 删除 {result["deleted_count"]} 个',
            'updated_count': result['updated_count'],
            'deleted_count': result['deleted_count'],
            'details': result['details'],
        }

    def codes(self, search=None, limit: int = 100):
        return self.repo.search_codes(search=search, limit=limit)


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository | None = None):
        self.repo = repo or AnalyticsRepository()

    def profit_loss(self):
        data = self.repo.profit_loss()
        total_pl = data['realized_pl'] + data['total_unrealized_pl']
        return {
            'realized_pl': safe_float(data['realized_pl']),
            'total_unrealized_pl': safe_float(data['total_unrealized_pl']),
            'total_market_value': safe_float(data['total_market_value']),
            'total_cost': safe_float(data['total_cost']),
            'total_pl': safe_float(total_pl),
        }

    def performance(self):
        positions = clean_dataframe(self.repo.positions())
        if positions.empty:
            return {'total_positions': 0, 'total_market_value': 0, 'total_cost': 0, 'best_performer': None, 'worst_performer': None, 'avg_return_pct': 0}
        positions['return_pct'] = ((positions['current_price'] - positions['avg_cost']) / positions['avg_cost'] * 100)
        positions['return_amount'] = ((positions['current_price'] - positions['avg_cost']) * positions['quantity'])
        best_idx = positions['return_pct'].idxmax()
        worst_idx = positions['return_pct'].idxmin()
        total_cost = (positions['avg_cost'] * positions['quantity']).sum()
        total_return = positions['return_amount'].sum()
        return {
            'total_positions': len(positions),
            'total_market_value': safe_float(positions['market_value'].sum()),
            'total_cost': safe_float(total_cost),
            'total_return': safe_float(total_return),
            'total_return_pct': safe_float(total_return / total_cost * 100 if total_cost > 0 else 0),
            'best_performer': {'symbol': positions.loc[best_idx, 'symbol'], 'return_pct': safe_float(positions.loc[best_idx, 'return_pct'])},
            'worst_performer': {'symbol': positions.loc[worst_idx, 'symbol'], 'return_pct': safe_float(positions.loc[worst_idx, 'return_pct'])},
            'avg_return_pct': safe_float(positions['return_pct'].mean()),
        }

    def historical_pl(self):
        symbols_data = self.repo.historical_pl_by_symbol()
        sold = [item for item in symbols_data if item['current_qty'] == 0]
        holding = [item for item in symbols_data if item['current_qty'] > 0]
        sold_realized = sum(item['realized_pl'] for item in sold)
        holding_realized = sum(item['realized_pl'] for item in holding)
        holding_unrealized = sum(item['unrealized_pl'] for item in holding)
        total_realized = sum(item['realized_pl'] for item in symbols_data)
        total_unrealized = sum(item['unrealized_pl'] for item in symbols_data)
        return {
            'sold': {'symbols': sold, 'summary': {'count': len(sold), 'realized_pl': safe_float(sold_realized), 'unrealized_pl': 0.0, 'total_pl': safe_float(sold_realized)}},
            'holding': {'symbols': holding, 'summary': {'count': len(holding), 'realized_pl': safe_float(holding_realized), 'unrealized_pl': safe_float(holding_unrealized), 'total_pl': safe_float(holding_realized + holding_unrealized)}},
            'total': {'total_symbols': len(symbols_data), 'realized_pl': safe_float(total_realized), 'unrealized_pl': safe_float(total_unrealized), 'total_pl': safe_float(total_realized + total_unrealized)},
        }


class ShortTermService:
    def __init__(self, repo: ShortTermRepository | None = None):
        self.repo = repo or ShortTermRepository()

    def latest_daily_operation_list(self, limit: int = 50):
        return [self._format_operation(item) for item in self.repo.latest_daily_operations(limit=limit)]

    def daily_operation_list_by_date(self, date: str):
        return [self._format_operation(item) for item in self.repo.daily_operations_by_date(date)]

    def latest_sectors(self, limit: int = 10):
        return [self._format_sector(item) for item in self.repo.latest_sectors(limit=limit)]

    def sectors_by_date(self, date: str):
        return [self._format_sector(item) for item in self.repo.sectors_by_date(date)]

    def latest_backtests(self, limit: int = 10):
        return [self._format_backtest(item) for item in self.repo.latest_backtests(limit=limit)]

    def backtest_by_id(self, backtest_id: int):
        result = self.repo.backtest_by_id(backtest_id)
        return self._format_backtest(result) if result else None

    def summary(self):
        result = self.repo.summary()
        if result['latest_operation_date']:
            result['latest_operation_date'] = result['latest_operation_date'].strftime('%Y-%m-%d')
        if result['latest_sector_date']:
            result['latest_sector_date'] = result['latest_sector_date'].strftime('%Y-%m-%d')
        return result

    @staticmethod
    def _format_operation(item: dict):
        if item.get('date'):
            item['date'] = item['date'].strftime('%Y-%m-%d')
        if item.get('executed_time'):
            item['executed_time'] = item['executed_time'].strftime('%Y-%m-%d %H:%M:%S')
        if item.get('position_ratio') is not None:
            item['position_ratio'] = round(item['position_ratio'] * 100, 2)
        return {key: safe_value(value) for key, value in item.items()}

    @staticmethod
    def _format_sector(item: dict):
        if item.get('date'):
            item['date'] = item['date'].strftime('%Y-%m-%d')
        return {key: safe_value(value) for key, value in item.items()}

    @staticmethod
    def _format_backtest(item: dict | None):
        if not item:
            return None
        for field in ('start_date', 'end_date'):
            if item.get(field):
                item[field] = item[field].strftime('%Y-%m-%d')
        if item.get('created_at'):
            item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return {key: safe_value(value) for key, value in item.items()}


class DashboardService:
    def __init__(self):
        self.trading = TradingService()
        self.signals = SignalsService()
        self.short_term = ShortTermService()
        self.signals_repo = SignalsRepository()
        self.trading_repo = TradingRepository()

    def dashboard_context(self):
        positions_df = self.trading_repo.get_positions()
        positions_dict = {}
        if not positions_df.empty:
            for record in positions_df.to_dict('records'):
                symbol = record['symbol']
                quantity = record['quantity']
                avg_cost = record['avg_cost']
                current_price = record.get('current_price', avg_cost)
                position_data = {
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'current_price': current_price,
                    'market_value': record.get('market_value'),
                    'unrealized_pl': (current_price - avg_cost) * quantity,
                    'unrealized_pl_pct': ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0,
                    'updated_at': record.get('updated_at'),
                }
                positions_dict[symbol] = position_data
                positions_dict[f'{symbol}.SH'] = position_data
                positions_dict[f'{symbol}.SZ'] = position_data
        ashare_result = self.signals.latest_ashare(limit=50)
        short_term_signals = self.short_term.latest_daily_operation_list(limit=50)
        short_term_date = short_term_signals[0].get('date') if short_term_signals else None
        for bucket in ('weekly', 'monthly'):
            for signal in ashare_result.get(bucket, {}).get('signals', []):
                symbol = signal.get('symbol')
                if symbol in positions_dict:
                    signal['position'] = positions_dict[symbol]
        for signal in short_term_signals:
            symbol = signal.get('stock_code')
            if symbol in positions_dict:
                signal['position'] = positions_dict[symbol]
        positions = dataframe_to_records(positions_df, {'updated_at': '%Y-%m-%d %H:%M:%S'})
        if positions:
            company_names = self.signals_repo.company_names([record['symbol'] for record in positions])
            for record in positions:
                record['stock_name'] = company_names.get(record['symbol'], '')
        transactions = dataframe_to_records(self.trading_repo.get_transactions().head(20), {'trade_date': '%Y-%m-%d', 'created_at': '%Y-%m-%d %H:%M:%S'})
        return {
            'ashare_weekly_date': ashare_result.get('weekly', {}).get('date'),
            'ashare_weekly_signals': ashare_result.get('weekly', {}).get('signals', []),
            'ashare_monthly_date': ashare_result.get('monthly', {}).get('date'),
            'ashare_monthly_signals': ashare_result.get('monthly', {}).get('signals', []),
            'short_term_date': short_term_date,
            'short_term_signals': short_term_signals,
            'positions': positions,
            'transactions': transactions,
        }

    def signal_page_context(self):
        latest_signals = self.signals.latest(limit=50)
        return {'latest_signals': latest_signals, 'positions': [], 'transactions': []}
