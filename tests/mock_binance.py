"""Mock Binance client for testing.

Provides a fake BinanceClient that returns deterministic data
without making real API calls.
"""

import time


class MockBinanceClient:
    """Mock replacement for BinanceClient used in tests."""

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.leverage_set = {}
        self.margin_types = {}
        self.orders = []
        self.positions = []

    def get_funding_rates(self) -> list[dict]:
        """Return fake funding rate data."""
        now_ms = int(time.time() * 1000)
        next_funding = now_ms + 60_000  # 1 minute from now

        return [
            {
                "symbol": "BTC/USDT:USDT",
                "funding_rate": -1.5,
                "mark_price": 50000.0,
                "next_funding_time": next_funding,
            },
            {
                "symbol": "ETH/USDT:USDT",
                "funding_rate": -2.0,
                "mark_price": 3000.0,
                "next_funding_time": next_funding,
            },
            {
                "symbol": "SOL/USDT:USDT",
                "funding_rate": -0.5,
                "mark_price": 100.0,
                "next_funding_time": next_funding,
            },
            {
                "symbol": "DOGE/USDT:USDT",
                "funding_rate": -1.2,
                "mark_price": 0.15,
                "next_funding_time": next_funding,
            },
            {
                "symbol": "ADA/USDT:USDT",
                "funding_rate": 0.01,
                "mark_price": 0.5,
                "next_funding_time": next_funding,
            },
        ]

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        self.leverage_set[symbol] = leverage
        return True

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> bool:
        self.margin_types[symbol] = margin_type
        return True

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        order = {
            "id": f"mock-{len(self.orders) + 1}",
            "symbol": symbol,
            "side": side,
            "amount": quantity,
            "average": self._get_mock_price(symbol),
            "status": "closed",
        }
        self.orders.append(order)
        return order

    def get_open_positions(self, symbol: str = None) -> list[dict]:
        return self.positions

    def get_account_balance(self) -> float:
        return 30.0

    def get_mark_price(self, symbol: str) -> float:
        return self._get_mock_price(symbol)

    def _get_mock_price(self, symbol: str) -> float:
        prices = {
            "BTC/USDT:USDT": 50000.0,
            "ETH/USDT:USDT": 3000.0,
            "SOL/USDT:USDT": 100.0,
            "DOGE/USDT:USDT": 0.15,
            "ADA/USDT:USDT": 0.5,
        }
        return prices.get(symbol, 1.0)
