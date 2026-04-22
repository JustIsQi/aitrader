import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aitrader.domain.market.stock_universe import StockUniverse
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReaderConfigError


class FakeCursor:
    def __init__(self):
        self.calls = []
        self._rows = []

    def execute(self, query, params=None):
        self.calls.append((query, params))
        if "ASHAREEODPRICES" in query:
            self._rows = [
                {"S_INFO_WINDCODE": "600000.SH"},
                {"S_INFO_WINDCODE": "300001.SZ"},
            ]
        else:
            self._rows = []

    def fetchall(self):
        return list(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


class FakeReader:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


class StockUniverseTest(unittest.TestCase):
    def test_get_all_stocks_uses_as_of_date(self):
        connection = FakeConnection()
        fake_reader = FakeReader(connection)
        as_of_date = "2024-12-31"
        expected_cutoff = (pd.Timestamp(as_of_date) - pd.Timedelta(days=500)).strftime("%Y%m%d")
        expected_recent = (pd.Timestamp(as_of_date) - pd.Timedelta(days=30)).strftime("%Y%m%d")

        with patch(
            "aitrader.infrastructure.market_data.mysql_reader.MySQLAshareReader",
            return_value=fake_reader,
        ):
            stocks = StockUniverse(db=object()).get_all_stocks(
                exclude_st=True,
                exclude_suspend=True,
                exclude_new_ipo_days=180,
                min_data_days=500,
                exclude_restricted_stocks=True,
                as_of_date=as_of_date,
            )

        self.assertEqual(stocks, ["600000.SH"])
        self.assertEqual(connection.cursor_obj.calls[0][1], [expected_cutoff, expected_recent])
        self.assertEqual(connection.cursor_obj.calls[1][1], [as_of_date.replace("-", ""), as_of_date.replace("-", "")])
        self.assertTrue(connection.closed)

    def test_get_all_stocks_propagates_reader_config_errors(self):
        with patch(
            "aitrader.infrastructure.market_data.mysql_reader.MySQLAshareReader",
            side_effect=MySQLAshareReaderConfigError("missing mysql config"),
        ):
            with self.assertRaises(MySQLAshareReaderConfigError):
                StockUniverse(db=object()).get_all_stocks(
                    exclude_st=True,
                    exclude_suspend=True,
                    exclude_new_ipo_days=180,
                    min_data_days=500,
                    exclude_restricted_stocks=True,
                    as_of_date="2024-12-31",
                )


if __name__ == "__main__":
    unittest.main()
