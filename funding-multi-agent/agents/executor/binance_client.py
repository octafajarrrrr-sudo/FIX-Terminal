"""Binance Futures client wrapper using CCXT.

Handles all direct interactions with the Binance Futures API including
funding rate queries, leverage/margin configuration, and order execution.
"""

from __future__ import annotations

import os
import ccxt
import logging

logger = logging.getLogger(__name__)


class BinanceClient:
    """Wrapper around CCXT binance client for futures operations."""

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """Initialize the Binance futures client.

        Args:
            api_key: Binance API key. Falls back to BINANCE_API_KEY env var.
            api_secret: Binance API secret. Falls back to BINANCE_API_SECRET env var.
            testnet: If True, use the Binance futures testnet.
        """
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.testnet = testnet

        options = {
            "defaultType": "future",
            "enableRateLimit": True,
        }

        if self.testnet:
            options["sandboxMode"] = True

        self.exchange = ccxt.binance({
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "options": options,
        })

        if self.testnet:
            self.exchange.set_sandbox_mode(True)

        logger.info("BinanceClient initialized (testnet=%s)", self.testnet)

    def get_funding_rates(self) -> list[dict]:
        """Fetch funding rates for all USDT-M perpetual pairs.

        Returns:
            List of dicts with keys: symbol, funding_rate, mark_price, next_funding_time.
        """
        try:
            funding_rates = self.exchange.fetch_funding_rates()
            result = []
            for symbol, info in funding_rates.items():
                if not symbol.endswith("/USDT:USDT"):
                    continue
                result.append({
                    "symbol": symbol,
                    "funding_rate": info.get("fundingRate", 0) * 100,  # convert to percentage
                    "mark_price": info.get("markPrice", 0),
                    "next_funding_time": info.get("fundingTimestamp", 0),
                })
            logger.info("Fetched funding rates for %d pairs", len(result))
            return result
        except Exception as e:
            logger.error("Failed to fetch funding rates: %s", e)
            return []

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USDT:USDT').
            leverage: Leverage multiplier (e.g. 10).

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.exchange.set_leverage(leverage, symbol)
            logger.info("Set leverage %dx for %s", leverage, symbol)
            return True
        except Exception as e:
            logger.error("Failed to set leverage for %s: %s", symbol, e)
            return False

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> bool:
        """Set margin type for a symbol.

        Args:
            symbol: Trading pair symbol.
            margin_type: 'ISOLATED' or 'CROSSED'.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.exchange.set_margin_mode(margin_type.lower(), symbol)
            logger.info("Set margin type %s for %s", margin_type, symbol)
            return True
        except Exception as e:
            # Already set to this type is not an error
            if "No need to change margin type" in str(e):
                logger.info("Margin type already %s for %s", margin_type, symbol)
                return True
            logger.error("Failed to set margin type for %s: %s", symbol, e)
            return False

    def create_market_order(self, symbol: str, side: str, quantity: float) -> dict | None:
        """Create a market order.

        Args:
            symbol: Trading pair symbol.
            side: 'buy' or 'sell'.
            quantity: Order quantity.

        Returns:
            Order info dict if successful, None otherwise.
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=quantity,
            )
            logger.info("Market %s order placed: %s qty=%f", side, symbol, quantity)
            return order
        except Exception as e:
            logger.error("Failed to create market %s order for %s: %s", side, symbol, e)
            return None

    def get_open_positions(self, symbol: str = None) -> list[dict]:
        """Get currently open positions.

        Args:
            symbol: If provided, filter for this symbol only.

        Returns:
            List of position dicts with non-zero amounts.
        """
        try:
            positions = self.exchange.fetch_positions([symbol] if symbol else None)
            open_pos = [
                p for p in positions
                if float(p.get("contracts", 0)) > 0
            ]
            return open_pos
        except Exception as e:
            logger.error("Failed to fetch positions: %s", e)
            return []

    def get_account_balance(self) -> float:
        """Get the total USDT balance in futures account.

        Returns:
            Total USDT balance as float.
        """
        try:
            balance = self.exchange.fetch_balance()
            usdt = balance.get("USDT", {})
            total = float(usdt.get("total", 0))
            logger.info("Account balance: %.4f USDT", total)
            return total
        except Exception as e:
            logger.error("Failed to fetch balance: %s", e)
            return 0.0

    def get_mark_price(self, symbol: str) -> float:
        """Get current mark price for a symbol.

        Args:
            symbol: Trading pair symbol.

        Returns:
            Mark price as float, or 0.0 on error.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker.get("last", 0))
        except Exception as e:
            logger.error("Failed to fetch mark price for %s: %s", symbol, e)
            return 0.0
