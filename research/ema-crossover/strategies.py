"""Crossover signals, actual and one bar early on the EMA Projection, and the trading engine.

Signals: each function returns a list `state` where state[i] is +1 (long side), -1 (short side) or 0
(no opinion, keep the last position), computed at the close of bar i from closes[0..i] only.

Engine: the decision made at the close of bar i is filled at the open of bar i+1 and held until
the open of the bar after the next decision changes it. Nothing reads a price after bar i to
make decision i.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ema-projection"))
import projection as pj  # noqa: E402


def sign(x):
    return (x > 0) - (x < 0)


def next_ema(closes, period, method):
    """q[i]: the EMA Projection's value for bar i+1, made at the close of bar i (None if not formed yet).

    projection.py's lists hold p[t] = forecast of bar t made at bar t-1, so q[i] = p[i+1]. Bar i+1 does
    not need to exist: the projection only reads bars up to i, so it is computed from closes + [anything].
    """
    p = method(list(closes) + [closes[-1]], period)
    return p[1:]


PRICE_HOLD = pj.price_hold
AVERAGE_SLOPE = pj.average_slope


# Family 1: EMA direction. Long while the EMA rises, short (or flat) while it falls.

def ema_direction(closes, period):
    """Actual: the EMA's last change, ema[i] - ema[i-1]."""
    e = pj.ema(closes, period)
    return [0] + [sign(e[i] - e[i - 1]) for i in range(1, len(e))]


def ema_direction_early(closes, period, method):
    """One bar early: the projected next change, projection(i+1) - ema[i]."""
    e = pj.ema(closes, period)
    q = next_ema(closes, period, method)
    return [0 if q[i] is None else sign(q[i] - e[i]) for i in range(len(e))]


# Family 2: price/EMA cross. Long while the close is above the EMA, short (or flat) below.

def price_cross(closes, period):
    """Actual: close[i] against ema[i]."""
    e = pj.ema(closes, period)
    return [sign(c - x) for c, x in zip(closes, e)]


def price_cross_early(closes, period, method):
    """One bar early: close[i] against the projected EMA of bar i+1."""
    q = next_ema(closes, period, method)
    return [0 if q[i] is None else sign(closes[i] - q[i]) for i in range(len(closes))]


# Family 3: fast/slow EMA cross. Long while the fast EMA is above the slow one.

def ema_cross(closes, fast, slow):
    """Actual: emaFast[i] against emaSlow[i]."""
    f, s = pj.ema(closes, fast), pj.ema(closes, slow)
    return [sign(a - b) for a, b in zip(f, s)]


def ema_cross_early(closes, fast, slow, method):
    """One bar early: both EMAs projected to bar i+1, then compared."""
    f, s = next_ema(closes, fast, method), next_ema(closes, slow, method)
    return [0 if f[i] is None or s[i] is None else sign(f[i] - s[i]) for i in range(len(closes))]


def positions(state, lo, hi, long_only):
    """Decisions for bars lo..hi-1: the state, held through zeros, with -1 turned flat when long_only.

    The book starts flat at bar lo; a zero state keeps the last decision.
    """
    out, last = [], 0
    for i in range(lo, hi):
        if state[i] != 0:
            last = state[i]
        out.append(max(last, 0) if long_only else last)
    return out


class Market:
    """Contract terms: dollars per point and the cost of one side (commission plus slippage)."""

    def __init__(self, multiplier, commission, slippage_points):
        self.multiplier = multiplier
        self.cost_per_side = commission + slippage_points * multiplier


ES = Market(multiplier=50.0, commission=2.50, slippage_points=0.25)  # one contract
SPY = Market(multiplier=1.0, commission=0.005, slippage_points=0.01)  # one share


def run(opens, decisions, lo, market, costs=True):
    """Trades decisions made at the closes of bars lo, lo+1, ... at the following opens.

    Decision k (made at the close of bar lo+k) is filled at the open of bar lo+k+1 and held to the
    open of bar lo+k+2. The last decision's position is closed at the open after it, so a run over
    decisions for bars lo..hi-1 needs opens up to bar hi; the caller passes hi <= len(opens) - 1.

    Returns per-interval P&L in dollars (interval k: open[lo+k+1] to open[lo+k+2], costs of the
    fill at its start included) and the closed trades' P&L.
    """
    side = market.cost_per_side if costs else 0.0
    m = market.multiplier
    pnl, trades = [], []
    prev, entry, trade_pnl = 0, None, 0.0
    n = len(decisions)
    for k, pos in enumerate(decisions):
        start, end = opens[lo + k + 1], opens[lo + k + 2]
        fill_cost = abs(pos - prev) * side
        bar = -fill_cost
        if pos != prev:
            if prev != 0:  # close the open trade at this open
                trade_pnl -= abs(prev) * side
                trades.append(trade_pnl)
            trade_pnl = -abs(pos) * side if pos != 0 else 0.0
        bar += pos * (end - start) * m
        if pos != 0:
            trade_pnl += pos * (end - start) * m
        if k == n - 1 and pos != 0:  # close out at the end
            bar -= abs(pos) * side
            trade_pnl -= abs(pos) * side
            trades.append(trade_pnl)
        pnl.append(bar)
        prev = pos
    return pnl, trades


def changes(decisions):
    """How many times the position changes, counting the first entry from flat."""
    prev, count = 0, 0
    for d in decisions:
        if d != prev:
            count += 1
        prev = d
    return count
