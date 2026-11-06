"""NinjaTrader's EMA and the candidate projections, written the way the indicator reads them.

Every projection function takes the closes and returns a list p where p[t] is the forecast
of the EMA at bar t made with data up to bar t-1 only (None while it cannot be formed).
Inside a function, `back(s, t, n)` is NinjaScript's `s[n]` on bar `t` (n bars ago), so each
line can be checked against EMAProjection.cs.
"""


def back(series, t, n):
    return series[t - n]


def ema(closes, period):
    """NinjaTrader 8's EMA: seeded with the first value, k = 2 / (Period + 1)."""
    k = 2.0 / (1 + period)
    out = []
    for t, x in enumerate(closes):
        out.append(x if t == 0 else x * k + (1 - k) * out[t - 1])
    return out


def no_change(closes, period):
    """Baseline A: the next EMA equals the last one."""
    e = ema(closes, period)
    return [None] + e[:-1]


def span_slope(closes, period, span):
    """ema1 plus the EMA's average change per bar over the last `span` bars.

    span = 1 is baseline B (the last bar's change repeated).
    """
    e = ema(closes, period)
    p = [None] * len(e)
    for t in range(span + 1, len(e)):
        ema1 = back(e, t, 1)
        emaX = back(e, t, span + 1)
        p[t] = ema1 + (ema1 - emaX) / span
    return p


def average_slope(closes, period):
    """EMAProjection's AverageSlope: the slope over the last Period bars, divided by its true span."""
    return span_slope(closes, period, period)


def average_slope_original(closes, period):
    """The formula before the fix: Period bars of change divided by Period - 1."""
    e = ema(closes, period)
    p = [None] * len(e)
    if period < 2:
        return p
    for t in range(period + 1, len(e)):
        ema1 = back(e, t, 1)
        emaX = back(e, t, period + 1)
        p[t] = ema1 + (ema1 - emaX) / (period - 1)
    return p


def damped_slope(closes, period, phi):
    """ema1 plus phi times the last bar's change."""
    e = ema(closes, period)
    p = [None] * len(e)
    for t in range(2, len(e)):
        p[t] = back(e, t, 1) + phi * (back(e, t, 1) - back(e, t, 2))
    return p


def price_hold(closes, period):
    """EMAProjection's PriceHold: the EMA the next bar would give if it closed where the last bar did.

    ema1 + k * (close1 - ema1). By the EMA's own recursion this equals ema1 + (1 - k) * (ema1 - ema2),
    the last bar's change scaled by 1 - k = (Period - 1) / (Period + 1).
    """
    e = ema(closes, period)
    k = 2.0 / (1 + period)
    p = [None] * len(e)
    for t in range(2, len(e)):
        ema1 = back(e, t, 1)
        ema2 = back(e, t, 2)
        p[t] = ema1 + (1 - k) * (ema1 - ema2)
    return p


def ew_slope(closes, period, beta):
    """ema1 plus an exponentially weighted average of the EMA's one-bar changes.

    This is Holt's trend with the EMA itself as the level: b = beta * (e1 - e2) + (1 - beta) * b.
    """
    e = ema(closes, period)
    p = [None] * len(e)
    b = None
    for t in range(2, len(e)):
        d = e[t - 1] - e[t - 2]
        b = d if b is None else beta * d + (1 - beta) * b
        p[t] = e[t - 1] + b
    return p


def holt_price(closes, period, alpha, beta):
    """Holt's linear trend on the closes, turned into an EMA forecast through the EMA's update.

    The next close is forecast as level + trend; the EMA forecast is ema1 + k * (forecast - ema1).
    """
    e = ema(closes, period)
    k = 2.0 / (1 + period)
    p = [None] * len(e)
    level, trend = closes[0], 0.0
    for t in range(1, len(e)):
        if t >= 2:
            x_hat = level + trend
            p[t] = e[t - 1] + k * (x_hat - e[t - 1])
        x = closes[t]
        prev = level
        level = alpha * x + (1 - alpha) * (level + trend)
        trend = beta * (level - prev) + (1 - beta) * trend
    return p


def sma(closes, period):
    """NinjaTrader 8's SMA on time bars: a running sum, averaging the bars so far until there are Period."""
    out = []
    total = 0.0
    for t, x in enumerate(closes):
        total = total + x - (closes[t - period] if t >= period else 0)
        out.append(total / (t + 1 if t < period else period))
    return out


def sma_projection(closes, period):
    """SMAProjection: sma1 plus the SMA's average change per bar over the last Period bars."""
    s = sma(closes, period)
    p = [None] * len(s)
    for t in range(period + 1, len(s)):
        sma1 = back(s, t, 1)
        smaX = back(s, t, period + 1)
        p[t] = sma1 + (sma1 - smaX) / period
    return p
