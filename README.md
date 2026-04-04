# IMC Prosperity — Round 0 Data Analysis

> [!IMPORTANT]
> This is **IMC Prosperity**, an algorithmic trading competition. You write a Python bot that receives market state and submits buy/sell orders. Your goal is to **maximize profit** by trading two products: **EMERALDS** and **TOMATOES**.

---

## 1. What Files Do We Have?

| File | Type | Size | Rows | Description |
|------|------|------|------|-------------|
| `prices_round_0_day_-2.csv` | Order Book | 1.3 MB | 20,001 data rows | Full order book snapshots for day -2 |
| `prices_round_0_day_-1.csv` | Order Book | 1.3 MB | 20,001 data rows | Full order book snapshots for day -1 |
| `trades_round_0_day_-2.csv` | Trade Log | 20 KB | 589 trades | All market trades that occurred on day -2 |
| `trades_round_0_day_-1.csv` | Trade Log | 21 KB | 632 trades | All market trades that occurred on day -1 |

- **Delimiter**: Semicolon (`;`) — NOT comma
- **Round**: 0 (tutorial/practice round)
- **Days**: -2 and -1 (historical training data before the live competition day 0)

---

## 2. Prices File Format (Order Book Snapshots)

### Columns

```
day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss
```

| Column | Meaning |
|--------|---------|
| `day` | Which day (-2 or -1) |
| `timestamp` | Tick number within the day (0, 100, 200, ..., up to 999,900) |
| `product` | The tradable instrument: `EMERALDS` or `TOMATOES` |
| `bid_price_1` | **Best (highest) bid price** — the highest price someone is willing to BUY at |
| `bid_volume_1` | Volume available at best bid |
| `bid_price_2` | Second-best bid price |
| `bid_volume_2` | Volume at second-best bid |
| `bid_price_3` | Third-best bid price (often empty) |
| `bid_volume_3` | Volume at third-best bid (often empty) |
| `ask_price_1` | **Best (lowest) ask price** — the lowest price someone is willing to SELL at |
| `ask_volume_1` | Volume available at best ask |
| `ask_price_2` / `ask_price_3` | Second/third-best ask prices and volumes |
| `mid_price` | Midpoint: `(best_bid + best_ask) / 2` |
| `profit_and_loss` | Your algo's PnL (always 0.0 because this is historical data, no algo was running) |

### Key Structural Facts
- **Timestamp step**: 100 units (each tick is 100ms apart)
- **Total ticks per day**: ~10,000 timestamps (0 to 999,900)
- **Rows per tick**: 2 (one for EMERALDS, one for TOMATOES) → ~20,000 rows per file
- **Order book depth**: Up to 3 levels on each side (bid/ask), but level 3 is often empty
- **Products per row**: 1 (each row is a separate product snapshot)

---

## 3. Trades File Format (Historical Trades)

### Columns

```
timestamp;buyer;seller;symbol;currency;price;quantity
```

| Column | Meaning |
|--------|---------|
| `timestamp` | When the trade occurred (same timescale as prices) |
| `buyer` | Who bought — **ALWAYS EMPTY** in this data |
| `seller` | Who sold — **ALWAYS EMPTY** in this data |
| `symbol` | `EMERALDS` or `TOMATOES` |
| `currency` | Always `XIRECS` (the in-game currency) |
| `price` | The execution price |
| `quantity` | Number of units traded |

> [!NOTE]
> The `buyer` and `seller` columns are blank (`;;;`). This means **we cannot see who is making these trades** — they are anonymous market participant trades. These represent the "bot" or NPC market makers trading in the background.

---

## 4. Product Analysis: EMERALDS 💎

### Behavior: **Extremely Stable / Mean-Reverting**

EMERALDS has a **true value very close to 10,000** and barely moves.

| Metric | Day -2 | Day -1 |
|--------|--------|--------|
| Mid price (typical) | **10,000.0** | **10,000.0** |
| Best bid (typical) | 9,992 | 9,992 |
| Best ask (typical) | 10,008 | 10,008 |
| Typical spread | **16** (9992→10008) | **16** (9992→10008) |
| Mid price excursions | Occasionally 9,996 or 10,004 | Occasionally 9,996 or 10,004 |

### Order Book Pattern (typical)

```
EMERALDS typical order book:
  Bid side:                Ask side:
  9992  ×  10-15           10008  ×  10-15
  9990  ×  20-30           10010  ×  20-30
                           
  Occasionally:            Occasionally:
  10000 ×  5-10 (bid)      10000 ×  5-10 (ask)
```

### Key Observations
- The spread is **always 16** (9992 to 10008) in normal conditions
- Sometimes a level at **10000** appears on either side — this creates a tighter spread temporarily (9992→10000 = 8, or 10000→10008 = 8)
- Level 3 depth rarely appears
- Bid volumes: 10-15 at level 1, 20-30 at level 2
- Ask volumes mirror the bid side almost exactly

### EMERALDS Trade Patterns (from trades files)
- Trades always execute at either **9,992** (at the bid) or **10,008** (at the ask), occasionally **10,000**
- Trade sizes: 3-8 units
- Trades are relatively infrequent compared to TOMATOES

> [!TIP]
> **EMERALDS Strategy Hint**: The fair value is clearly **10,000**. The market makers quote 9992/10008. If you can buy at 9,992 and sell at 10,008, you make 16 per unit. Even better, you can **quote inside the spread** (e.g., bid 9,996, ask 10,004) and make money as a market maker yourself.

---

## 5. Product Analysis: TOMATOES 🍅

### Behavior: **Volatile / Trending**

TOMATOES has a much more dynamic price that wanders significantly within and across days.

| Metric | Day -2 | Day -1 |
|--------|--------|--------|
| Mid price start | ~5,000 | ~5,006 |
| Mid price lowest seen | ~4,988 | ~4,984 |
| Mid price highest seen | ~5,001 | ~5,011 |
| Typical spread | **13-14** (e.g., 4993→5007) | **13-14** (e.g., 4996→5010) |
| Bid volumes | 5-10 at L1, 15-25 at L2 | 5-10 at L1, 15-25 at L2 |

### Day -2 Price Journey (from order book mid-prices)
```
Start (t=0):     ~5000
t=2000-3000:     Drops to ~4996
t=3000-6000:     Drops further to ~4994
t=6000-8000:     Bottom ~4993
t=8000-11000:    Drops to ~4992-4991
t=11000-14000:   Drops to ~4991-4990
t=14000-16000:   Stabilizes ~4991
t=16000-20000:   Recovers to ~4993
t=20000-25000:   Rises to ~4994-4995
t=25000-28000:   Drifts around ~4995
t=28000-35000:   Rises to ~4998-4999
t=35000-40000:   Fluctuates ~4993-4998
```

### Day -1 Price Journey
```
Start (t=0):     ~5006
t=0-5000:        Drops from 5006 to ~5002
t=5000-10000:    Fluctuates 5002-5007
t=10000-15000:   Moves 5007-5003
t=15000-20000:   Drifts 5003-4999
t=20000-25000:   Drops to ~4995
t=25000-30000:   Further decline to ~4990
t=30000-35000:   Drops sharply to ~4990
t=35000-40000:   Continues falling to ~4985
```

### TOMATOES Trade Patterns
- **Much more frequent** trading than EMERALDS
- Day -2: 417 TOMATO trades vs ~172 EMERALD trades (out of 589 total)
- Day -1: 440 TOMATO trades vs ~192 EMERALD trades (out of 632 total)
- Trade prices are spread across a wide range (not just at best bid/ask)
- Trade sizes: 2-5 units typical
- Prices sometimes **outside** the current bid/ask → suggests aggressive orders or fast price moves

### TOMATOES Order Book (typical row)
```
TOMATOES typical order book:
  Bid side:                Ask side:
  4993  ×  5-10            5007  ×  5-10
  4992  ×  15-25           5008  ×  15-25
  
  Level 3 sometimes present:
  4991  ×  varies          5009  ×  varies
```

> [!TIP]
> **TOMATOES Strategy Hint**: TOMATOES trends and mean-reverts on different timescales. You could use moving averages or fair value estimation to predict short-term direction and trade accordingly. The spread is ~13-14, so there's room to quote inside the spread similar to EMERALDS, but you must also manage **inventory risk** since the price actually moves.

---

## 6. Understanding the Game Mechanics

### What Your Algorithm Receives
Every tick (every 100 timestamp units), your `run()` method receives:
1. **Order book state** — the current bids and asks for each product (exactly what you see in the prices CSV)
2. **Recent trades** — trades that happened since the last tick
3. **Your current position** — how many units of each product you hold
4. **Your PnL** — current profit and loss

### What Your Algorithm Must Output
A dictionary of **Orders**:
```python
{
    "EMERALDS": [Order("EMERALDS", price, quantity), ...],
    "TOMATOES": [Order("TOMATOES", price, quantity), ...],
}
```

Each `Order` has three properties:
1. **symbol** — which product ("EMERALDS" or "TOMATOES")
2. **price** — the price you want to buy/sell at
3. **quantity** — positive = BUY, negative = SELL

### Position Limits
- You likely have a **position limit** per product (typically ±20 units in Prosperity)
- You cannot hold more than the limit in either direction

### Currency
- Everything is priced in **XIRECS** (the in-game seashell currency)
- Your PnL is tracked in XIRECS

---

## 7. Key Trading Opportunities

### 🟢 Opportunity 1: EMERALDS Market Making (Easy Money)

Since EMERALDS is pegged to ~10,000 with a wide 16-unit spread:
- **Buy at ≤ 9,997** and **sell at ≥ 10,003** = profit per round-trip
- Place standing limit orders: bid at 9,998, ask at 10,002
- The NPC bots quote 9992/10008, so you can **undercut them** and still profit
- Risk is very low because the price barely moves

### 🟡 Opportunity 2: TOMATOES Trend Following / Mean Reversion

TOMATOES has real price moves:
- Track the **mid-price** or a **moving average**
- When price dips below fair value, buy cheap
- When price rises above fair value, sell high
- Manage position carefully since the price can trend against you

### 🔵 Opportunity 3: TOMATOES Spread Capture

Like EMERALDS but riskier:
- Quote inside the 13-14 unit spread
- Example: bid at `mid_price - 3`, ask at `mid_price + 3`
- Must adjust quotes as mid-price moves

---

## 8. Data Format Summary (Quick Reference)

### Prices CSV — Semicolon Delimited
```
day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss
```
- **20,001 rows** per file (header + 10,000 timestamps × 2 products)
- Empty cells (`;;;`) when level 2 or 3 doesn't exist

### Trades CSV — Semicolon Delimited
```
timestamp;buyer;seller;symbol;currency;price;quantity
```
- **~590-632 rows** per file
- `buyer` and `seller` always empty
- Currency always `XIRECS`

---

## 9. Quick Stat Cheat Sheet

| Metric | EMERALDS | TOMATOES |
|--------|----------|----------|
| Fair value | **~10,000** (extremely stable) | **~4,990-5,010** (moves a lot) |
| Typical spread | **16** (9992/10008) | **13-14** (e.g. 4993/5007) |
| Volatility | Nearly zero | Moderate (~20-30 range within a day) |
| Best strategy | Market making around 10,000 | Estimate fair value + trade deviations |
| Trades per day | ~170-190 | ~420-440 |
| Trade size | 3-8 units | 2-5 units |
| Price at bid/ask? | Almost always at 9992 or 10008 | Varies widely |

---

## 10. What You Need to Build

```python
class Trader:
    def run(self, state):
        """
        Called every tick with the current market state.
        Must return a dict of product -> list of Orders.
        """
        orders = {}
        
        # For EMERALDS: market make around 10,000
        # For TOMATOES: estimate fair value and trade
        
        return orders
```

> [!CAUTION]
> **Position limits exist!** You must track your position and not exceed the limit. If you buy too much without selling, you'll hit the limit and miss future opportunities.
