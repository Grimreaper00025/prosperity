"""
Local Backtester for IMC Prosperity (Optimized)
=================================================
Fast line-by-line parsing instead of csv.DictReader.
"""
import sys
from collections import defaultdict
from datamodel import Order, OrderDepth, TradingState, Listing, Trade, Observation


def parse_price_line(line: str):
    """Parse a single price CSV line. Returns (timestamp, product, row_fields)."""
    parts = line.strip().split(";")
    ts = int(parts[1])
    product = parts[2]
    return ts, product, parts


def build_order_depth_fast(parts: list) -> OrderDepth:
    """Build OrderDepth from pre-split line parts."""
    od = OrderDepth()
    # Indices: 3=bid_p1, 4=bid_v1, 5=bid_p2, 6=bid_v2, 7=bid_p3, 8=bid_v3
    #          9=ask_p1, 10=ask_v1, 11=ask_p2, 12=ask_v2, 13=ask_p3, 14=ask_v3
    for i, (pi, vi) in enumerate([(3,4), (5,6), (7,8)]):
        if pi < len(parts) and parts[pi].strip():
            od.buy_orders[int(float(parts[pi]))] = int(parts[vi])
    for i, (pi, vi) in enumerate([(9,10), (11,12), (13,14)]):
        if pi < len(parts) and parts[pi].strip():
            od.sell_orders[int(float(parts[pi]))] = -int(parts[vi])
    return od


def get_mid_price_fast(parts: list) -> float:
    """Extract mid_price from parts[15]."""
    return float(parts[15])


def match_orders(orders, order_depth, position, limit):
    """Match trader orders against the order book. Returns (fills_count, new_pos, pnl_delta)."""
    fills = 0
    pnl = 0.0
    pos = position

    for order in orders:
        remaining = order.quantity
        if remaining > 0:  # BUY
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if order.price >= ask_price and remaining > 0:
                    available = -order_depth.sell_orders[ask_price]
                    can_buy = min(remaining, available, limit - pos)
                    if can_buy > 0:
                        fills += 1
                        pos += can_buy
                        pnl -= ask_price * can_buy
                        remaining -= can_buy
        elif remaining < 0:  # SELL
            qty = -remaining
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if order.price <= bid_price and qty > 0:
                    available = order_depth.buy_orders[bid_price]
                    can_sell = min(qty, available, limit + pos)
                    if can_sell > 0:
                        fills += 1
                        pos -= can_sell
                        pnl += bid_price * can_sell
                        qty -= can_sell

    return fills, pos, pnl


def run_backtest(price_file: str, trade_file: str, day_label: str):
    """Run the backtest for one day."""
    from trader import Trader

    print(f"\n{'='*60}")
    print(f"  BACKTESTING: {day_label}")
    print(f"{'='*60}")

    # ── Load all price data into memory ──
    # Group by timestamp: {ts: {product: parts}}
    snapshots = {}
    with open(price_file, "r") as f:
        header = f.readline()  # skip header
        for line in f:
            if not line.strip():
                continue
            parts = line.strip().split(";")
            ts = int(parts[1])
            product = parts[2]
            if ts not in snapshots:
                snapshots[ts] = {}
            snapshots[ts][product] = parts

    trader = Trader()
    trader_data = ""
    positions = defaultdict(int)
    cash = 0.0
    total_fills = 0
    limits = {"EMERALDS": 20, "TOMATOES": 20}
    listings = {
        "EMERALDS": Listing("EMERALDS", "EMERALDS", "XIRECS"),
        "TOMATOES": Listing("TOMATOES", "TOMATOES", "XIRECS"),
    }
    last_mid_prices = {}

    timestamps = sorted(snapshots.keys())
    tick_count = 0

    for ts in timestamps:
        tick_count += 1

        # Build order depths
        order_depths = {}
        for product, parts in snapshots[ts].items():
            order_depths[product] = build_order_depth_fast(parts)
            last_mid_prices[product] = float(parts[15])

        # Build TradingState (no market trades for simplicity/speed)
        state = TradingState(
            traderData=trader_data,
            timestamp=ts,
            listings=listings,
            order_depths=order_depths,
            own_trades={},
            market_trades={},
            position=dict(positions),
            observations=Observation(),
        )

        # Call trader
        result, conversions, trader_data = trader.run(state)

        # Match orders against the book
        for product, orders in result.items():
            if not orders:
                continue
            # Build a fresh order depth for matching
            od = build_order_depth_fast(snapshots[ts][product])
            fills, new_pos, pnl_delta = match_orders(
                orders, od, positions[product], limits[product]
            )
            positions[product] = new_pos
            cash += pnl_delta
            total_fills += fills

        # Progress indicator
        if tick_count % 2000 == 0:
            print(f"  ... processed {tick_count}/{len(timestamps)} ticks")

    # Calculate final PnL
    mtm = sum(positions[p] * last_mid_prices.get(p, 0) for p in positions)
    total_pnl = cash + mtm

    print(f"\n  Results for {day_label}:")
    print(f"  ───────────────────────────────")
    print(f"  Ticks processed: {tick_count}")
    print(f"  Total fills:     {total_fills}")
    print(f"  Final positions: {dict(positions)}")
    print(f"  Cash (realized): {cash:,.1f}")
    print(f"  MTM value:       {mtm:,.1f}")
    print(f"  ───────────────────────────────")
    print(f"  TOTAL PnL:       {total_pnl:,.1f} XIRECS")
    print(f"  ───────────────────────────────")

    return total_pnl


if __name__ == "__main__":
    pnl_day_2 = run_backtest(
        "prices_round_0_day_-2.csv",
        "trades_round_0_day_-2.csv",
        "Day -2"
    )
    pnl_day_1 = run_backtest(
        "prices_round_0_day_-1.csv",
        "trades_round_0_day_-1.csv",
        "Day -1"
    )

    print(f"\n{'='*60}")
    print(f"  COMBINED PnL: {pnl_day_2 + pnl_day_1:,.1f} XIRECS")
    print(f"{'='*60}")
