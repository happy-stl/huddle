"""Backtest the EMA projections: how well each one forecasts the next bar's EMA.

Usage: python3 fetch.py && python3 backtest.py   (writes RESULTS.md)

Each series is split in time: parameters are chosen on the first 60% (by mean absolute error)
and every number in the tables is measured on the last 40%, which the choice never saw.
"""

import csv
import math
import os
import statistics

import projection as pj

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SERIES = [
    ("ES=F", "30m", "ESF_30m.csv"),
    ("ES=F", "1h", "ESF_1h.csv"),
    ("ES=F", "1d", "ESF_1d.csv"),
    ("SPY", "30m", "SPY_30m.csv"),
    ("SPY", "1h", "SPY_1h.csv"),
    ("SPY", "1d", "SPY_1d.csv"),
]
MAIN_PERIOD = 14
OTHER_PERIODS = [9, 21, 50]
TRAIN_SHARE = 0.6
MIN_RUN = 3

# name -> (function(closes, period, *params), list of parameter tuples; [()] means none)
METHODS = {
    "A: no change": (lambda c, p: pj.no_change(c, p), [()]),
    "B: last-bar slope": (lambda c, p: pj.span_slope(c, p, 1), [()]),
    "AverageSlope, before fix (/(P-1))": (lambda c, p: pj.average_slope_original(c, p), [()]),
    "AverageSlope (/P)": (lambda c, p: pj.average_slope(c, p), [()]),
    "Span-2 slope": (lambda c, p: pj.span_slope(c, p, 2), [()]),
    "Span-3 slope": (lambda c, p: pj.span_slope(c, p, 3), [()]),
    "Span-5 slope": (lambda c, p: pj.span_slope(c, p, 5), [()]),
    "EW slope = Holt, EMA level (beta tuned)": (
        lambda c, p, b: pj.ew_slope(c, p, b),
        [(b,) for b in (0.1, 0.2, 0.3, 0.5, 0.7, 0.9)],
    ),
    "Holt on price (alpha, beta tuned)": (
        lambda c, p, a, b: pj.holt_price(c, p, a, b),
        [(a, b) for a in (0.2, 0.4, 0.6, 0.8, 0.9, 1.0) for b in (0.0, 0.02, 0.05, 0.1, 0.2, 0.4)],
    ),
    "Damped last-bar slope (phi tuned)": (
        lambda c, p, f: pj.damped_slope(c, p, f),
        [(round(0.05 * i, 2),) for i in range(0, 25)],
    ),
    "PriceHold: ema1 + (1-k)(ema1-ema2)": (lambda c, p: pj.price_hold(c, p), [()]),
}


def load(name):
    with open(os.path.join(DATA, name)) as f:
        rows = list(csv.DictReader(f))
    return [r["time"] for r in rows], [float(r["close"]) for r in rows]


def sign(x):
    return (x > 0) - (x < 0)


def bounds(n, period):
    start = max(2 * period + 2, 30)
    split = start + int(TRAIN_SHARE * (n - start))
    return start, split


def mae(e, p, lo, hi):
    return sum(abs(p[t] - e[t]) for t in range(lo, hi)) / (hi - lo)


def metrics(e, p, lo, hi):
    errs = [p[t] - e[t] for t in range(lo, hi)]
    hits = total = 0
    for t in range(lo, hi):
        actual = sign(e[t] - e[t - 1])
        if actual == 0:
            continue
        total += 1
        hits += sign(p[t] - e[t - 1]) == actual
    return {
        "mae": sum(abs(x) for x in errs) / len(errs),
        "rmse": math.sqrt(sum(x * x for x in errs) / len(errs)),
        "hit": hits / total,
        **turn_lags(e, p, lo, hi),
    }


def turn_lags(e, p, lo, hi):
    """Bars from each lasting EMA turn until the projection points the new way.

    A turn is a bar t whose EMA change has the opposite sign of the last non-zero change; it lasts
    when the EMA keeps the new direction for at least MIN_RUN bars (one- and two-bar wiggles are
    over before any forecast from earlier bars could follow them, so they are left out).
    Lag 0: the projection made for bar t already pointed the new way; lag 1: the one for t+1; ...
    A lasting turn the projection never follows before the EMA turns again counts as missed.
    """
    a = [sign(e[t] - e[t - 1]) for t in range(len(e))]
    turns, last = [], 0
    for t in range(1, hi):
        if a[t] == 0:
            continue
        if last and a[t] != last and t >= lo:
            turns.append(t)
        last = a[t]
    lags = []
    for i, t in enumerate(turns):
        end = turns[i + 1] if i + 1 < len(turns) else hi
        lag = math.inf
        for s in range(t, end):
            if sign(p[s] - e[s - 1]) == a[t]:
                lag = s - t
                break
        if end - t >= MIN_RUN:
            lags.append(lag)
    caught = [x for x in lags if x != math.inf]
    srt = sorted(lags)
    return {
        "turns": len(lags),
        "lag_median": statistics.median(srt) if srt else math.nan,
        "lag_max": max(caught) if caught else math.nan,
        "missed": 1 - len(caught) / len(lags) if lags else math.nan,
    }


def tune(fn, grid, closes, period, e, lo, hi):
    best = None
    for params in grid:
        p = fn(closes, period, *params)
        score = mae(e, p, lo, hi)
        if best is None or score < best[0]:
            best = (score, params, p)
    return best[1], best[2]


def evaluate(closes, period):
    e = pj.ema(closes, period)
    start, split = bounds(len(closes), period)
    out = {}
    for name, (fn, grid) in METHODS.items():
        params, p = tune(fn, grid, closes, period, e, start, split)
        out[name] = (params, metrics(e, p, split, len(closes)))
    return out, (start, split)


def fmt_lag(x):
    if x == math.inf:
        return "never"
    if isinstance(x, float) and math.isnan(x):
        return "-"
    return "{:g}".format(x)


def fmt_params(params):
    return ", ".join("{:g}".format(v) for v in params) if params else ""


def main():
    lines = [
        "# EMA Projection Backtest Results",
        "",
        "Generated by `backtest.py` from Yahoo Finance bars downloaded by `fetch.py`.",
        "Each projection forecasts the EMA of bar t from data up to bar t-1.",
        "Parameters (where a method has any) were chosen by mean absolute error on the first {:.0%} of each series;".format(TRAIN_SHARE),
        "every number below is measured on the held-out last {:.0%}.".format(1 - TRAIN_SHARE),
        "",
        "Columns: MAE and RMSE in price points; *vs B* is MAE relative to baseline B (below 1 is better);",
        "*Hit* is the share of bars where the projection's direction (projection - ema1) matched the EMA's real change;",
        "*Lag* is bars from an EMA turn that lasts at least {} bars until the projection points the new way".format(MIN_RUN),
        "(0 = already there; median and largest), and *Missed* the share of those turns the projection never",
        "followed before the EMA turned again (missed turns sort last in the median).",
        "",
    ]
    data = {}
    for symbol, interval, fname in SERIES:
        times, closes = load(fname)
        data[(symbol, interval)] = (times, closes)

    summary = {}
    for (symbol, interval), (times, closes) in data.items():
        res, (start, split) = evaluate(closes, MAIN_PERIOD)
        b = res["B: last-bar slope"][1]["mae"]
        lines += [
            "## {} {} bars, Period {}".format(symbol, interval, MAIN_PERIOD),
            "",
            "{} bars from {} to {}; held out: {} bars from {}.".format(
                len(closes), times[0][:10], times[-1][:10], len(closes) - split, times[split][:16]
            ),
            "",
            "| Method | Chosen | MAE | RMSE | vs B | Hit | Lag median | Lag max | Missed |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for name, (params, m) in res.items():
            lines.append(
                "| {} | {} | {:.4g} | {:.4g} | {:.3f} | {:.1%} | {} | {} | {:.0%} |".format(
                    name, fmt_params(params), m["mae"], m["rmse"], m["mae"] / b, m["hit"],
                    fmt_lag(m["lag_median"]), fmt_lag(m["lag_max"]), m["missed"],
                )
            )
            summary.setdefault(name, {})[(symbol, interval, MAIN_PERIOD)] = m["mae"] / b
        lines.append("")

    for period in OTHER_PERIODS:
        for (symbol, interval), (times, closes) in data.items():
            res, _ = evaluate(closes, period)
            b = res["B: last-bar slope"][1]["mae"]
            for name, (params, m) in res.items():
                summary[name][(symbol, interval, period)] = m["mae"] / b

    keys = [(s, i, p) for p in [MAIN_PERIOD] + OTHER_PERIODS for (s, i) in data]
    lines += [
        "## Every Series and Period: Held-Out MAE Relative to Baseline B",
        "",
        "Below 1 beats the last-bar slope. *Wins* counts the {} series-and-period cases where it does.".format(len(keys)),
        "",
        "| Method | " + " | ".join("{} {} P{}".format(s, i, p) for s, i, p in keys) + " | Wins |",
        "|---|" + "---|" * (len(keys) + 1),
    ]
    for name, vals in summary.items():
        wins = sum(vals[k] < 1 for k in keys)
        lines.append("| {} | ".format(name) + " | ".join("{:.4f}".format(vals[k]) for k in keys) + " | {} |".format(wins))
    lines.append("")

    times, closes = data[("ES=F", "30m")]
    n = len(closes)
    lo = n - 170
    e = pj.ema(closes, MAIN_PERIOD)
    lines += [
        "## Check: the Last 170 ES=F 30-Minute Bars, Period 14",
        "",
        "Bars {} to {}.".format(times[lo][:16], times[-1][:16]),
        "",
        "| Method | MAE | Hit | Lag median | Lag max | Missed |",
        "|---|---|---|---|---|---|",
    ]
    for name in ["B: last-bar slope", "AverageSlope, before fix (/(P-1))", "AverageSlope (/P)", "PriceHold: ema1 + (1-k)(ema1-ema2)"]:
        fn = METHODS[name][0]
        m = metrics(e, fn(closes, MAIN_PERIOD), lo, n)
        lines.append("| {} | {:.3f} | {:.1%} | {} | {} | {:.0%} |".format(
            name, m["mae"], m["hit"], fmt_lag(m["lag_median"]), fmt_lag(m["lag_max"]), m["missed"]))
    lines.append("")

    with open(os.path.join(HERE, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
