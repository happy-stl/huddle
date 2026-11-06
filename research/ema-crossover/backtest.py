"""Backtest crossover strategies traded on the actual EMA against the same rules one bar early on
the EMA Projection.

Usage: python3 ../ema-projection/fetch.py && python3 backtest.py   (writes RESULTS.md)

Each series is split in time: the parameter (EMA period, or fast/slow pair) of each strategy family
and mode is chosen by the actual-EMA rule's after-cost net P&L on the first 60%, and the early rule
uses the same parameter, so the two differ only in acting a bar early. Everything reported is the
held-out last 40%.
"""

import csv
import datetime as dt
import math
import os
import random
import statistics
import zlib

import strategies as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "ema-projection", "data")

SERIES = [
    ("ES=F", "30m", "ESF_30m.csv", st.ES),
    ("ES=F", "1h", "ESF_1h.csv", st.ES),
    ("ES=F", "1d", "ESF_1d.csv", st.ES),
    ("SPY", "30m", "SPY_30m.csv", st.SPY),
    ("SPY", "1h", "SPY_1h.csv", st.SPY),
    ("SPY", "1d", "SPY_1d.csv", st.SPY),
]
TRAIN_SHARE = 0.6
WARMUP = 110  # bars before any decision: more than twice the longest EMA
PERIODS = [5, 9, 14, 21, 34, 50]
PAIRS = [(5, 20), (9, 21), (14, 50), (20, 50)]
RANDOM_SEEDS = 1000
BOOTSTRAP = 2000
BLOCK = 20  # bars per bootstrap block, to keep short-run dependence
MODES = [("long/short", False), ("long/flat", True)]

METHODS = [("PriceHold", st.PRICE_HOLD), ("AverageSlope", st.AVERAGE_SLOPE)]

# Written from the tables this script produces on the data fetched 2026-11-06; rerun and reread it if the data changes.
VERDICT = [
    "## Verdict",
    "",
    "Acting a bar early on the EMA Projection does not make or save money consistently, after costs or before.",
    "",
    "- **Single-EMA rules (EMA direction, price/EMA cross): PriceHold's early signal is the actual signal.**",
    "  `close - ema[i] = (1 - k)(close - ema[i-1])`, and PriceHold projects the next change as `k (close - ema[i])`,",
    "  so the EMA's direction, the price/EMA cross and both early versions agree on every bar. The projection",
    "  never calls a turn before the EMA makes it: its 82-86% direction hit rate is the EMA continuing the way",
    "  it is already going.",
    "- **Fast/slow crosses, early on PriceHold:** better on 2 series, worse on 4, in both modes. The one",
    "  significant gain (ES=F 1h, p < 0.01) comes from the actual 5/20 cross losing heavily in that stretch;",
    "  on SPY 30m and 1h the early cross lost more, and on the daily series the differences are small and",
    "  nowhere near significant.",
    "- **Early on AverageSlope** (the original projection): worse than acting on the EMA in most cases",
    "  (EMA direction 2 better / 4 worse, price/EMA cross 1 / 5, fast/slow 2 / 4).",
    "- **Noise:** 48 early-vs-actual comparisons are not identical. 7 reach p < 0.05, all in the early rule's",
    "  favour and all on ES=F, but they are 3 events counted in correlated pairs (long/short and long/flat of",
    "  the same signal; PriceHold and AverageSlope on the same series): the ES=F 1h and 30m fast/slow crosses",
    "  and the ES=F daily price/EMA cross on AverageSlope. About 2.4 false positives are expected from 48 tests",
    "  at 5%. None of it carries over to SPY, which tracks the same index, so it is not a usable edge.",
    "- **The crossover rules themselves show no edge:** every rule's net P&L sits between the 2nd and 82nd",
    "  percentile of random entries with the same number of trades, never above the 95th. On the daily",
    "  series, buy and hold beat every rule.",
    "",
]

# family -> (parameter grid, actual signal(closes, param), early signal(closes, param, method))
FAMILIES = {
    "EMA direction": (PERIODS, lambda c, p: st.ema_direction(c, p), lambda c, p, m: st.ema_direction_early(c, p, m)),
    "Price/EMA cross": (PERIODS, lambda c, p: st.price_cross(c, p), lambda c, p, m: st.price_cross_early(c, p, m)),
    "Fast/slow EMA cross": (PAIRS, lambda c, p: st.ema_cross(c, *p), lambda c, p, m: st.ema_cross_early(c, p[0], p[1], m)),
}


def load(name):
    with open(os.path.join(DATA, name)) as f:
        rows = list(csv.DictReader(f))
    times = [dt.datetime.fromisoformat(r["time"]) for r in rows]
    return times, [float(r["open"]) for r in rows], [float(r["close"]) for r in rows]


def windows(n):
    split = WARMUP + int(TRAIN_SHARE * (n - WARMUP))
    # Train decisions: bars WARMUP..split-2 (the last is closed at the open of bar split).
    # Test decisions: bars split..n-3 (the last is closed at the open of bar n-1).
    return (WARMUP, split - 1), (split, n - 2)


def metrics(pnl, trades, decisions, opens, lo, market, bars_per_year):
    notional = opens[lo + 1] * market.multiplier
    net = sum(pnl)
    equity, peak, mdd = 0.0, 0.0, 0.0
    for x in pnl:
        equity += x
        peak = max(peak, equity)
        mdd = max(mdd, peak - equity)
    rets = [x / (opens[lo + k + 1] * market.multiplier) for k, x in enumerate(pnl)]
    sd = statistics.pstdev(rets)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    return {
        "net": net,
        "ret": net / notional,
        "trades": len(trades),
        "win": len(wins) / len(trades) if trades else math.nan,
        "avg": net / len(trades) if trades else math.nan,
        "pf": sum(wins) / -sum(losses) if losses else math.inf,
        "mdd": mdd,
        "sharpe": statistics.fmean(rets) / sd * math.sqrt(bars_per_year) if sd > 0 else math.nan,
        "exposure": sum(1 for d in decisions if d != 0) / len(decisions),
    }


def evaluate(decisions, opens, lo, market, bars_per_year):
    pnl, trades = st.run(opens, decisions, lo, market, costs=True)
    gross, _ = st.run(opens, decisions, lo, market, costs=False)
    m = metrics(pnl, trades, decisions, opens, lo, market, bars_per_year)
    g = metrics(gross, [], decisions, opens, lo, market, bars_per_year)
    m["gross"], m["gross_sharpe"] = g["net"], g["sharpe"]
    return m, pnl, gross


def random_entry(opens, lo, n_dec, k, long_only, market, rng):
    """Net P&L after costs of a strategy with k position changes at random bars, alternating sides."""
    if k == 0:
        return 0.0
    k = min(k, n_dec)
    side = market.cost_per_side
    m = market.multiplier
    times = sorted(rng.sample(range(n_dec), k)) + [n_dec]
    pos = 1 if long_only else rng.choice((1, -1))
    total, prev = 0.0, 0
    for j in range(k):
        a, b = times[j], times[j + 1]
        total -= abs(pos - prev) * side
        total += pos * (opens[lo + b + 1] - opens[lo + a + 1]) * m
        prev = pos
        pos = (0 if pos else 1) if long_only else -pos
    total -= abs(prev) * side
    return total


def percentile(value, sample):
    return sum(1 for s in sample if s < value) / len(sample)


def block_bootstrap(diff, rng):
    """Circular block bootstrap of the summed per-bar difference: 95% interval and two-sided p for 0."""
    n = len(diff)
    prefix = [0.0]
    for x in diff + diff[:BLOCK]:
        prefix.append(prefix[-1] + x)
    blocks = math.ceil(n / BLOCK)
    sums = []
    for _ in range(BOOTSTRAP):
        total = 0.0
        for _ in range(blocks):
            s = rng.randrange(n)
            total += prefix[s + BLOCK] - prefix[s]
        sums.append(total * n / (blocks * BLOCK))
    sums.sort()
    lo, hi = sums[int(0.025 * BOOTSTRAP)], sums[int(0.975 * BOOTSTRAP) - 1]
    below = sum(1 for s in sums if s <= 0) / BOOTSTRAP
    above = sum(1 for s in sums if s >= 0) / BOOTSTRAP
    return lo, hi, min(1.0, 2 * min(below, above))


def run_series(symbol, interval, fname, market):
    times, opens, closes = load(fname)
    n = len(closes)
    (tr_lo, tr_hi), (te_lo, te_hi) = windows(n)
    years = (times[te_hi] - times[te_lo + 1]).total_seconds() / (365.25 * 86400)
    bpy = (te_hi - te_lo) / years
    tr_years = (times[tr_hi] - times[tr_lo + 1]).total_seconds() / (365.25 * 86400)
    tr_bpy = (tr_hi - tr_lo) / tr_years
    rng = random.Random(zlib.crc32((symbol + interval).encode()))
    rows, diffs = [], []

    hold = [1] * (te_hi - te_lo)
    m, _, _ = evaluate(hold, opens, te_lo, market, bpy)
    rows.append(("Buy and hold", "", "long", "", m, None))

    cache = {}

    def signal(family, param, method_name):
        key = (family, param, method_name)
        if key not in cache:
            grid, actual, early = FAMILIES[family]
            method = dict(METHODS).get(method_name)
            cache[key] = actual(closes, param) if method is None else early(closes, param, method)
        return cache[key]

    for family, (grid, _, _) in FAMILIES.items():
        for mode, long_only in MODES:
            best = None
            for param in grid:
                dec = st.positions(signal(family, param, None), tr_lo, tr_hi, long_only)
                net = sum(st.run(opens, dec, tr_lo, market)[0])
                if best is None or net > best[0]:
                    best = (net, param)
            param = best[1]
            label = "{}/{}".format(*param) if isinstance(param, tuple) else str(param)
            base = None
            for method_name in [None] + [name for name, _ in METHODS]:
                dec = st.positions(signal(family, param, method_name), te_lo, te_hi, long_only)
                m, pnl, gross = evaluate(dec, opens, te_lo, market, bpy)
                k = st.changes(dec)
                # The same seed for the same trade count, so identical strategies get identical samples.
                r = random.Random(zlib.crc32("{}{}{}{}".format(symbol, interval, k, long_only).encode()))
                sample = [random_entry(opens, te_lo, len(dec), k, long_only, market, r) for _ in range(RANDOM_SEEDS)]
                m["random_pct"] = percentile(m["net"], sample)
                variant = "actual EMA" if method_name is None else "early, " + method_name
                rows.append((family, variant, mode, label, m, None))
                if method_name is None:
                    base = (m, pnl, gross, dec)
                else:
                    same = dec == base[3]
                    d = [a - b for a, b in zip(pnl, base[1])]
                    lo, hi, p = (0.0, 0.0, 1.0) if same else block_bootstrap(d, rng)
                    diffs.append({
                        "family": family, "method": method_name, "mode": mode, "param": label,
                        "dnet": m["net"] - base[0]["net"], "dgross": m["gross"] - base[0]["gross"],
                        "dsharpe": m["sharpe"] - base[0]["sharpe"], "lo": lo, "hi": hi, "p": p,
                        "dtrades": m["trades"] - base[0]["trades"], "same": same,
                    })
    info = {
        "bars": n, "from": times[0], "to": times[-1], "test_from": times[te_lo + 1], "test_bars": te_hi - te_lo,
        "bpy": bpy, "notional": opens[te_lo + 1] * market.multiplier,
    }
    return rows, diffs, info


def money(x):
    return "{:,.0f}".format(x) if abs(x) >= 100 else "{:,.2f}".format(x)


def fmt(x, spec):
    if isinstance(x, float) and (math.isnan(x)):
        return "-"
    if x == math.inf:
        return "inf"
    return spec.format(x)


def main():
    out = [
        "# EMA Crossover Backtest Results",
        "",
        "Generated by `backtest.py`; see README.md for the rules, costs and method, and its verdict.",
        "All numbers are on the held-out last {:.0%} of each series. Money is in dollars for one ES contract".format(1 - TRAIN_SHARE),
        "($50 a point) or one SPY share. *After costs* includes commission and one tick of slippage per side.",
        "",
    ] + VERDICT
    all_diffs = []
    for symbol, interval, fname, market in SERIES:
        rows, diffs, info = run_series(symbol, interval, fname, market)
        all_diffs += [dict(d, series="{} {}".format(symbol, interval)) for d in diffs]
        out += [
            "## {} {}".format(symbol, interval),
            "",
            "{} bars from {} to {}; held out: {} decisions from {} ({:.0f} bars a year). Return is net P&L over the notional"
            " at the start of the held-out part, ${}.".format(
                info["bars"], info["from"].date(), info["to"].date(), info["test_bars"], info["test_from"].strftime("%Y-%m-%d %H:%M"),
                info["bpy"], money(info["notional"])),
            "",
            "| Strategy | Signal | Mode | Param | Net P&L | Return | Trades | Win | Avg trade | PF | Max DD | Sharpe | Exposure | Gross P&L | Gross Sharpe | Random pctile |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for family, variant, mode, label, m, _ in rows:
            out.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                family, variant, mode, label, money(m["net"]), fmt(m["ret"], "{:.1%}"), m["trades"], fmt(m["win"], "{:.0%}"),
                fmt(m["avg"], "{:,.2f}"), fmt(m["pf"], "{:.2f}"), money(m["mdd"]), fmt(m["sharpe"], "{:.2f}"),
                fmt(m["exposure"], "{:.0%}"), money(m["gross"]), fmt(m["gross_sharpe"], "{:.2f}"),
                fmt(m.get("random_pct", math.nan), "{:.0%}")))
        out.append("")

    out += [
        "## Early Minus Actual, After Costs",
        "",
        "The early rule's held-out net P&L minus the actual-EMA rule's, same parameter. The interval and p",
        "come from a circular block bootstrap ({} resamples, {}-bar blocks) of the per-bar P&L difference;".format(BOOTSTRAP, BLOCK),
        "p is two-sided for a difference of zero. *Identical* marks rules that make the same decision on every bar.",
        "",
        "| Series | Strategy | Early on | Mode | Param | Net P&L difference | 95% interval | p | Gross difference | Sharpe difference | Trades difference |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for d in all_diffs:
        out.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {:+d} |".format(
            d["series"], d["family"], d["method"], d["mode"], d["param"],
            "identical" if d["same"] else money(d["dnet"]),
            "" if d["same"] else "{} to {}".format(money(d["lo"]), money(d["hi"])),
            "" if d["same"] else "{:.2f}".format(d["p"]),
            "" if d["same"] else money(d["dgross"]),
            "" if d["same"] else fmt(d["dsharpe"], "{:+.2f}"), d["dtrades"]))
    out.append("")

    out += [
        "## Tally",
        "",
        "Of the six series, how often the early rule's after-cost net P&L beat the actual rule's, and how often",
        "the difference was significant at p < 0.05 (in either direction).",
        "",
        "| Strategy | Early on | Mode | Early better | Early worse | Identical | Significant (better / worse) |",
        "|---|---|---|---|---|---|---|",
    ]
    keys = []
    for d in all_diffs:
        k = (d["family"], d["method"], d["mode"])
        if k not in keys:
            keys.append(k)
    for k in keys:
        ds = [d for d in all_diffs if (d["family"], d["method"], d["mode"]) == k]
        better = sum(1 for d in ds if not d["same"] and d["dnet"] > 0)
        worse = sum(1 for d in ds if not d["same"] and d["dnet"] < 0)
        same = sum(1 for d in ds if d["same"])
        sb = sum(1 for d in ds if not d["same"] and d["p"] < 0.05 and d["dnet"] > 0)
        sw = sum(1 for d in ds if not d["same"] and d["p"] < 0.05 and d["dnet"] < 0)
        out.append("| {} | {} | {} | {} | {} | {} | {} / {} |".format(*k, better, worse, same, sb, sw))
    out.append("")

    with open(os.path.join(HERE, "RESULTS.md"), "w") as f:
        f.write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
