# NinjaTrader

Everything in this directory is related to the NinjaTrader (NT) platform. Specifically, everything as of the date of
this writing is for NinjaTrader 8.1.2.4 (NT8) or later. Some of the code may run on earlier versions of NT8, but none
of this code has been tested on those earlier versions.

## Layout and Usage

The directory layout follows that of NT8. To make use of any of the code here, just copy it directly into your NT8
code folder and reference it from your `NinjaTrader.Custom.csproj` project file. For now, only a set of `Indicators`
exist.

## Indicators

### EMA Projection

`EMAProjection` plots the EMA of `Period` bars and a projection of that EMA one bar ahead. The
projection on each bar uses closed bars only, so comparing it with the EMA the bar ends on shows
how good the forecast was. `Projection Method` picks how the projection is made, with
`k = 2 / (Period + 1)`, the EMA's own weight:

- `PriceHold` (default): the EMA this bar gives if it closes where the last bar closed,
  `ema[1] + k * (Close[1] - ema[1])`, computed as `ema[1] + (1 - k) * (ema[1] - ema[2])`.
- `AverageSlope`: the EMA's average change per bar over the last `Period` bars added to the last
  value, `ema[1] + (ema[1] - ema[Period + 1]) / Period`.

`PriceHold` is the default because it had the smallest error in a backtest on ES futures and SPY
(30-minute, 1-hour and daily bars, Periods 9 to 50, measured on held-out data): 2 to 5% less at Period 14
than repeating the last bar's EMA change and roughly half of `AverageSlope`'s, which also points
the wrong way more often and takes several bars to follow a turn. The backtest, its data sources
and full results are in [research/ema-projection](../research/ema-projection/README.md).

`EMAProjectionTrend` plots how much the projection rose or fell since the last bar, and
`EMAProjectionError` the difference between the projection and the EMA it was projecting. Both
take the same `Period` and `Projection Method`.

### SMA Projection

`SMAProjection` plots the SMA of `Period` bars and `sma[1] + (sma[1] - sma[Period + 1]) / Period`,
the SMA's average change per bar over the last `Period` bars added to its last value.
`SMAProjectionTrend` plots how much that projection rose or fell since the last bar.
