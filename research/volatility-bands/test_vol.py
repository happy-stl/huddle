"""Checks the forecasts never look ahead and the tests compute what their formulas say.

Usage: python3 -m unittest test_vol
"""

import math
import random
import unittest

import vol


def returns(n, seed):
    rng = random.Random(seed)
    x, h = [0.0], 1e-4
    for _ in range(n - 1):
        h = 1e-6 + 0.1 * (x[-1] ** 2) + 0.85 * h
        x.append(rng.gauss(0, math.sqrt(h)))
    return x


class NoLookahead(unittest.TestCase):
    def test_forecast_for_bar_j_uses_only_bars_before_j(self):
        x = returns(400, 1)
        makers = {
            "rolling": lambda y: vol.rolling(y, 20),
            "ewma": lambda y: vol.ewma(y, 0.94, 1e-4),
            "garch": lambda y: vol.garch(y, 1e-6, 0.1, 0.85, 50, 1e-4),
            "har": lambda y: [None if f is None else sum(f) for f in vol.har_features(y, (1, 5, 22))],
        }
        for name, make in makers.items():
            base = make(x)
            for j in (60, 150, 399):
                altered = x[:j] + [v * 7 + 0.01 for v in x[j:]]
                self.assertEqual(make(altered)[: j + 1], base[: j + 1], "{} at {}".format(name, j))


class Formulas(unittest.TestCase):
    def test_rolling_and_ewma(self):
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        self.assertEqual(vol.rolling(x, 2), [None, None, 1.0, 2.5, 6.5])
        g = vol.ewma(x, 0.5, 10.0)
        self.assertEqual(g, [None, 10.0, 5.5, 4.75, 6.875])

    def test_ols_recovers_coefficients(self):
        rows = [[1.0, i, i * i % 7] for i in range(30)]
        ys = [2 + 3 * a + 0.5 * b for _, a, b in rows]
        for got, want in zip(vol.ols(rows, ys), [2, 3, 0.5]):
            self.assertAlmostEqual(got, want, places=9)

    def test_garch_fit_recovers_simulated_parameters(self):
        x = returns(6000, 2)
        omega, alpha, beta, _ = vol.fit_garch(x, 100, 6000)
        self.assertAlmostEqual(alpha, 0.1, delta=0.04)
        self.assertAlmostEqual(beta, 0.85, delta=0.06)

    def test_kupiec_and_christoffersen(self):
        misses = [0] * 95 + [1] * 5
        lr, p = vol.kupiec(misses, 0.05)
        self.assertAlmostEqual(lr, 0.0, places=9)
        self.assertAlmostEqual(p, 1.0, places=6)
        clustered = [0] * 90 + [1] * 10
        _, p_ind, _, _ = vol.christoffersen(clustered, 0.10)
        spread = ([0] * 9 + [1]) * 10
        _, p_ind2, _, _ = vol.christoffersen(spread, 0.10)
        self.assertLess(p_ind, 0.001)
        self.assertGreater(p_ind2, 0.05)

    def test_quantile_and_dm(self):
        self.assertEqual(vol.quantile([3, 1, 2, 4], 0.5), 2.5)
        mean, stat, p = vol.diebold_mariano([1.0, -1.0] * 50)
        self.assertEqual(mean, 0.0)
        self.assertAlmostEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
