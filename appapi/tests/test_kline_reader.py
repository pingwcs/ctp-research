"""Tests for K-line parquet reader query planning."""

from pathlib import Path

from appapi.services.kline_reader import KLineReader


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0]

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, total, rows):
        self.total = total
        self.rows = rows
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(sql.split())
        self.statements.append((normalized_sql, params))
        if normalized_sql.startswith("DESCRIBE SELECT"):
            return FakeResult(
                [
                    ("eob",),
                    ("open",),
                    ("high",),
                    ("low",),
                    ("close",),
                    ("volume",),
                ],
            )
        if normalized_sql.startswith("SELECT COUNT"):
            return FakeResult([(self.total,)])
        return FakeResult(self.rows)

    @property
    def select_sql(self):
        return next(
            sql for sql, _params in self.statements if sql.startswith("SELECT epoch")
        )


def _reader_for(connection):
    return KLineReader(
        connection_factory=lambda: connection,
        contract_resolver=lambda symbol: Path(f"C:/data/{symbol}.parquet"),
    )


def test_kline_reader_uses_latest_window_when_offset_is_missing():
    connection = FakeConnection(
        total=5,
        rows=[(1253026200, 1, 2, 0.5, 1.5, 10)],
    )

    response = _reader_for(connection).load("RB0909", limit=2)

    assert response.symbol == "RB0909"
    assert response.total == 5
    assert response.offset == 3
    assert response.limit == 2
    assert [candle.model_dump() for candle in response.candles] == [
        {
            "time": 1253026200,
            "open": 1.0,
            "high": 2.0,
            "low": 0.5,
            "close": 1.5,
            "volume": 10.0,
        },
    ]
    assert "LIMIT 2 OFFSET 3" in connection.select_sql


def test_kline_reader_clamps_limit_and_explicit_offset():
    connection = FakeConnection(total=3, rows=[])

    response = _reader_for(connection).load("RB0909", offset=10, limit=5000)

    assert response.offset == 2
    assert response.limit == 2000
    assert "LIMIT 2000 OFFSET 2" in connection.select_sql
