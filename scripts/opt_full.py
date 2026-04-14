import subprocess
import re
from multiprocessing import Pool
import itertools

def create_trader_code(p_edge, p_skew, o_edge, o_skew):
    return f"""import math
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
                skew = ({o_skew} * position) / limit
                my_bid = min(best_bid + 1, int(math.floor(10000 - {o_edge} - skew)))
                my_ask = max(best_ask - 1, int(math.ceil(10000 + {o_edge} - skew)))
                my_bid = min(my_bid, best_ask - 1)
                my_ask = max(my_ask, best_bid + 1)
                
                if can_buy > 0: orders.append(Order(product, my_bid, can_buy))
                if can_sell > 0: orders.append(Order(product, my_ask, -can_sell))

            elif product == 'INTARIAN_PEPPER_ROOT':
                mid = (best_bid + best_ask) / 2.0
                # Using an EMA or microprice could be better, but let's just make markets around mid with a huge skew towards holding +80.
                # Actually, pepper root drifts UP. So we want to buy it. But it fluctuates. 
                # What if we market make with a moving average? 
                
                # Let's try simple market making but biased to be long:
                skew = ({p_skew} * position) / limit
                # We subtract skew so that positive position LOWERS our bids/asks.
                # But we want to be MAX LONG. So we can add a constant to push our bids up.
                fv = mid + 1.0  # Bias upwards to accumulate
                
                my_bid = min(best_bid + 1, int(math.floor(fv - {p_edge} - skew)))
                my_ask = max(best_ask - 1, int(math.ceil(fv + {p_edge} - skew)))
                
                my_bid = min(my_bid, best_ask - 1)
                my_ask = max(my_ask, best_bid + 1)
                
                # Take liquidity if it's cheap
                for ask, vol in order_depth.sell_orders.items():
                    if ask < fv - {p_edge} and can_buy > 0:
                        take_vol = min(-vol, can_buy)
                        orders.append(Order(product, ask, take_vol))
                        can_buy -= take_vol
                        position += take_vol
                
                for bid, vol in order_depth.buy_orders.items():
                    if bid > fv + {p_edge} and can_sell > 0:
                        take_vol = min(vol, can_sell)
                        orders.append(Order(product, bid, -take_vol))
                        can_sell -= take_vol
                        position -= take_vol

                if can_buy > 0: orders.append(Order(product, my_bid, can_buy))
                if can_sell > 0: orders.append(Order(product, my_ask, -can_sell))

            result[product] = orders
                
        return result, 0, state.traderData
"""

def evaluate(params):
    p_edge, p_skew, o_edge, o_skew = params
    filename = f'temp_trader_{p_edge}_{p_skew}_{o_edge}_{o_skew}.py'
    code = create_trader_code(p_edge, p_skew, o_edge, o_skew)
    with open(filename, 'w') as f:
        f.write(code)
        
    cmd = ['/home/yashashwi-s/.local/bin/prosperity4btx', filename, '1', '--data', '.', '--no-out', '--no-progress', '--match-trades', 'worse', '--limit', 'ASH_COATED_OSMIUM:80', '--limit', 'INTARIAN_PEPPER_ROOT:80']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        match = re.search(r'final_pnl:\s*(-?[\d,]+)', result.stdout)
        if match:
            pnl = float(match.group(1).replace(',', ''))
            return (params, pnl)
    except Exception as e:
        pass
    finally:
        import os
        if os.path.exists(filename):
            os.remove(filename)
    return (params, -999999)

if __name__ == '__main__':
    p_edges = [0.5, 1.0, 1.5, 2.0]
    p_skews = [1.0, 3.0, 5.0, 10.0]
    o_edges = [1.5, 2.0]
    o_skews = [5.0, 6.0]
    
    param_list = list(itertools.product(p_edges, p_skews, o_edges, o_skews))
    
    best_pnl = -999999
    best_params = None
    
    with Pool(8) as p:
        results = p.map(evaluate, param_list)
        
    for params, pnl in results:
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = params
            
    print(f"Best PnL: {best_pnl} with params P_EDGE={best_params[0]}, P_SKEW={best_params[1]}, O_EDGE={best_params[2]}, O_SKEW={best_params[3]}")
