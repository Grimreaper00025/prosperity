import pandas as pd
import numpy as np

def max_pnl_dp(df, product, limit=80):
    df = df[df['product'] == product].reset_index(drop=True)
    if df.empty:
        return 0
    n = len(df)
    # dp[i][pos] = max pnl at step i with position pos. pos ranges from -80 to 80.
    # We map pos to index 0 to 160.
    offset = limit
    dp = np.full((n + 1, 2 * limit + 1), -np.inf)
    dp[0][offset] = 0
    
    for i in range(n):
        # We can either stay, or trade up to max possible volume from the order book.
        # But this DP is O(N * limit^2). Let's simplify:
        # Assume we can buy/sell at mid_price for simplicity to get a bound, 
        # or at bid_price_1 / ask_price_1 (which is more realistic but we don't know the exact volume).
        # Let's assume we can buy/sell 1 unit at best_ask / best_bid to get a quick bound.
        
        # Actually, let's just do greedy with unlimited volume but restricted by position limit,
        # using best bid/ask.
        row = df.iloc[i]
        ask = row['ask_price_1']
        bid = row['bid_price_1']
        
        for pos in range(-limit, limit + 1):
            p_idx = pos + offset
            if dp[i][p_idx] == -np.inf:
                continue
                
            # Stay
            dp[i+1][p_idx] = max(dp[i+1][p_idx], dp[i][p_idx])
            
            # Buy
            for trade in range(1, limit - pos + 1):
                new_pos = pos + trade
                cost = ask * trade
                dp[i+1][new_pos + offset] = max(dp[i+1][new_pos + offset], dp[i][p_idx] - cost)
                
            # Sell
            for trade in range(1, pos + limit + 1):
                new_pos = pos - trade
                revenue = bid * trade
                dp[i+1][new_pos + offset] = max(dp[i+1][new_pos + offset], dp[i][p_idx] + revenue)
                
    # Final PnL = Cash + Position * final_mid_price
    final_mid = df.iloc[-1]['mid_price']
    max_pnl = -np.inf
    for pos in range(-limit, limit + 1):
        p_idx = pos + offset
        val = dp[n][p_idx] + pos * final_mid
        if val > max_pnl:
            max_pnl = val
            
    return max_pnl

if __name__ == '__main__':
    for day in [-2, -1, 0]:
        filename = f'prices_round_1_day_{day}.csv'
        try:
            df = pd.read_csv(filename, sep=';')
            pnl_pepper = max_pnl_dp(df, 'INTARIAN_PEPPER_ROOT')
            pnl_osmium = max_pnl_dp(df, 'ASH_COATED_OSMIUM')
            print(f"Day {day}:")
            print(f"  Pepper Max PnL (simplified DP): {pnl_pepper}")
            print(f"  Osmium Max PnL (simplified DP): {pnl_osmium}")
        except Exception as e:
            print(f"Error on {filename}: {e}")
