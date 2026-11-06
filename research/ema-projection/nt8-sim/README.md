# NinjaTrader 8 Simulation

Compiles the indicators in [NinjaTrader/Indicators](../../../NinjaTrader/Indicators) unmodified
(their "NinjaScript generated code" regions included) against a small stand-in for NinjaTrader 8,
replays the bars the backtest uses through them, and checks every plotted value against the
backtest's Python formulas. This gives a way to check the C# without NinjaTrader.

## Running It

Setup on Fedora: `sudo dnf install dotnet-sdk-8.0`. Then, from `research/ema-projection`:

```sh
python3 fetch.py                                             # the bars, if data/ is empty
dotnet run --project nt8-sim -- data nt8-sim/out             # replays them; optional third argument: Period (default 14)
python3 nt8-sim/compare.py                                   # compares; pass the same Period if you changed it
```

The runner writes one CSV per series and projection method (`out/<series>_<method>.csv`) with each
plot's value on every bar, empty where the indicator left it unset, and prints how many times an
indicator read a value that was never set. `compare.py` checks that each plot is set on exactly
the bars where the Python port has a value and that the values agree within 1e-9. It exits
non-zero on any difference.

## What Is Simulated

`Stubs/` holds the parts of NinjaTrader 8 the indicators use:

- **The indicator life cycle.** Creating an indicator runs `OnStateChange` in `State.SetDefaults`,
  so the object initializers in the generated factory methods override the defaults. Attaching it
  to bars runs `State.Configure`, then `State.DataLoaded`. An indicator created by another, through
  the generated factory methods and `CacheIndicator`, shares its parent's bars and input, and it
  updates before its parent on every bar.
- **Bar-by-bar replay.** Each bar runs `OnBarUpdate` once, as historical bars do (and as
  `Calculate.OnBarClose` does in real time); the `Calculate.OnPriceChange` the indicators ask for
  makes no difference to finished bars.
- **Series.** `Close`/`Input`, the plots in `Values` and the indicators themselves index by bars
  ago (`[0]` is the bar being processed). Reaching before the first bar throws, as in NinjaTrader.
  `IsValidDataPoint(barsAgo)` reports whether a plot was set on a bar. A value never set reads as
  NaN and is counted, so the run shows any read of a value that was never set.
- **The built-in `EMA` and `SMA`**, as NinjaTrader 8 defines them. The EMA is seeded with the first
  value and uses `k = 2 / (Period + 1)`. The SMA keeps a running sum and averages the bars so far
  until there are `Period` of them; this is its path for time-based bars, the ones Yahoo's 30-minute,
  1-hour and daily bars are.
- **Everything else** is a placeholder for compiling: brushes, strokes, plot styles,
  the attribute and resource types, and the market analyzer and strategy base classes the
  generated regions extend.

## Last Run

ES=F and SPY, 30-minute, 1-hour and daily bars, Period 14, both projection methods: all 120
comparisons agree exactly (largest difference 0), with no set/unset mismatches and no reads of
unset values. Periods 1, 2, 9 and 50 also agree exactly.
