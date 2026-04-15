import pandas as pd
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


class MySQLAshareReaderTest(unittest.TestCase):
    def test_price_query_joins_derivative_indicator_table(self):
        query_text, params = MySQLAshareReader().build_price_query(
            symbols=["000001.SZ"],
            start_date="20260410",
            end_date="20260414",
        )

        self.assertIn("ASHAREEODPRICES", query_text)
        self.assertIn("ASHAREEODDERIVATIVEINDICATOR", query_text)
        self.assertIn("d.S_DQ_TURN AS turnover_rate", query_text)
        self.assertIn("d.S_VAL_PE AS pe", query_text)
        self.assertIn("d.S_VAL_PB_NEW AS pb", query_text)
        self.assertEqual(params, ["000001.SZ", "20260410", "20260414"])

    def test_normalize_prices_keeps_derivative_indicator_columns(self):
        reader = MySQLAshareReader()
        raw = pd.DataFrame(
            {
                "trade_date": ["20260410"],
                "stock_code": ["000001.SZ"],
                "real_open": [10.0],
                "real_close": [10.5],
                "real_low": [9.9],
                "open": [10.1],
                "close": [10.6],
                "high": [10.8],
                "low": [10.0],
                "vwap": [10.4],
                "volume": [100000],
                "amount": [105000.0],
                "change_pct": [1.2],
                "turnover_rate": [2.3],
                "free_turnover_rate": [3.4],
                "pe": [12.5],
                "pe_ttm": [11.9],
                "pb": [1.4],
                "ps": [2.1],
                "ps_ttm": [2.0],
                "total_mv": [12000000.0],
                "circ_mv": [9000000.0],
                "total_shares": [1000000.0],
                "float_shares": [800000.0],
                "free_shares": [700000.0],
                "up_down_limit_status": [0],
            }
        )

        normalized = reader.normalize_prices(raw)

        self.assertEqual(normalized.loc[0, "date"], "20260410")
        self.assertEqual(normalized.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(normalized.loc[0, "turnover_rate"], 2.3)
        self.assertEqual(normalized.loc[0, "pe"], 12.5)
        self.assertEqual(normalized.loc[0, "pb"], 1.4)
        self.assertEqual(normalized.loc[0, "total_mv"], 12000000.0)


    def test_latest_derivative_query_and_normalization(self):
        reader = MySQLAshareReader()
        query_text, params = reader.build_latest_derivative_query(
            symbols=["000001.SZ"],
            end_date="20260414",
        )

        self.assertIn("ASHAREEODDERIVATIVEINDICATOR", query_text)
        self.assertIn("MAX(TRADE_DT)", query_text)
        self.assertIn("S_INFO_WINDCODE IN", query_text)
        self.assertEqual(params, ["20260414", "000001.SZ"])

        raw = pd.DataFrame(
            {
                "trade_date": ["20260410"],
                "stock_code": ["000001.SZ"],
                "pe_ratio": [12.5],
                "pe_ttm": [11.9],
                "pb_ratio": [1.4],
                "ps_ratio": [2.1],
                "ps_ttm": [2.0],
                "total_mv": [12000000.0],
                "circ_mv": [9000000.0],
                "turnover_rate": [2.3],
                "free_turnover_rate": [3.4],
            }
        )

        normalized = reader.normalize_derivative_indicators(raw)

        self.assertEqual(normalized.loc[0, "date"], "2026-04-10")
        self.assertEqual(normalized.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(normalized.loc[0, "pe_ratio"], 12.5)
        self.assertEqual(normalized.loc[0, "pb_ratio"], 1.4)
        self.assertEqual(normalized.loc[0, "turnover_rate"], 2.3)


if __name__ == "__main__":
    unittest.main()
