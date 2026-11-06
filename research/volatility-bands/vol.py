"""Variance forecasts, losses and band tests, as pre-registered in README.md.

Indexing: x[j] is the return of bar j (x[0] is unused). Each forecast list g has g[j] = the variance
forecast for bar j made at the close of bar j-1, from x[1..j-1] only (None where not formed).
"""

import math


def rolling(x, n):
    """g[j] = mean of x^2 over the last n bars before j (all of them while there are fewer than n)."""
    g = [None] * len(x)
    total = 0.0
    sq = [0.0] + [v * v for v in x[1:]]
    for j in range(2, len(x)):
        total += sq[j - 1]
        if j - 1 - n >= 1:
            total -= sq[j - 1 - n]
        g[j] = total / min(n, j - 1)  # fewer than n bars so far: their mean
    return g


def ewma(x, lam, start):
    """g[j] = lam g[j-1] + (1 - lam) x[j-1]^2, with g[1] = start."""
    g = [None] * len(x)
    g[1] = start
    for j in range(2, len(x)):
        g[j] = lam * g[j - 1] + (1 - lam) * x[j - 1] * x[j - 1]
    return g


def garch(x, omega, alpha, beta, first, h0):
    """g[j] = omega + alpha x[j-1]^2 + beta g[j-1], with g[first] = h0."""
    g = [None] * len(x)
    g[first] = h0
    for j in range(first + 1, len(x)):
        g[j] = omega + alpha * x[j - 1] * x[j - 1] + beta * g[j - 1]
    return g


def har_features(x, windows):
    """Per bar j: [1, mean x^2 over the last w bars before j for each w], from bars before j."""
    sq = [0.0] + [v * v for v in x[1:]]
    prefix = [0.0]
    for v in sq[1:]:
        prefix.append(prefix[-1] + v)  # prefix[i] = sum sq[1..i]
    feats = [None] * len(x)
    for j in range(max(windows) + 1, len(x)):
        feats[j] = [1.0] + [(prefix[j - 1] - prefix[j - 1 - w]) / w for w in windows]
    return feats


def ols(rows, ys):
    """Least squares by the normal equations (a handful of columns)."""
    k = len(rows[0])
    a = [[0.0] * (k + 1) for _ in range(k)]
    for r, y in zip(rows, ys):
        for i in range(k):
            for m in range(k):
                a[i][m] += r[i] * r[m]
            a[i][k] += r[i] * y
    for c in range(k):  # Gauss-Jordan with partial pivoting
        p = max(range(c, k), key=lambda i: abs(a[i][c]))
        a[c], a[p] = a[p], a[c]
        for i in range(k):
            if i != c and a[c][c] != 0:
                f = a[i][c] / a[c][c]
                for m in range(c, k + 1):
                    a[i][m] -= f * a[c][m]
    return [a[i][k] / a[i][i] for i in range(k)]


def har(x, windows, fit_lo, fit_hi):
    feats = har_features(x, windows)
    rows = [feats[j] for j in range(fit_lo, fit_hi)]
    ys = [x[j] * x[j] for j in range(fit_lo, fit_hi)]
    b = ols(rows, ys)
    g = [None if f is None else sum(c * v for c, v in zip(b, f)) for f in feats]
    return g, b


def nelder_mead(f, x0, step=0.5, iters=800, tol=1e-10):
    n = len(x0)
    pts = [list(x0)] + [[x0[i] + (step if i == k else 0.0) for i in range(n)] for k in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) <= tol * (abs(vals[0]) + tol):
            break
        c = [sum(p[i] for p in pts[:-1]) / n for i in range(n)]
        xr = [c[i] + (c[i] - pts[-1][i]) for i in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [c[i] + 2 * (c[i] - pts[-1][i]) for i in range(n)]
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [c[i] + 0.5 * (pts[-1][i] - c[i]) for i in range(n)]
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                for k in range(1, n + 1):
                    pts[k] = [pts[0][i] + 0.5 * (pts[k][i] - pts[0][i]) for i in range(n)]
                    vals[k] = f(pts[k])
    best = min(range(n + 1), key=lambda i: vals[i])
    return pts[best], vals[best]


def garch_params(theta):
    a, b, c = theta
    persistence = 0.999999 / (1 + math.exp(-b))
    share = 1 / (1 + math.exp(-c))
    return math.exp(a), persistence * share, persistence * (1 - share)


def fit_garch(x, fit_lo, fit_hi):
    """Gaussian MLE on bars fit_lo..fit_hi-1, recursion started at fit_lo with the training variance."""
    var = sum(x[j] * x[j] for j in range(fit_lo, fit_hi)) / (fit_hi - fit_lo)

    def nll(theta):
        omega, alpha, beta = garch_params(theta)
        h, total = var, 0.0
        for j in range(fit_lo, fit_hi):
            if j > fit_lo:
                h = omega + alpha * x[j - 1] * x[j - 1] + beta * h
            if h <= 0:
                return 1e300
            total += math.log(h) + x[j] * x[j] / h
        return total

    theta0 = [math.log(var * 0.05), math.log(0.95 / 0.05), math.log(0.1 / 0.9)]
    theta, _ = nelder_mead(nll, theta0)
    theta, _ = nelder_mead(nll, theta, step=0.2)  # restart from the best point
    omega, alpha, beta = garch_params(theta)
    return omega, alpha, beta, var


def qlike(h, r):
    return math.log(h) + r * r / h


def mse(h, r):
    return (r * r - h) ** 2


def diebold_mariano(d):
    """Mean loss difference, Newey-West t statistic and two-sided normal p."""
    t = len(d)
    mean = sum(d) / t
    lags = int(4 * (t / 100) ** (2 / 9))
    dev = [v - mean for v in d]
    var = sum(v * v for v in dev) / t
    for lag in range(1, lags + 1):
        cov = sum(dev[i] * dev[i - lag] for i in range(lag, t)) / t
        var += 2 * (1 - lag / (lags + 1)) * cov
    stat = mean / math.sqrt(var / t) if var > 0 else 0.0
    return mean, stat, math.erfc(abs(stat) / math.sqrt(2))


def quantile(values, q):
    """Empirical quantile with linear interpolation between order statistics."""
    s = sorted(values)
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _xlogy(x, y):
    return 0.0 if x == 0 else x * math.log(y)


def chi2_sf(stat, df):
    if df == 1:
        return math.erfc(math.sqrt(max(stat, 0.0) / 2))
    if df == 2:
        return math.exp(-max(stat, 0.0) / 2)
    raise ValueError(df)


def kupiec(misses, nominal_miss):
    """Unconditional coverage: LR statistic and p (chi-square, 1 df)."""
    t, x = len(misses), sum(misses)
    p_hat = x / t
    lr = -2 * (_xlogy(t - x, 1 - nominal_miss) + _xlogy(x, nominal_miss)
               - _xlogy(t - x, 1 - p_hat) - _xlogy(x, p_hat))
    return lr, chi2_sf(lr, 1)


def christoffersen(misses, nominal_miss):
    """Independence (1 df) and conditional coverage (2 df): statistics and p values."""
    n = [[0, 0], [0, 0]]
    for a, b in zip(misses, misses[1:]):
        n[a][b] += 1
    n0, n1 = n[0][0] + n[0][1], n[1][0] + n[1][1]
    p01 = n[0][1] / n0 if n0 else 0.0
    p11 = n[1][1] / n1 if n1 else 0.0
    p = (n[0][1] + n[1][1]) / (n0 + n1)
    l_null = _xlogy(n[0][0] + n[1][0], 1 - p) + _xlogy(n[0][1] + n[1][1], p)
    l_alt = (_xlogy(n[0][0], 1 - p01) + _xlogy(n[0][1], p01)
             + _xlogy(n[1][0], 1 - p11) + _xlogy(n[1][1], p11))
    lr_ind = -2 * (l_null - l_alt)
    lr_pof, _ = kupiec(misses, nominal_miss)
    lr_cc = lr_pof + lr_ind
    return lr_ind, chi2_sf(lr_ind, 1), lr_cc, chi2_sf(lr_cc, 2)
