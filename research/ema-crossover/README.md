# EMA Crossover Backtest

The EMA Projection calls the EMA's next direction right on 82 to 86% of held-out bars (see
[ema-projection](../ema-projection/README.md)). Does trading crossover signals a bar early, on the
projected EMA instead of the actual one, make or save money? This folder tests it on ES futures and
SPY. **Short answer: no.** The verdict and every table are in [RESULTS.md](RESULTS.md).

## Running It

Python 3.9 or later, standard library only. It reuses `../ema-projection/projection.py` and the bars
`../ema-projection/fetch.py` downloads.

```sh
python3 ../ema-projection/fetch.py     # if ../ema-projection/data is empty
python3 backtest.py                    # writes RESULTS.md (about 20 seconds)
python3 -m unittest test_strategies    # no-lookahead and engine checks
```

## Strategies

Every signal is computed at the close of bar i from closes up to bar i. `state` is +1 (long side),
-1 (short side) or 0 (no opinion: keep the last position). `q(i)` is the EMA Projection's value for bar
i+1, made at bar i, with either `PriceHold` or `AverageSlope`; `k = 2 / (P + 1)`.

| Strategy | Actual EMA | One bar early |
|---|---|---|
| EMA direction | sign(ema[i] - ema[i-1]): long while the EMA rises | sign(q(i) - ema[i]): long while the projection says it will rise next bar |
| Price/EMA cross | sign(close[i] - ema[i]) | sign(close[i] - q(i)): the close against the projected next EMA |
| Fast/slow EMA cross | sign(emaFast[i] - emaSlow[i]) | sign(qFast(i) - qSlow(i)): both EMAs projected to the next bar |

Each runs **long/short** (+1 long, -1 short) and **long/flat** (-1 means no position). For context,
the results also show **buy and hold** and a **random-entry benchmark**: 1,000 strategies that change
position the same number of times as the rule, at random bars, alternating sides. Each rule's
*Random pctile* is the share of those random strategies it beat.

With PriceHold, the early signal of the two single-EMA rules is the actual signal. Because
`ema[i] = ema[i-1] + k (close[i] - ema[i-1])`, `close[i] - ema[i] = (1 - k)(close[i] - ema[i-1])`,
so the EMA rises exactly when the close is above it. PriceHold projects the next change as
`q(i) - ema[i] = k (close[i] - ema[i])`, with the same sign. So the EMA's direction, the price/EMA
cross and both early versions make the same decision on every bar. The tests check this, and
RESULTS.md marks those pairs *identical*. Only the fast/slow cross, whose two EMAs have different
`k`, can act differently a bar early.

## Trading and Costs

- **Fills:** a decision made at the close of bar i is filled at the open of bar i+1 and held until the
  open after the next change. No decision reads a price after its bar; the tests check every signal
  on truncated data and with later bars altered.
- **Size:** one ES contract ($50 a point) or one SPY share. No leverage, margin interest or dividends.
- **Costs per side:** ES $2.50 commission plus 0.25 point (one tick, $12.50) of slippage. SPY $0.005 a
  share plus $0.01 slippage. A reversal from long to short is two sides. Every table shows the P&L
  after costs and the gross P&L before them.

## Discipline

Each series is split in time. The first 110 bars warm up the EMAs. Of the rest, the first 60% chooses
the parameter: EMA period from 5, 9, 14, 21, 34 and 50, or fast/slow pair from 5/20, 9/21, 14/50 and 20/50.
The choice is made separately for each strategy and mode, by the actual-EMA rule's after-cost net P&L.
The early rule uses the same parameter, so the two differ only in acting a bar early. Every reported
number is from the last 40%, which played no part in the choice.

## Metrics

Net P&L and return (P&L over one unit's notional at the start of the held-out part); trades (a trade
is a stretch in one position, closed at the end of the data if still open), win rate, average trade
and profit factor, all after costs; maximum drawdown of cumulative P&L; Sharpe ratio of per-bar
returns on the unit's notional, annualized by the bars a year the held-out part actually has (252 for
daily; for intraday, as many as the sessions Yahoo reports); exposure (the share of bars in a
position).

**Significance:** for each early-vs-actual pair, a circular block bootstrap (2,000 resamples of 20-bar
blocks) of the per-bar P&L difference gives a 95% interval and a two-sided p for no difference.
The random-entry percentile asks the same of each rule against chance.

## Results

Held out, after costs, long/short. Net P&L is in dollars; *Random* is the random-entry percentile.
The price/EMA cross row stands for all four identical single-EMA rules. The last column is early
fast/slow minus actual fast/slow, with its bootstrap p.

| Series | Buy and hold | Price/EMA cross (= EMA direction = early PriceHold) | Fast/slow cross, actual | Fast/slow cross, early PriceHold | Early minus actual (p) |
|---|---|---|---|---|---|
| ES=F 30m | -23,530 | P 9: 8,160, Sharpe 1.62, random 78% | 9/21: 5,695, 1.12, 63% | 4,675, 0.92, 64% | -1,020 (0.76) |
| ES=F 1h | 36,508 | P 50: -81,358, -1.63, 9% | 5/20: -76,672, -1.59, 9% | -12,772, -0.29, 49% | +63,900 (< 0.01) |
| ES=F 1d | 279,570 | P 50: 11,420, 0.01, 56% | 20/50: 90,955, 0.17, 82% | 75,865, 0.17, 77% | -15,090 (0.57) |
| SPY 30m | -40.29 | P 9: 19.96, 2.44, 72% | 5/20: -7.45, -0.85, 43% | -18.17, -2.14, 32% | -10.72 (0.37) |
| SPY 1h | 74.79 | P 9: -74.98, -0.70, 25% | 5/20: -38.60, -0.34, 37% | -102, -0.98, 17% | -63.32 (0.08) |
| SPY 1d | 600 | P 50: 69.97, -0.06, 62% | 14/50: 56.33, -0.01, 61% | 64.27, -0.01, 62% | +7.94 (0.87) |

The verdict, in RESULTS.md, explains this table:

- For single-EMA rules the projection gives no earlier signal.
- The early fast/slow cross helps on 2 series and hurts on 4.
- The significant differences are all on ES=F and do not carry over to SPY.
- None of the rules beats random entries with the same number of trades by a margin that rules out chance.

## Caveats

- **ES=F is Yahoo's continuous front-month series, not back-adjusted.** Quarterly rolls show up as price
  jumps that a real position would not earn or lose. They hit the actual and early rules alike, but they add
  noise to both.
- **SPY prices exclude dividends**, which understates buy and hold and every long position on daily bars.
- **Short intraday samples.** The held-out 30-minute parts are 856 (ES) and 266 (SPY) bars, about a month.
- **One parameter per rule**, chosen by the actual rule. An early rule tuned on its own might pick
  differently. The tables show the same signals at their chosen parameter, not a search for the best
  early setting.
- **Many comparisons.** With 48 early-vs-actual tests, a few p < 0.05 results are expected by chance.
