"""
IMC Prosperity Round 0 Trading Algorithm
=========================================
Strategy:
  EMERALDS: Pure market-making around fair value 10,000.
            Place buy orders below fair value, sell orders above.
            The NPC spread is 9992/10008 (width 16), so we quote tighter.

  TOMATOES: Market-making with dynamic fair value estimation.
            Use a simple EMA of mid-prices to track fair value,
            then quote around it with a configurable spread.
"""
import json
from datamodel import Order, TradingState, OrderDepth
from typing import Dict, List


class Trader:
    # ─── Position limits (standard Prosperity round 0) ───
    POSITION_LIMITS = {
        "EMERALDS": 20,
        "TOMATOES": 20,
    }

    # ─── EMERALDS parameters ───
    EMERALDS_FAIR = 10_000         # True value is locked at 10,000
    EMERALDS_SPREAD_HALF = 2       # We quote 9998 / 10002 → 4-wide spread inside the 16-wide NPC spread
    EMERALDS_ORDER_SIZE = 5        # Units per order level

    # ─── TOMATOES parameters ───
    TOMATOES_EMA_ALPHA = 0.3       # Exponential moving average smoothing factor (higher = more responsive)
    TOMATOES_SPREAD_HALF = 3       # We quote fair_value ± 3   → 6-wide spread inside the ~14-wide NPC spread
    TOMATOES_ORDER_SIZE = 4        # Units per order level

    def run(self, state: TradingState) -> tuple:
        """
        Called every tick by the Prosperity engine.
        
        Returns:
            result: Dict[str, List[Order]] — orders to place
            conversions: int — not used in round 0
            traderData: str — serialized state to persist between ticks
        """
        # ── Load persisted state ──
        trader_state = self._load_state(state.traderData)

        result: Dict[str, List[Order]] = {}

        # ── Trade each product ──
        for product in state.order_depths:
            if product == "EMERALDS":
                result[product] = self._trade_emeralds(state, product)
            elif product == "TOMATOES":
                result[product] = self._trade_tomatoes(state, product, trader_state)

        # ── Serialize state for next tick ──
        trader_data = json.dumps(trader_state)

        return result, 0, trader_data

    # ═══════════════════════════════════════════════════════════════
    # EMERALDS — Pure market making around known fair value
    # ═══════════════════════════════════════════════════════════════
    def _trade_emeralds(self, state: TradingState, product: str) -> List[Order]:
        orders: List[Order] = []
        order_depth: OrderDepth = state.order_depths[product]
        position = state.position.get(product, 0)
        limit = self.POSITION_LIMITS[product]
        fair = self.EMERALDS_FAIR

        # ── Step 1: Take any mispriced orders (free money) ──
        # If someone is selling BELOW fair value, buy from them
        if order_depth.sell_orders:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price < fair and position < limit:
                    # sell_orders quantities are negative
                    ask_vol = -order_depth.sell_orders[ask_price]
                    can_buy = min(ask_vol, limit - position)
                    if can_buy > 0:
                        orders.append(Order(product, ask_price, can_buy))
                        position += can_buy

        # If someone is buying ABOVE fair value, sell to them
        if order_depth.buy_orders:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price > fair and position > -limit:
                    bid_vol = order_depth.buy_orders[bid_price]
                    can_sell = min(bid_vol, limit + position)
                    if can_sell > 0:
                        orders.append(Order(product, bid_price, -can_sell))
                        position -= can_sell

        # ── Step 2: Place our market-making quotes ──
        bid_price = fair - self.EMERALDS_SPREAD_HALF   # 9998
        ask_price = fair + self.EMERALDS_SPREAD_HALF   # 10002

        # Adjust size based on current position to stay within limits
        # If we're long, be more aggressive selling, less aggressive buying
        buy_size = min(self.EMERALDS_ORDER_SIZE, limit - position)
        sell_size = min(self.EMERALDS_ORDER_SIZE, limit + position)

        if buy_size > 0:
            orders.append(Order(product, bid_price, buy_size))
        if sell_size > 0:
            orders.append(Order(product, ask_price, -sell_size))

        return orders

    # ═══════════════════════════════════════════════════════════════
    # TOMATOES — Market making with dynamic fair value (EMA)
    # ═══════════════════════════════════════════════════════════════
    def _trade_tomatoes(self, state: TradingState, product: str,
                        trader_state: dict) -> List[Order]:
        orders: List[Order] = []
        order_depth: OrderDepth = state.order_depths[product]
        position = state.position.get(product, 0)
        limit = self.POSITION_LIMITS[product]

        # ── Calculate current mid price ──
        mid_price = self._get_mid_price(order_depth)
        if mid_price is None:
            return orders

        # ── Update EMA fair value ──
        ema_key = "tomatoes_ema"
        if ema_key in trader_state and trader_state[ema_key] is not None:
            old_ema = trader_state[ema_key]
            fair = old_ema + self.TOMATOES_EMA_ALPHA * (mid_price - old_ema)
        else:
            fair = mid_price  # First tick — initialize

        trader_state[ema_key] = fair
        fair_rounded = round(fair)

        # ── Step 1: Take mispriced orders ──
        # Buy anything offered below our fair value
        if order_depth.sell_orders:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price < fair_rounded and position < limit:
                    ask_vol = -order_depth.sell_orders[ask_price]
                    can_buy = min(ask_vol, limit - position)
                    if can_buy > 0:
                        orders.append(Order(product, ask_price, can_buy))
                        position += can_buy

        # Sell to anyone bidding above our fair value
        if order_depth.buy_orders:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price > fair_rounded and position > -limit:
                    bid_vol = order_depth.buy_orders[bid_price]
                    can_sell = min(bid_vol, limit + position)
                    if can_sell > 0:
                        orders.append(Order(product, bid_price, -can_sell))
                        position -= can_sell

        # ── Step 2: Place market-making quotes ──
        bid_price = fair_rounded - self.TOMATOES_SPREAD_HALF
        ask_price = fair_rounded + self.TOMATOES_SPREAD_HALF

        # Skew sizes based on position to mean-revert inventory
        # If long → want to sell more than buy. If short → want to buy more than sell.
        position_skew = -position / limit  # ranges from -1 (max long) to +1 (max short)
        base_size = self.TOMATOES_ORDER_SIZE

        buy_size = min(int(base_size * (1 + position_skew * 0.5)), limit - position)
        sell_size = min(int(base_size * (1 - position_skew * 0.5)), limit + position)

        buy_size = max(0, buy_size)
        sell_size = max(0, sell_size)

        if buy_size > 0:
            orders.append(Order(product, bid_price, buy_size))
        if sell_size > 0:
            orders.append(Order(product, ask_price, -sell_size))

        return orders

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════
    def _get_mid_price(self, order_depth: OrderDepth) -> float | None:
        """Calculate mid price from the order book."""
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def _load_state(self, trader_data: str) -> dict:
        """Load persisted trader state from JSON string."""
        if trader_data and trader_data.strip():
            try:
                return json.loads(trader_data)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}
