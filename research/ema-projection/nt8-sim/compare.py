"""Compares the simulated NinjaTrader plots (nt8-sim/out/*.csv) with the Python backtest's formulas.

Usage: python3 nt8-sim/compare.py [period]   (after the runner has written nt8-sim/out/)

For every bar it checks that each plot is set exactly where the Python port has a value, and
reports the largest absolute difference per series, method and plot (it fails above 1e-9).
"""

import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import projection as pj  # noqa: E402

TOLERANCE = 1e-9
METHODS = {"PriceHold": pj.price_hold, "AverageSlope": pj.average_slope}


def trend(p):
    up, down = [None] * len(p), [None] * len(p)
    for t in range(1, len(p)):
        if p[t] is not None and p[t - 1] is not None:
            d = p[t] - p[t - 1]
            up[t] = d if d > 0 else 0
            down[t] = d if d < 0 else 0
    return up, down


def error(p, e):
    pos, neg = [None] * len(p), [None] * len(p)
    for t in range(len(p)):
        if p[t] is not None:
            err = (p[t] - e[t]) * -1  # EMAProjectionError's default InverseGraph = true
            if err >= 0.0:
                pos[t] = err
            else:
                neg[t] = err
    return pos, neg


def expected(closes, method, period):
    e = pj.ema(closes, period)
    p = METHODS[method](closes, period)
    s = pj.sma(closes, period)
    sp = pj.sma_projection(closes, period)
    up, down = trend(p)
    pos, neg = error(p, e)
    sup, sdown = trend(sp)
    return {
        "EMAProjection.EMA": e,
        "EMAProjection.Projection": p,
        "EMAProjectionTrend.TrendUp": up,
        "EMAProjectionTrend.TrendDown": down,
        "EMAProjectionError.PositiveError": pos,
        "EMAProjectionError.NegativeError": neg,
        "SMAProjection.SMA": s,
        "SMAProjection.Projection": sp,
        "SMAProjectionTrend.TrendUp": sup,
        "SMAProjectionTrend.TrendDown": sdown,
    }


def main():
    period = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    failed = False
    rows = []
    for path in sorted(glob.glob(os.path.join(HERE, "out", "*.csv"))):
        name = os.path.basename(path)[:-4]
        series, method = name.rsplit("_", 1)
        with open(os.path.join(os.path.dirname(HERE), "data", series + ".csv")) as f:
            closes = [float(r["close"]) for r in csv.DictReader(f)]
        with open(path) as f:
            got = list(csv.DictReader(f))
        want = expected(closes, method, period)
        for column, values in want.items():
            worst, mismatched, bars = 0.0, 0, 0
            for t, w in enumerate(values):
                g = got[t][column]
                if (w is None) != (g == ""):
                    mismatched += 1
                    continue
                if w is not None:
                    bars += 1
                    worst = max(worst, abs(float(g) - w))
            ok = mismatched == 0 and worst <= TOLERANCE
            failed |= not ok
            rows.append((series, method, column, bars, mismatched, worst, "ok" if ok else "FAIL"))
    print("| Series | Method | Plot | Bars compared | Set/unset mismatches | Max abs diff | |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print("| {} | {} | {} | {} | {} | {:.3g} | {} |".format(*r))
    print("\n{} plot comparisons, {}".format(len(rows), "FAILED" if failed else "all within {:g}".format(TOLERANCE)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
