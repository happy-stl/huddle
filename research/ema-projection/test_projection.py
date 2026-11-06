"""Checks the Python port against hand-computed values (the table in README.md).

Usage: python3 -m unittest test_projection
"""

import random
import unittest

import projection as pj

CLOSES = [100, 102, 101, 104, 103, 105]
PERIOD = 3  # k = 2 / (3 + 1) = 0.5


class HandComputed(unittest.TestCase):
    def assertSeries(self, got, want):
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            if w is None:
                self.assertIsNone(g)
            else:
                self.assertAlmostEqual(g, w, places=9)

    def test_ema(self):
        self.assertSeries(pj.ema(CLOSES, PERIOD), [100, 101, 101, 102.5, 102.75, 103.875])

    def test_price_hold(self):
        # ema1 + (1 - k) * (ema1 - ema2)
        self.assertSeries(pj.price_hold(CLOSES, PERIOD), [None, None, 101.5, 101, 103.25, 102.875])

    def test_average_slope(self):
        # ema1 + (ema1 - ema[Period + 1]) / Period
        self.assertSeries(pj.average_slope(CLOSES, PERIOD), [None, None, None, None, 102.5 + 2.5 / 3, 102.75 + 1.75 / 3])

    def test_average_slope_before_fix(self):
        # ema1 + (ema1 - ema[Period + 1]) / (Period - 1)
        self.assertSeries(pj.average_slope_original(CLOSES, PERIOD), [None, None, None, None, 103.75, 103.625])

    def test_price_hold_is_the_ema_of_a_repeated_close(self):
        rng = random.Random(1)
        closes = [5000.0]
        for _ in range(500):
            closes.append(closes[-1] + rng.gauss(0, 3))
        for period in (2, 9, 14, 50):
            e = pj.ema(closes, period)
            k = 2.0 / (1 + period)
            p = pj.price_hold(closes, period)
            for t in range(2, len(closes)):
                self.assertAlmostEqual(p[t], e[t - 1] + k * (closes[t - 1] - e[t - 1]), places=6)

    def test_holt_with_alpha_one_and_no_trend_is_price_hold(self):
        a = pj.holt_price(CLOSES, PERIOD, 1.0, 0.0)
        b = pj.price_hold(CLOSES, PERIOD)
        self.assertSeries(a, b)


if __name__ == "__main__":
    unittest.main()
