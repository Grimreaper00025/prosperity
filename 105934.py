import math
from typing import Dict, List, Any
import json

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
        result = {}
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

            mid = (best_bid + best_ask) / 2.0

            if product == 'ASH_COATED_OSMIUM':
                # SOTA OSMIUM: High Frequency Imbalance Mean Reversion
                b_v1 = self.get_level_vol(order_depth.buy_orders, 0, True)
                a_v1 = self.get_level_vol(order_depth.sell_orders, 0, False)
                imb1 = (b_v1 - a_v1) / (b_v1 + a_v1) if (b_v1 + a_v1) > 0 else 0
                
                signal = imb1 * 2.0
                pullback = (10000 - mid) * 0.5
                fv = mid + signal + pullback
                
                # Extreme Imbalance Taking (Market Orders)
                if imb1 > 0.8 and can_buy > 0 and best_ask <= 10002:
                    take = min(can_buy, self.get_level_vol(order_depth.sell_orders, 0, False))
                    orders.append(Order(product, best_ask, take))
                    can_buy -= take; position += take
                elif imb1 < -0.8 and can_sell > 0 and best_bid >= 9998:
                    take = min(can_sell, self.get_level_vol(order_depth.buy_orders, 0, True))
                    orders.append(Order(product, best_bid, -take))
                    can_sell -= take; position -= take
                
                # Passive Skewed Quoting (Limit Orders)
                skew = int(1.0 * (position / limit))
                
                my_bid = min(best_bid + 1, int(math.floor(fv - 1 - skew)))
                my_ask = max(best_ask - 1, int(math.ceil(fv + 1 - skew)))
                my_bid = min(my_bid, best_ask - 1)
                my_ask = max(my_ask, best_bid + 1)
                
                # Take adverse limits
                for ask, vol in order_depth.sell_orders.items():
                    if ask < fv - 0.5 and can_buy > 0:
                        take = min(-vol, can_buy)
                        orders.append(Order(product, ask, take))
                        can_buy -= take; position += take
                        
                for bid, vol in order_depth.buy_orders.items():
                    if bid > fv + 0.5 and can_sell > 0:
                        take = min(vol, can_sell)
                        orders.append(Order(product, bid, -take))
                        can_sell -= take; position -= take
                
                if can_buy > 0: orders.append(Order(product, my_bid, can_buy))
                if can_sell > 0: orders.append(Order(product, my_ask, -can_sell))

            elif product == 'INTARIAN_PEPPER_ROOT':
                # SOTA PEPPER ROOT: Drift Exploitation (Max Long) + Extreme Spike Ladder
                # 1. Sweep to Max Long
                if can_buy > 0:
                    vol = min(can_buy, self.get_level_vol(order_depth.sell_orders, 0, False))
                    if vol > 0:
                        orders.append(Order(product, best_ask, vol))
                        position += vol; can_buy -= vol
                
                # 2. Passive bid for remainder
                if can_buy > 0:
                    orders.append(Order(product, best_bid, can_buy))
                
                # 3. Ladder Asks High to capture liquidity spikes
                if can_sell > 0:
                    chunk = int(can_sell * 0.3)
                    if chunk > 0:
                        orders.append(Order(product, best_ask + 4, -chunk))
                        orders.append(Order(product, best_ask + 8, -chunk))
                        orders.append(Order(product, best_ask + 12, -(can_sell - 2 * chunk)))

            result[product] = orders
            
        return result, 0, state.traderData