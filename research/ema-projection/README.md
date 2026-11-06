# EMA Projection Backtest

How well does each way of projecting an EMA one bar ahead forecast the EMA the next bar
actually prints? This folder answers that for the
[EMA Projection](../../NinjaTrader/Indicators/EMAProjection.cs) indicator and picks its default.

## Running It

Python 3.9 or later, standard library only (`requirements.txt` lists no packages).

```sh
python3 fetch.py                       # Yahoo Finance bars into data/ (not committed)
python3 backtest.py                    # writes RESULTS.md
python3 -m unittest test_projection    # the hand-computed checks below
```

`fetch.py` downloads ES=F (E-mini S&P 500 continuous futures) and SPY from Yahoo Finance's
public chart API: 30-minute bars (Yahoo keeps about 60 days), 1-hour bars (about 730 days)
and daily bars (ES=F from 2000, SPY from 1993). SPY is the out-of-sample instrument: every
choice was made looking at ES=F, then checked on SPY.

## Method

- `projection.py` reproduces NinjaTrader 8's EMA exactly (seeded with the first close,
  `k = 2 / (Period + 1)`) and every candidate projection. Each forecasts the EMA of bar t
  from bars up to t-1 only, written with NinjaScript's "n bars ago" indexing so the lines
  can be read against the C#.
- Candidates: A, no change (`ema[1]`); B, the last bar's change repeated (`2*ema[1] - ema[2]`);
  AverageSlope before and after the off-by-one fix; slopes over the last 2, 3 and 5 bars; an
  exponentially weighted slope (an EMA of the EMA's one-bar changes, which is Holt's trend with
  the EMA as its level); Holt's linear trend on the closes, turned into an EMA forecast through
  the EMA's own update; the last bar's change times a damping factor phi; and PriceHold.
- Each series is split in time. Parameters are chosen by mean absolute error on the first 60%;
  all reported numbers come from the last 40%. Periods 14 (the default), 9, 21 and 50.
- Metrics: MAE and RMSE; direction hit rate (did `projection - ema[1]` have the sign of the real
  change); and lag after turns (bars from an EMA turn that lasts at least 3 bars until the
  projection points the new way, 0 meaning it already did).

## Results

Held out, Period 14 (full tables, including every period, in [RESULTS.md](RESULTS.md)).
MAE is in price points; the lag is the median.

| Series | Held-out bars | B: last-bar slope | AverageSlope before fix | AverageSlope | PriceHold | PriceHold vs B |
|---|---|---|---|---|---|---|
| ES=F 30m | 890 | 0.890, 82.0%, lag 1 | 1.835, 70.0%, lag 3 | 1.780, 70.0%, lag 3 | **0.869**, 82.0%, lag 1 | -2.5% |
| ES=F 1h | 5466 | 1.193, 85.4%, lag 1 | 2.235, 70.5%, lag 3 | 2.180, 70.5%, lag 3 | **1.136**, 85.4%, lag 1 | -4.7% |
| ES=F 1d | 2628 | 4.114, 86.2%, lag 1 | 6.852, 73.6%, lag 3 | 6.734, 73.6%, lag 3 | **3.959**, 86.2%, lag 1 | -3.8% |
| SPY 30m | 300 | 0.155, 86.3%, lag 1 | 0.334, 71.0%, lag 4 | 0.328, 71.0%, lag 4 | **0.149**, 86.3%, lag 1 | -3.7% |
| SPY 1h | 2021 | 0.197, 85.8%, lag 1 | 0.388, 67.9%, lag 4 | 0.380, 67.9%, lag 4 | **0.187**, 85.8%, lag 1 | -5.0% |
| SPY 1d | 3388 | 0.355, 84.7%, lag 1 | 0.592, 71.7%, lag 3 | 0.582, 71.7%, lag 3 | **0.341**, 84.7%, lag 1 | -3.9% |

What it shows:

- **AverageSlope is the worst of the trend methods everywhere**: about 1.6 to 2.1 times
  the last-bar slope's error at Period 14 (up to 3.9 times at Period 50), the wrong direction
  on 26 to 32% of bars, and a median 3 to 4 bars (up to 12) to follow a turn. The off-by-one
  fix lowers its error by up to 3% but leaves it far behind, because an average over Period bars
  of an already smoothed series lags.
- **Longer windows are worse, not better.** Spans 2, 3 and 5 rank in that order, all behind B.
  The exponentially weighted slope only matches B when its smoothing is light (beta 0.9 was
  always chosen), which makes it nearly B.
- **PriceHold beats B in 23 of 24 series-and-period cases** and ties the 24th (SPY 30m at
  Period 50, 1.0003). It points the same way as B on every bar (it is B times a positive
  factor), so its hit rate and lag equal B's; it wins on size, with up to 8% lower MAE.
- **Holt's method, tuned freely, chose alpha 1 and beta 0 on every series**, which is exactly
  PriceHold. Damping the last-bar slope with a tuned phi chose 0.85 to 0.9, next to PriceHold's
  fixed `1 - k = 0.867` at Period 14, and did no better. On these markets no trend estimate
  beat "the next close equals the last close".

Why: the EMA's next change is `k * (next close - ema[1])`, so forecasting the EMA is forecasting
the next close. Prices at these horizons are close to a random walk, whose best guess for the
next close is the last close. PriceHold is that guess pushed through the EMA's formula. Any
trend estimate adds the noise of estimating the trend, and the longer its window, the further
it lags.

On short stretches B can come out ahead: on the last 170 ES=F 30-minute bars (Nov 2-6 2026)
B's MAE was 1.410 and PriceHold's 1.414, against 3.903 for AverageSlope before the fix.

## The Formula, Line by Line

On bar t, with `ema[n]` meaning the EMA n bars ago and `k = 2 / (Period + 1)`:

| Method | C# in `EMAProjection.cs` | Python in `projection.py` |
|---|---|---|
| PriceHold | `slope = (1 - k) * (ema1 - ema2); Projection[0] = ema1 + slope;` | `p[t] = ema1 + (1 - k) * (ema1 - ema2)` |
| AverageSlope | `slope = (ema1 - emaX) / Period; Projection[0] = ema1 + slope;` with `emaX = ema[Period + 1]` | `p[t] = ema1 + (ema1 - emaX) / span` with `span = period` |

PriceHold needs two closed bars (`CurrentBar >= 2`), AverageSlope `Period + 1`.

Hand-computed check, Period 3 (`k = 0.5`), closes 100, 102, 101, 104, 103, 105
(`test_projection.py` asserts every value):

| Bar | Close | EMA | PriceHold | AverageSlope | AverageSlope before fix |
|---|---|---|---|---|---|
| 0 | 100 | 100 | | | |
| 1 | 102 | 101 | | | |
| 2 | 101 | 101 | 101 + 0.5 × (101 - 100) = 101.5 | | |
| 3 | 104 | 102.5 | 101 + 0.5 × (101 - 101) = 101 | | |
| 4 | 103 | 102.75 | 102.5 + 0.5 × (102.5 - 101) = 103.25 | 102.5 + (102.5 - 100) / 3 = 103.333 | 102.5 + 2.5 / 2 = 103.75 |
| 5 | 105 | 103.875 | 102.75 + 0.5 × (102.75 - 102.5) = 102.875 | 102.75 + (102.75 - 101) / 3 = 103.333 | 102.75 + 1.75 / 2 = 103.625 |

PriceHold is also exactly the EMA the bar would give if it closed where the previous bar did.
For bar 4: bar 3 closed at 104, and `102.5 + 0.5 × (104 - 102.5) = 103.25`, the PriceHold value.
The tests check this identity on random data for several periods.
