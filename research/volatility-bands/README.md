# Volatility Forecast and Price-Range Bands

Can a volatility forecast beat simple historical volatility at predicting the size of the next bar's
move? And do bands built from it hold their stated coverage while staying narrower than a fixed band?
Tested on ES futures and SPY, 30-minute, 1-hour and daily bars.

## Pre-Registered Criteria

This section was committed before any held-out result was computed, and it is not edited afterwards.
The results and verdicts are in [RESULTS.md](RESULTS.md).

### Data

The bars `../ema-projection/fetch.py` downloaded on 2026-11-06, used as they are: no rolls adjusted,
no bars removed.

| File | Bars | First bar (UTC) | Last bar (UTC) | SHA-256 (first 16) |
|---|---|---|---|---|
| ESF_30m.csv | 2,254 | 2026-08-28 04:00 | 2026-11-06 08:00 | 037e19eb39828bce |
| ESF_1h.csv | 13,695 | 2024-06-16 22:00 | 2026-11-06 08:00 | e7855bdc6f864036 |
| ESF_1d.csv | 6,599 | 2000-09-18 04:00 | 2026-11-05 05:00 | 904f43b29bd11319 |
| SPY_30m.csv | 780 | 2026-08-13 13:30 | 2026-11-05 20:30 | 6c61088cbdc1757f |
| SPY_1h.csv | 5,082 | 2023-12-08 14:30 | 2026-11-05 20:30 | 31a0109e90ca52d5 |
| SPY_1d.csv | 8,500 | 1993-01-29 14:30 | 2026-11-04 14:30 | b1da05f73619693f |

### Setup

- **Returns:** close-to-close log returns, `r[t] = ln(close[t] / close[t-1])`. Session gaps (overnight,
  weekends, ES's daily halt) stay in the return of the first bar after them.
- **Forecast:** at the close of bar t, a variance forecast `h[t+1]` for the return of bar t+1, using
  bars up to t. The only thing known about bar t+1 is its scheduled time of day.
- **Primary target:** the squared next-bar return `r[t+1]^2`. It is an unbiased proxy for the
  conditional variance and exists on every series, daily included. With an unbiased proxy, QLIKE and MSE
  rank forecasts the same way the true variance would (Patton, 2011). A range-based (Parkinson) proxy
  would be less noisy intraday but is not comparable across the gaps; it is not used.
- **Split:** the first 250 bars are warm-up. Of the forecasts after them, the first 60% are training and
  the last 40% held out. `D`, the HAR's day window, is the median number of bars per trading date (exchange
  local time) in the first 60% of the series. It is 46, 23, 13 and 7 for ES 30m, ES 1h, SPY 30m and SPY 1h,
  so the longest window, `5D = 230`, fits in the warm-up. Everything fitted or chosen (coefficients, the
  windows N and lambda, quantile multipliers, the time-of-day profile, which model and which baseline)
  uses the training part only.
- **Time-of-day profile (intraday only):** `s(slot)` is the training mean of `r^2` in each time-of-day
  slot, divided by the overall training mean. The slot is the bar's start time in the exchange's local
  time (America/Chicago for ES, America/New_York for SPY, so daylight saving does not move it). A slot not
  seen in training gets `s = 1`. With the profile, every model and baseline runs on deseasonalized
  returns `r / sqrt(s(slot))`, and its forecast is multiplied by `s(slot of bar t+1)`. **Primary** for the
  criteria: with the profile on intraday series, and with none on daily series. Results without the
  profile are reported alongside.
- **Floor:** a forecast below 1% of the training mean of the (deseasonalized) `r^2` is raised to it.

### Models and Baselines

- **HAR** (bar-level): `h[t+1] = b0 + b1 r[t]^2 + b2 mean(r^2 over the last D bars) + b3 mean(r^2
  over the last 5D bars)`, fitted by ordinary least squares on training. On daily bars the windows are 1,
  5 and 22.
- **GARCH(1,1)**: `h[t+1] = omega + alpha r[t]^2 + beta h[t]`, zero mean, with `h` at the first training
  bar set to the training variance. It is fitted by Gaussian maximum likelihood on training (Nelder-Mead,
  `omega > 0`, `alpha, beta >= 0`, `alpha + beta < 1`).
- **Rolling historical variance:** the mean of `r^2` over the last N bars, with N in {5, 10, 20, 50,
  100, 250} chosen on training.
- **EWMA:** `h[t+1] = lambda h[t] + (1 - lambda) r[t]^2`, with lambda = 0.94 (RiskMetrics) and lambda in
  {0.80, 0.85, 0.90, 0.94, 0.97, 0.98, 0.99, 0.995} chosen on training. Started from the mean `r^2` of
  the warm-up.

### Losses

- **QLIKE** (primary): `ln h + r^2 / h`. This is Patton's QLIKE less a term that does not depend on the
  forecast, so it stays defined when a bar's return is zero.
- **MSE:** `(r^2 - h)^2`.
- **Diebold-Mariano:** the loss difference model minus baseline, with a Newey-West (Bartlett) variance
  using `floor(4 (T/100)^(2/9))` lags. Two-sided normal p.

### Criterion 1: The Volatility Forecast

On each series, the **best model** is whichever of HAR and GARCH has the lower training QLIKE. The
**best baseline** is whichever of rolling (tuned N), EWMA 0.94 and EWMA (tuned lambda) has the lower
training QLIKE. A series **passes** if the best model's mean QLIKE on the held-out part is lower than the
best baseline's. The Diebold-Mariano statistic and p are reported for every series but are not part of
the pass rule. **Criterion 1 passes if at least 5 of the 6 series pass.** Also reported: the held-out QLIKE
and MSE of every model and baseline.

### Criterion 2: The Range Bands

- **Band:** the next close, `close[t+1]`, is forecast to lie in `[close[t] exp(q_lo sqrt(h[t+1])),
  close[t] exp(q_hi sqrt(h[t+1]))]`. `h` comes from Criterion 1's best model for that series, primary
  variant. `q_lo` and `q_hi` are the empirical `(1 - c)/2` and `(1 + c)/2` quantiles of the training
  standardized returns `r[t+1] / sqrt(h[t+1])`, for nominal coverage c = 80% and 95%.
- **Fixed band:** `[close[t] exp(f_lo), close[t] exp(f_hi)]`, where `f_lo` and `f_hi` are the same
  quantiles of the training returns themselves.
- **Reported, held out:** coverage, the share of bars where `close[t+1]` falls inside, with Kupiec's
  unconditional-coverage test; Christoffersen's independence test and conditional-coverage test (whether
  misses cluster); and the mean width `(upper - lower) / close[t]`.
- **Coverage condition, per series and level:** held-out coverage within ±2.5 percentage points of
  nominal.
- **Width condition, per series and level:** the volatility band's mean width is smaller than the
  fixed band's, and its coverage is at least the fixed band's coverage minus 1.0 percentage point.
- **Criterion 2 passes if, at both 80% and 95%, the coverage condition holds on at least 5 of 6 series
  and the width condition holds on at least 5 of 6 series.**

### What Follows

Only if both criteria pass is a NinjaTrader indicator built from the model, together with a chart for
the website. A failure is reported as a failure.

## Results

Run after the criteria above were committed. Tables are in [RESULTS.md](RESULTS.md).

- **Criterion 1 (volatility forecast): PASS**, 5 of 6. GARCH(1,1) beat the best baseline on ES=F 1h and daily and
  on SPY 30m, 1h and daily, but the difference is significant only on the daily series.
- **Criterion 2 (range bands): FAIL.** At 80% the volatility band was wider than the fixed band on all 6
  series; at 95% it was narrower at no worse coverage on 3. Coverage was within 2.5 points of nominal on 4 of
  6 at each level.

So no NinjaTrader indicator was built.

## Running It

Python 3.9 or later, standard library only.

```sh
python3 ../ema-projection/fetch.py   # the data; check the SHA-256 values above match
python3 backtest.py                  # writes RESULTS.md (a few seconds)
python3 -m unittest test_vol         # no-lookahead and formula checks
```
