"""Runs the pre-registered volatility and band tests (README.md) and writes RESULTS.md.

Usage: python3 ../ema-projection/fetch.py && python3 backtest.py
"""

import collections
import csv
import datetime as dt
import math
import os
import statistics
import zoneinfo

import vol

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "ema-projection", "data")

SERIES = [
    ("ES=F", "30m", "ESF_30m.csv", "America/Chicago"),
    ("ES=F", "1h", "ESF_1h.csv", "America/Chicago"),
    ("ES=F", "1d", "ESF_1d.csv", None),
    ("SPY", "30m", "SPY_30m.csv", "America/New_York"),
    ("SPY", "1h", "SPY_1h.csv", "America/New_York"),
    ("SPY", "1d", "SPY_1d.csv", None),
]
WARMUP = 250
TRAIN_SHARE = 0.6
ROLLING = [5, 10, 20, 50, 100, 250]
LAMBDAS = [0.80, 0.85, 0.90, 0.94, 0.97, 0.98, 0.99, 0.995]
LEVELS = [0.80, 0.95]
FLOOR_SHARE = 0.01
COVERAGE_TOLERANCE = 0.025
WIDTH_COVERAGE_SLACK = 0.010
NEEDED = 5


def load(name, tz):
    with open(os.path.join(DATA, name)) as f:
        rows = list(csv.DictReader(f))
    times = [dt.datetime.fromisoformat(r["time"]) for r in rows]
    if tz:
        zone = zoneinfo.ZoneInfo(tz)
        times = [t.astimezone(zone) for t in times]
    return times, [float(r["close"]) for r in rows]


def split_point(n):
    return WARMUP + int(TRAIN_SHARE * (n - WARMUP))


def day_window(times, n):
    counts = collections.Counter(t.date() for t in times[: int(TRAIN_SHARE * n)])
    return int(statistics.median(counts.values()))


def mean_loss(loss, h, r, lo, hi):
    return sum(loss(h[j], r[j]) for j in range(lo, hi)) / (hi - lo)


def forecasts(r, times, intraday, profiled, train, d):
    """Every model's and baseline's variance forecast h[j] for the return of bar j, and fit details."""
    lo, hi = train
    n = len(r)
    if profiled:
        slot = [None] + [t.strftime("%H:%M") for t in times[1:]]
        sums, counts = collections.defaultdict(float), collections.Counter()
        for j in range(lo, hi):
            sums[slot[j]] += r[j] * r[j]
            counts[slot[j]] += 1
        overall = sum(r[j] * r[j] for j in range(lo, hi)) / (hi - lo)
        prof = {s: sums[s] / counts[s] / overall for s in counts}
        s = [None] + [prof.get(slot[j], 1.0) for j in range(1, n)]
        x = [0.0] + [r[j] / math.sqrt(s[j]) for j in range(1, n)]
    else:
        prof = None
        s = [None] + [1.0] * (n - 1)
        x = r
    floor = FLOOR_SHARE * sum(x[j] * x[j] for j in range(lo, hi)) / (hi - lo)

    def finish(g):
        return [None if j == 0 or g[j] is None else max(g[j], floor) * s[j] for j in range(n)]

    out, info = {}, {}
    windows = (1, d, 5 * d) if intraday else (1, 5, 22)
    g, b = vol.har(x, windows, lo, hi)
    out["HAR"] = finish(g)
    info["HAR"] = "windows {}, b = {}".format("/".join(map(str, windows)), ", ".join("{:.3g}".format(v) for v in b))
    omega, alpha, beta, var = vol.fit_garch(x, lo, hi)
    out["GARCH(1,1)"] = finish(vol.garch(x, omega, alpha, beta, lo, var))
    info["GARCH(1,1)"] = "omega {:.3g}, alpha {:.4f}, beta {:.4f}".format(omega, alpha, beta)
    info["garch"] = (omega, alpha, beta, var)

    start = sum(x[j] * x[j] for j in range(1, WARMUP)) / (WARMUP - 1)
    best = None
    for nn in ROLLING:
        h = finish(vol.rolling(x, nn))
        q = mean_loss(vol.qlike, h, r, lo, hi)
        if best is None or q < best[0]:
            best = (q, nn, h)
    out["Rolling (N tuned)"] = best[2]
    info["Rolling (N tuned)"] = "N = {}".format(best[1])
    out["EWMA 0.94"] = finish(vol.ewma(x, 0.94, start))
    info["EWMA 0.94"] = ""
    best = None
    for lam in LAMBDAS:
        h = finish(vol.ewma(x, lam, start))
        q = mean_loss(vol.qlike, h, r, lo, hi)
        if best is None or q < best[0]:
            best = (q, lam, h)
    out["EWMA (lambda tuned)"] = best[2]
    info["EWMA (lambda tuned)"] = "lambda = {}".format(best[1])
    info["profile"] = prof
    info["floor"] = floor
    return out, info


# Written from this script's output on the pre-registered data; reread it if anything changes.
NOTES = [
    "What the numbers say:",
    "",
    "- **The forecast passes, narrowly.** GARCH(1,1) beat the best baseline on 5 series, significantly (DM p < 0.05)",
    "  only on the two daily series; ES=F 1h and SPY 1h are at p 0.055 and 0.085, and SPY 30m (212 held-out bars)",
    "  is a coin toss (p 0.83). On ES=F 30m the training-selected HAR lost to EWMA.",
    "- **The bands fail.** At 80% the volatility band was wider than the fixed band on every series, so the width",
    "  condition held on none: returns are fat-tailed, so the fixed band's 80% interval of the unconditional returns",
    "  is narrow, and scaling by a forecast does not beat it. At 95% the volatility band was narrower at no worse",
    "  coverage on 3 series (ES=F daily, SPY 1h and daily), short of the 5 needed. Coverage was within 2.5 points",
    "  of nominal on 4 series at each level; the two 30-minute series, whose held-out stretches were more volatile",
    "  than their training, under-covered. Where the volatility band does work it removes the clustering of misses",
    "  that the fixed band shows (Christoffersen p near 0 for most fixed bands).",
    "- **The time-of-day profile is fragile.** On ES=F a 16:00 Chicago bar (the settlement bar inside the daily",
    "  halt) appeared twice in training with almost no movement, so its profile weight was near 0. One such bar in",
    "  the held-out part (2026-10-23) moved normally, and its QLIKE term was about 1,100, which alone lifted the",
    "  ES=F 30m model's mean QLIKE by 1.4. Leaving that single bar out, which the pre-registration does not",
    "  allow and is noted only to explain the failure, HAR would have beaten EWMA there (-12.430 vs -12.417).",
    "  Without the profile, the models beat the baselines on ES=F 30m and 1h and SPY 1h but not SPY 30m.",
    "- **One implementation detail** not spelled out in advance: the rolling baseline with N = 250 has only 249",
    "  returns at the first training bar, so a rolling window shorter than N uses the bars it has.",
    "",
    "No NinjaTrader indicator or website chart follows, because Criterion 2 failed.",
    "",
]

MODELS = ["HAR", "GARCH(1,1)"]
BASELINES = ["Rolling (N tuned)", "EWMA 0.94", "EWMA (lambda tuned)"]


def bands(h, r, closes, train, test, level):
    lo, hi = train
    z = [r[j] / math.sqrt(h[j]) for j in range(lo, hi)]
    q_lo, q_hi = vol.quantile(z, (1 - level) / 2), vol.quantile(z, (1 + level) / 2)
    f_lo = vol.quantile([r[j] for j in range(lo, hi)], (1 - level) / 2)
    f_hi = vol.quantile([r[j] for j in range(lo, hi)], (1 + level) / 2)
    t_lo, t_hi = test
    res = {}
    for name, lower, upper in (
        ("vol", lambda j: q_lo * math.sqrt(h[j]), lambda j: q_hi * math.sqrt(h[j])),
        ("fixed", lambda j: f_lo, lambda j: f_hi),
    ):
        misses = [0 if lower(j) <= r[j] <= upper(j) else 1 for j in range(t_lo, t_hi)]
        widths = [math.exp(upper(j)) - math.exp(lower(j)) for j in range(t_lo, t_hi)]
        miss = 1 - level
        _, p_pof = vol.kupiec(misses, miss)
        _, p_ind, _, p_cc = vol.christoffersen(misses, miss)
        res[name] = {
            "coverage": 1 - sum(misses) / len(misses), "width": statistics.fmean(widths),
            "p_pof": p_pof, "p_ind": p_ind, "p_cc": p_cc,
        }
    res["q"] = (q_lo, q_hi, f_lo, f_hi)
    return res


def evaluate(symbol, interval, fname, tz, profiled):
    times, closes = load(fname, tz)
    n = len(closes)
    r = [0.0] + [math.log(closes[j] / closes[j - 1]) for j in range(1, n)]
    split = split_point(n)
    train, test = (WARMUP, split), (split, n)
    intraday = tz is not None
    d = day_window(times, n) if intraday else 1
    h, info = forecasts(r, times, intraday, profiled and intraday, train, d)
    rows = {}
    for name in MODELS + BASELINES:
        rows[name] = {
            "train_qlike": mean_loss(vol.qlike, h[name], r, *train),
            "qlike": mean_loss(vol.qlike, h[name], r, *test),
            "mse": mean_loss(vol.mse, h[name], r, *test),
            "info": info[name],
        }
    model = min(MODELS, key=lambda m: rows[m]["train_qlike"])
    base = min(BASELINES, key=lambda m: rows[m]["train_qlike"])
    diff = [vol.qlike(h[model][j], r[j]) - vol.qlike(h[base][j], r[j]) for j in range(*test)]
    dm = vol.diebold_mariano(diff)
    band = {level: bands(h[model], r, closes, train, test, level) for level in LEVELS}
    return {
        "times": times, "closes": closes, "r": r, "h": h, "info": info, "rows": rows, "model": model,
        "base": base, "dm": dm, "bands": band, "split": split, "n": n, "d": d,
    }


def pct(x):
    return "{:.1f}%".format(100 * x)


def main():
    lines = [
        "# Volatility Forecast and Range Bands: Results",
        "",
        "Generated by `backtest.py` from the data and the criteria pre-registered in [README.md](README.md)",
        "(commit 0cb5cb7, before any held-out run). Every number is from the held-out last 40% unless it says",
        "training. QLIKE is `ln h + r^2 / h` on log returns (lower is better); MSE is on `r^2`, times 1e9.",
        "",
    ]
    results = {}
    for symbol, interval, fname, tz in SERIES:
        for profiled in ([True, False] if tz else [False]):
            results[(symbol, interval, profiled)] = evaluate(symbol, interval, fname, tz, profiled)

    def primary(symbol, interval, tz):
        return results[(symbol, interval, tz is not None)]

    # Criterion 1.
    c1 = []
    lines += ["## Criterion 1: Volatility Forecast", "",
              "Best model and best baseline chosen by training QLIKE; primary variant (time-of-day profile on intraday).",
              "Diebold-Mariano on the per-bar QLIKE difference model minus baseline (negative favours the model).", "",
              "| Series | Best model | Held-out QLIKE | Best baseline | Held-out QLIKE | Difference | DM statistic | DM p | Pass |",
              "|---|---|---|---|---|---|---|---|---|"]
    for symbol, interval, _, tz in SERIES:
        res = primary(symbol, interval, tz)
        m, b = res["rows"][res["model"]], res["rows"][res["base"]]
        ok = m["qlike"] < b["qlike"]
        c1.append(ok)
        lines.append("| {} {} | {} | {:.4f} | {} | {:.4f} | {:+.4f} | {:.2f} | {:.3f} | {} |".format(
            symbol, interval, res["model"], m["qlike"], res["base"], b["qlike"], m["qlike"] - b["qlike"],
            res["dm"][1], res["dm"][2], "yes" if ok else "no"))
    c1_pass = sum(c1) >= NEEDED
    lines += ["", "**Criterion 1: {}** ({} of 6 series pass; {} needed).".format("PASS" if c1_pass else "FAIL", sum(c1), NEEDED), ""]

    # Criterion 2.
    c2_parts = {}
    lines += ["## Criterion 2: Range Bands", "",
              "Bands from each series' best model (primary variant). Coverage is the held-out share of next closes inside",
              "the band; *Kupiec p* tests coverage against nominal, *Christoffersen ind p* whether misses cluster and",
              "*cc p* both together. Width is the mean of (upper - lower) / last close.", ""]
    for level in LEVELS:
        cov_ok, width_ok = [], []
        lines += ["### {:.0%} Nominal".format(level), "",
                  "| Series | Band | Coverage | Kupiec p | Christoffersen ind p | cc p | Mean width | Coverage within 2.5 pp | Narrower at same or better coverage |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for symbol, interval, _, tz in SERIES:
            bd = primary(symbol, interval, tz)["bands"][level]
            v, f = bd["vol"], bd["fixed"]
            a = abs(v["coverage"] - level) <= COVERAGE_TOLERANCE
            w = v["width"] < f["width"] and v["coverage"] >= f["coverage"] - WIDTH_COVERAGE_SLACK
            cov_ok.append(a)
            width_ok.append(w)
            for name, x, extra in (("volatility", v, ("yes" if a else "no", "yes" if w else "no")), ("fixed", f, ("", ""))):
                lines.append("| {} {} | {} | {} | {:.3f} | {:.3f} | {:.3f} | {:.3f}% | {} | {} |".format(
                    symbol, interval, name, pct(x["coverage"]), x["p_pof"], x["p_ind"], x["p_cc"], 100 * x["width"], *extra))
        c2_parts[level] = (sum(cov_ok), sum(width_ok))
        lines += ["", "At {:.0%}: coverage condition on {} of 6 series, width condition on {} of 6.".format(
            level, sum(cov_ok), sum(width_ok)), ""]
    c2_pass = all(a >= NEEDED and w >= NEEDED for a, w in c2_parts.values())
    lines += ["**Criterion 2: {}** ({}).".format("PASS" if c2_pass else "FAIL", "; ".join(
        "{:.0%}: coverage {} / 6, width {} / 6".format(level, a, w) for level, (a, w) in c2_parts.items())), ""]

    # Detail tables.
    lines += ["## Every Model and Baseline", "",
              "Held-out QLIKE and MSE (x 1e9) of everything fitted, with and without the time-of-day profile on intraday",
              "series. Training QLIKE is what the selection used.", ""]
    for symbol, interval, _, tz in SERIES:
        for profiled in ([True, False] if tz else [False]):
            res = results[(symbol, interval, profiled)]
            label = "with time-of-day profile" if profiled else ("without profile" if tz else "daily")
            lines += ["### {} {}, {}".format(symbol, interval, label), "",
                      "{} bars; held out {} from {}{}.".format(
                          res["n"], res["n"] - res["split"], res["times"][res["split"]].strftime("%Y-%m-%d %H:%M"),
                          ", day window D = {}".format(res["d"]) if tz else ""),
                      "",
                      "| Forecast | Fitted | Training QLIKE | Held-out QLIKE | Held-out MSE |",
                      "|---|---|---|---|---|"]
            for name in MODELS + BASELINES:
                row = res["rows"][name]
                lines.append("| {}{} | {} | {:.4f} | {:.4f} | {:.4g} |".format(
                    name, " (selected)" if name in (res["model"], res["base"]) else "", row["info"],
                    row["train_qlike"], row["qlike"], row["mse"] * 1e9))
            if not profiled and tz:
                m, b = res["rows"][res["model"]], res["rows"][res["base"]]
                lines.append("")
                lines.append("Without the profile: best model {} {:.4f} vs best baseline {} {:.4f} ({}).".format(
                    res["model"], m["qlike"], res["base"], b["qlike"], "model lower" if m["qlike"] < b["qlike"] else "baseline lower"))
            lines.append("")

    lines += ["## Verdict", "",
              "- Criterion 1 (volatility forecast): **{}**.".format("PASS" if c1_pass else "FAIL"),
              "- Criterion 2 (range bands): **{}**.".format("PASS" if c2_pass else "FAIL"), ""] + NOTES
    with open(os.path.join(HERE, "RESULTS.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return results, c1_pass, c2_pass


if __name__ == "__main__":
    main()
