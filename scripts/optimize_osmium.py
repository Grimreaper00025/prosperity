import math
import collections
from typing import Dict, List, Any
import json
import subprocess
import re

def create_trader(base_edge, skew_mult):
    code = f"""import math
import collections
from typing import Dict, List, Any
import json

class Order:
    def __init__(self, symbol: str, price: int, quantity: int) -> None:
        self.symbol = symbol; self.price = price; self.quantity = quantity

class OrderDepth:
    def __init__(self) -> None:
        self.buy_orders: Dict[int, int] = {{}}; self.sell_orders: Dict[int, int] = {{}}

class TradingState:
    def __init__(self, traderData: str, timestamp: int, listings: Dict, order_depths: Dict, own_trades: Dict, market_trades: Dict, position: Dict, observations: Any) -> None:
        self.traderData = traderData; self.timestamp = timestamp; self.order_depths = order_depths; self.position = position; self.observations = observations

class Trader:
    def get_level_vol(self, orders_dict: Dict[int, int], level: int, is_buy: bool) -> int:
        sorted_prices = sorted(orders_dict.keys(), reverse=is_buy)
        if len(sorted_prices) > level: return abs(orders_dict[sorted_prices[level]])
        return 0

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {{}}
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            orders = []
            limit = 80
            can_buy = limit - position
            can_sell = limit + position
            
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else 0
            if not best_bid or not best_ask: continue

            if product == 'ASH_COATED_OSMIUM':
                skew = int({skew_mult} * (position / limit))
                my_bid = min(best_bid + 1, int(10000 - {base_edge} - skew))
                my_ask = max(best_ask - 1, int(10000 + {base_edge} - skew))
                
                my_bid = min(my_bid, best_ask - 1)
                my_ask = max(my_ask, best_bid + 1)
                
                if can_buy > 0: orders.append(Order(product, my_bid, can_buy))
                if can_sell > 0: orders.append(Order(product, my_ask, -can_sell))
                result[product] = orders
                
            elif product == 'INTARIAN_PEPPER_ROOT':
                if can_buy > 0:
                    vol = min(can_buy, self.get_level_vol(order_depth.sell_orders, 0, False))
                    if vol > 0:
                        orders.append(Order(product, best_ask, vol))
                        position += vol; can_buy -= vol
                if can_buy > 0:
                    orders.append(Order(product, best_bid, can_buy))
                result[product] = orders
                
        return result, 0, state.traderData
"""
    with open('temp_trader.py', 'w') as f:
        f.write(code)

def evaluate(base_edge, skew_mult):
    create_trader(base_edge, skew_mult)
    cmd = ['python3', '-m', 'prosperity4bt', 'temp_trader.py', '1', '--data', '.', '--no-out', '--no-progress', '--match-trades', 'worse', '--limit', 'ASH_COATED_OSMIUM:80', '--limit', 'INTARIAN_PEPPER_ROOT:80']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Find Total Profit
        match = re.search(r'final_pnl:\s*(-?[\d,]+)', result.stdout)
        if match:
            pnl = float(match.group(1).replace(',', ''))
            return pnl
    except Exception as e:
        pass
    return 0.0

best_pnl = 0
best_params = (0, 0)

for edge in [2.0, 2.5, 3.0, 3.5, 4.0]:
    for skew in [1.0, 2.0, 3.0, 4.0, 5.0]:
        pnl = evaluate(edge, skew)
        print(f"Edge: {edge}, Skew: {skew} => PnL: {pnl}")
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = (edge, skew)
            
print(f"Best: Edge={best_params[0]}, Skew={best_params[1]} with PnL {best_pnl}")
