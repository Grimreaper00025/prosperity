import subprocess
import re
from multiprocessing import Pool
import itertools

def create_trader_code(p_edge, p_skew, signal_mult):
    return f"""import math
import collections
from typing import Dict, List, Any

class Order:
    def __init__(self, symbol: str, price: int, quantity: int) -> None:
        self.symbol = symbol; self.price = price; self.quantity = quantity

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
            if product != 'INTARIAN_PEPPER_ROOT': continue
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            orders = []
            limit = 80
            can_buy = limit - position
            can_sell = limit + position
            
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else 0
            if not best_bid or not best_ask: continue

            mid = (best_bid + best_ask) / 2.0
            
            b_v1 = self.get_level_vol(order_depth.buy_orders, 0, True)
            a_v1 = self.get_level_vol(order_depth.sell_orders, 0, False)
            imb1 = (b_v1 - a_v1) / (b_v1 + a_v1) if (b_v1 + a_v1) > 0 else 0
            
            signal = imb1 * {signal_mult}
            
            # Since drift is positive, we want a large positive target inventory.
            desired_pos = 80
            pos_diff = position - desired_pos
            skew = (pos_diff / limit) * {p_skew}
            
            fv = mid + signal
            
            my_bid = min(best_bid + 1, int(math.floor(fv - {p_edge} - skew)))
            my_ask = max(best_ask - 1, int(math.ceil(fv + {p_edge} - skew)))
            
            my_bid = min(my_bid, best_ask - 1)
            my_ask = max(my_ask, best_bid + 1)
            
            for ask, vol in order_depth.sell_orders.items():
                if ask < fv - {p_edge} and can_buy > 0:
                    take = min(-vol, can_buy)
                    orders.append(Order(product, ask, take))
                    can_buy -= take; position += take
                    
            for bid, vol in order_depth.buy_orders.items():
                if bid > fv + {p_edge} and can_sell > 0:
                    take = min(vol, can_sell)
                    orders.append(Order(product, bid, -take))
                    can_sell -= take; position -= take
            
            if can_buy > 0: orders.append(Order(product, my_bid, can_buy))
            if can_sell > 0: orders.append(Order(product, my_ask, -can_sell))
            
            result[product] = orders
            
        return result, 0, state.traderData
"""

def evaluate(params):
    p_edge, p_skew, signal_mult = params
    filename = f'temp_pepper_{str(p_edge).replace(".", "_")}_{str(p_skew).replace(".", "_")}_{str(signal_mult).replace(".", "_")}.py'
    code = create_trader_code(p_edge, p_skew, signal_mult)
    with open(filename, 'w') as f:
        f.write(code)
        
    cmd = ['/home/yashashwi-s/.local/bin/prosperity4btx', filename, '1', '--data', '.', '--no-out', '--no-progress', '--match-trades', 'worse', '--limit', 'ASH_COATED_OSMIUM:80', '--limit', 'INTARIAN_PEPPER_ROOT:80']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        match = re.search(r'final_pnl:\s*(-?[\d,]+)', result.stdout + result.stderr)
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
    p_skews = [1.0, 2.0, 3.0, 5.0, 10.0]
    signal_mults = [1.0, 2.0, 5.0, 10.0]
    
    param_list = list(itertools.product(p_edges, p_skews, signal_mults))
    
    best_pnl = -999999
    best_params = None
    
    with Pool(8) as p:
        results = p.map(evaluate, param_list)
        
    for params, pnl in results:
        if pnl > best_pnl:
            best_pnl = pnl
            best_params = params
            
    print(f"Best PnL: {best_pnl} with params P_EDGE={best_params[0]}, P_SKEW={best_params[1]}, SIGNAL={best_params[2]}")
