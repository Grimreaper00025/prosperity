"""
=============================================================================
  PROSPERITY 4 — ALGORITHMIC TRADING TEMPLATE  (single-file submission)
=============================================================================

This file is a **self-contained** trading algorithm ready for upload to the
Prosperity exchange.  It embeds the complete data-model so no external
`datamodel.py` import is required, and ships with two baseline strategies:

  1. EMERALDS  → Tight market-making around the 10 000 fair value.
  2. TOMATOES  → EMA-based fair-value estimation + adaptive market-making.

Position limits, inventory skew, and logging are all handled.

Currency: XIRECS
"""

from __future__ import annotations

import json
import math
from json import JSONEncoder
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
#  DATA MODEL  (mirrors the official Prosperity datamodel.py)
# ═══════════════════════════════════════════════════════════════════════════

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int


class Listing:
    """Represents a tradable product on the exchange."""

    def __init__(self, symbol: Symbol, product: Product, denomination: int) -> None:
        self.symbol = symbol
        self.product = product
        self.denomination = denomination


class ConversionObservation:
    """Conversion-related market data (used in later rounds for arb)."""

    def __init__(
        self,
        bidPrice: float,
        askPrice: float,
        transportFees: float,
        exportTariff: float,
        importTariff: float,
        sugarPrice: float,
        sunlightIndex: float,
    ) -> None:
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sugarPrice = sugarPrice
        self.sunlightIndex = sunlightIndex


class Observation:
    """Container for all observations passed to the trader each tick."""

    def __init__(
        self,
        plainValueObservations: Dict[Product, ObservationValue],
        conversionObservations: Dict[Product, ConversionObservation],
    ) -> None:
        self.plainValueObservations = plainValueObservations
        self.conversionObservations = conversionObservations

    def __str__(self) -> str:
        return (
            "(plainValueObservations: "
            + json.dumps({k: v for k, v in self.plainValueObservations.items()})
            + ", conversionObservations: "
            + json.dumps({k: v.__dict__ for k, v in self.conversionObservations.items()})
            + ")"
        )


class Order:
    """
    A single order to be placed on the exchange.

    quantity > 0  →  BUY order
    quantity < 0  →  SELL order
    """

    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return self.__str__()


class OrderDepth:
    """
    The current order book for a single symbol.

    buy_orders:  { price: quantity }   — quantity is POSITIVE
    sell_orders: { price: quantity }   — quantity is NEGATIVE (convention)
    """

    def __init__(self) -> None:
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


class Trade:
    """A single executed trade."""

    def __init__(
        self,
        symbol: Symbol,
        price: int,
        quantity: int,
        buyer: UserId = None,
        seller: UserId = None,
        timestamp: int = 0,
    ) -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __str__(self) -> str:
        return (
            f"({self.symbol}, {self.buyer} << {self.seller}, "
            f"{self.price}, {self.quantity}, {self.timestamp})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class TradingState:
    """
    The full state object passed to ``Trader.run()`` every tick.

    Attributes
    ----------
    traderData : str
        Persistent string you returned last tick (use for state across ticks).
    timestamp : int
        Current simulation time (increments by 100 each tick).
    listings : Dict[Symbol, Listing]
        All products available for trading this round.
    order_depths : Dict[Symbol, OrderDepth]
        Current order book for every symbol.
    own_trades : Dict[Symbol, List[Trade]]
        Trades YOUR algorithm executed since the last tick.
    market_trades : Dict[Symbol, List[Trade]]
        Trades OTHER participants executed since the last tick.
    position : Dict[Product, Position]
        Your current net position per product.
    observations : Observation
        External data provided by the exchange (round-dependent).
    """

    def __init__(
        self,
        traderData: str,
        timestamp: Time,
        listings: Dict[Symbol, Listing],
        order_depths: Dict[Symbol, OrderDepth],
        own_trades: Dict[Symbol, List[Trade]],
        market_trades: Dict[Symbol, List[Trade]],
        position: Dict[Product, Position],
        observations: Observation,
    ) -> None:
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

    def toJSON(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


class ProsperityEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        return o.__dict__


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Position limits per product (adjust per round rules)
POSITION_LIMITS: Dict[Symbol, int] = {
    "EMERALDS": 20,
    "TOMATOES": 20,
}

# EMERALDS — stable fair value market-making parameters
EMERALDS_FAIR_VALUE = 10_000
EMERALDS_HALF_SPREAD = 4          # quote at fair ± 4  →  9996 / 10004
EMERALDS_ORDER_SIZE = 10          # max size per side per tick

# TOMATOES — adaptive fair-value estimation parameters
TOMATOES_EMA_ALPHA = 0.15         # smoothing factor for EMA (higher = faster)
TOMATOES_HALF_SPREAD = 4          # quote at EMA ± 4
TOMATOES_ORDER_SIZE = 8           # max size per side per tick
TOMATOES_AGGRESSION_THRESHOLD = 2 # take liquidity if edge > this


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def get_mid_price(order_depth: OrderDepth) -> Optional[float]:
    """Compute the mid-price from the best bid and best ask."""
    if not order_depth.buy_orders or not order_depth.sell_orders:
        return None
    best_bid = max(order_depth.buy_orders.keys())
    best_ask = min(order_depth.sell_orders.keys())
    return (best_bid + best_ask) / 2.0


def get_best_bid(order_depth: OrderDepth) -> Optional[int]:
    """Return the best (highest) bid price, or None."""
    return max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None


def get_best_ask(order_depth: OrderDepth) -> Optional[int]:
    """Return the best (lowest) ask price, or None."""
    return min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None


def get_position(state: TradingState, symbol: Symbol) -> int:
    """Return current position for *symbol*, defaulting to 0."""
    return state.position.get(symbol, 0)


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


# ═══════════════════════════════════════════════════════════════════════════
#  TRADER CLASS  (this is what you upload to the Prosperity platform)
# ═══════════════════════════════════════════════════════════════════════════

class Trader:
    """
    Main algo class.  The exchange calls ``run()`` on every tick.

    Return values:
      - result:      Dict[Symbol, List[Order]]  — orders to place
      - conversions:  int                        — conversion requests (0 if unused)
      - traderData:   str                        — serialised state persisted to next tick
    """

    def __init__(self) -> None:
        # Internal state (will be re-hydrated from traderData each tick)
        self.tomatoes_ema: Optional[float] = None

    # ─── MAIN ENTRY POINT ─────────────────────────────────────────────
    def run(
        self, state: TradingState
    ) -> tuple[Dict[Symbol, List[Order]], int, str]:

        # --- Restore persisted state ---
        self._load_state(state.traderData)

        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        # --- Trade every product that is listed ---
        for symbol in state.listings:
            if symbol == "EMERALDS":
                result[symbol] = self._trade_emeralds(state)
            elif symbol == "TOMATOES":
                result[symbol] = self._trade_tomatoes(state)
            else:
                # Placeholder for future products — no orders
                result[symbol] = []

        # --- Persist state for the next tick ---
        trader_data = self._save_state()

        return result, conversions, trader_data

    # ─── EMERALDS: FIXED-VALUE MARKET MAKING ──────────────────────────
    def _trade_emeralds(self, state: TradingState) -> List[Order]:
        """
        EMERALDS barely moves from 10 000.  Strategy:
          1. Take any mispriced liquidity (buy below fair, sell above fair).
          2. Post passive bids/asks inside the NPC spread (9992/10008).
        """
        symbol = "EMERALDS"
        orders: List[Order] = []
        order_depth = state.order_depths[symbol]
        pos = get_position(state, symbol)
        limit = POSITION_LIMITS[symbol]
        fair = EMERALDS_FAIR_VALUE

        # --- Phase 1: Take cheap asks (aggressive BUYs) ---
        if order_depth.sell_orders:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price < fair:
                    ask_vol = order_depth.sell_orders[ask_price]  # negative
                    max_buy = limit - pos
                    buy_qty = min(-ask_vol, max_buy)
                    if buy_qty > 0:
                        orders.append(Order(symbol, ask_price, buy_qty))
                        pos += buy_qty

        # --- Phase 2: Take expensive bids (aggressive SELLs) ---
        if order_depth.buy_orders:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price > fair:
                    bid_vol = order_depth.buy_orders[bid_price]  # positive
                    max_sell = limit + pos  # how many we can sell (pos can be negative)
                    sell_qty = min(bid_vol, max_sell)
                    if sell_qty > 0:
                        orders.append(Order(symbol, bid_price, -sell_qty))
                        pos -= sell_qty

        # --- Phase 3: Passive market-making quotes ---
        bid_price = fair - EMERALDS_HALF_SPREAD
        ask_price = fair + EMERALDS_HALF_SPREAD

        # Inventory skew: shift prices toward flattening the position
        skew = -round(pos * 0.25)
        bid_price += skew
        ask_price += skew

        buy_qty = clamp(EMERALDS_ORDER_SIZE, 0, limit - pos)
        sell_qty = clamp(EMERALDS_ORDER_SIZE, 0, limit + pos)

        if buy_qty > 0:
            orders.append(Order(symbol, int(bid_price), buy_qty))
        if sell_qty > 0:
            orders.append(Order(symbol, int(ask_price), -sell_qty))

        return orders

    # ─── TOMATOES: ADAPTIVE FAIR-VALUE MARKET MAKING ──────────────────
    def _trade_tomatoes(self, state: TradingState) -> List[Order]:
        """
        TOMATOES price drifts.  Strategy:
          1. Maintain an EMA of the mid-price as our fair value estimate.
          2. Aggressively lift/hit when the book is clearly mispriced vs EMA.
          3. Quote passively around the EMA with inventory skew.
        """
        symbol = "TOMATOES"
        orders: List[Order] = []
        order_depth = state.order_depths[symbol]
        pos = get_position(state, symbol)
        limit = POSITION_LIMITS[symbol]

        mid = get_mid_price(order_depth)
        if mid is None:
            return orders

        # Update EMA
        if self.tomatoes_ema is None:
            self.tomatoes_ema = mid
        else:
            self.tomatoes_ema = (
                TOMATOES_EMA_ALPHA * mid
                + (1 - TOMATOES_EMA_ALPHA) * self.tomatoes_ema
            )

        fair = self.tomatoes_ema

        # --- Phase 1: Aggressive takes when edge is large ---
        if order_depth.sell_orders:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price < fair - TOMATOES_AGGRESSION_THRESHOLD:
                    ask_vol = order_depth.sell_orders[ask_price]
                    max_buy = limit - pos
                    buy_qty = min(-ask_vol, max_buy)
                    if buy_qty > 0:
                        orders.append(Order(symbol, ask_price, buy_qty))
                        pos += buy_qty

        if order_depth.buy_orders:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price > fair + TOMATOES_AGGRESSION_THRESHOLD:
                    bid_vol = order_depth.buy_orders[bid_price]
                    max_sell = limit + pos
                    sell_qty = min(bid_vol, max_sell)
                    if sell_qty > 0:
                        orders.append(Order(symbol, bid_price, -sell_qty))
                        pos -= sell_qty

        # --- Phase 2: Passive quotes ---
        bid_price = math.floor(fair) - TOMATOES_HALF_SPREAD
        ask_price = math.ceil(fair) + TOMATOES_HALF_SPREAD

        # Inventory skew
        skew = -round(pos * 0.3)
        bid_price += skew
        ask_price += skew

        buy_qty = clamp(TOMATOES_ORDER_SIZE, 0, limit - pos)
        sell_qty = clamp(TOMATOES_ORDER_SIZE, 0, limit + pos)

        if buy_qty > 0:
            orders.append(Order(symbol, int(bid_price), buy_qty))
        if sell_qty > 0:
            orders.append(Order(symbol, int(ask_price), -sell_qty))

        return orders

    # ─── STATE PERSISTENCE ────────────────────────────────────────────
    def _load_state(self, trader_data: str) -> None:
        """Deserialise persistent state from the previous tick."""
        if not trader_data:
            return
        try:
            data = json.loads(trader_data)
            self.tomatoes_ema = data.get("tomatoes_ema")
        except (json.JSONDecodeError, TypeError):
            pass

    def _save_state(self) -> str:
        """Serialise state to persist across ticks."""
        return json.dumps(
            {
                "tomatoes_ema": self.tomatoes_ema,
            }
        )
