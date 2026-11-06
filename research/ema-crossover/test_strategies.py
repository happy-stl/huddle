"""Checks the signals never look ahead and the engine fills and charges as documented.

Usage: python3 -m unittest test_strategies
"""

import random
import unittest

import backtest as bt
import strategies as st


def walk(n, seed):
    rng = random.Random(seed)
    closes = [5000.0]
    for _ in range(n - 1):
        closes.append(closes[-1] + rng.gauss(0, 5))
    return closes


SIGNALS = [
    ("ema_direction", lambda c: st.ema_direction(c, 9)),
    ("ema_direction_early PriceHold", lambda c: st.ema_direction_early(c, 9, st.PRICE_HOLD)),
    ("ema_direction_early AverageSlope", lambda c: st.ema_direction_early(c, 9, st.AVERAGE_SLOPE)),
    ("price_cross", lambda c: st.price_cross(c, 14)),
    ("price_cross_early PriceHold", lambda c: st.price_cross_early(c, 14, st.PRICE_HOLD)),
    ("price_cross_early AverageSlope", lambda c: st.price_cross_early(c, 14, st.AVERAGE_SLOPE)),
    ("ema_cross", lambda c: st.ema_cross(c, 5, 20)),
    ("ema_cross_early PriceHold", lambda c: st.ema_cross_early(c, 5, 20, st.PRICE_HOLD)),
    ("ema_cross_early AverageSlope", lambda c: st.ema_cross_early(c, 5, 20, st.AVERAGE_SLOPE)),
]


class NoLookahead(unittest.TestCase):
    def test_signal_at_bar_i_uses_only_bars_up_to_i(self):
        closes = walk(300, 1)
        for name, fn in SIGNALS:
            full = fn(closes)
            for i in range(0, len(closes)):
                self.assertEqual(fn(closes[: i + 1])[i], full[i], "{} at bar {}".format(name, i))

    def test_changing_later_bars_never_changes_earlier_signals(self):
        closes = walk(200, 2)
        for name, fn in SIGNALS:
            before = fn(closes)
            for i in (50, 120, 199):
                altered = closes[: i + 1] + [c * 1.1 + 40 for c in closes[i + 1:]]
                self.assertEqual(fn(altered)[: i + 1], before[: i + 1], "{} up to bar {}".format(name, i))


class Identities(unittest.TestCase):
    def test_single_ema_rules_are_one_rule(self):
        # c - ema[i] = (1 - k)(c - ema[i-1]), and PriceHold's projected change is k (c - ema[i]):
        # the EMA's direction, the price/EMA cross and both early PriceHold versions always agree.
        closes = walk(500, 3)
        for p in (5, 14, 50):
            a = st.price_cross(closes, p)
            self.assertEqual(st.ema_direction(closes, p)[1:], a[1:])
            self.assertEqual(st.ema_direction_early(closes, p, st.PRICE_HOLD)[2:], a[2:])
            self.assertEqual(st.price_cross_early(closes, p, st.PRICE_HOLD)[2:], a[2:])


class Engine(unittest.TestCase):
    def test_fills_at_the_next_open_with_costs(self):
        market = st.Market(multiplier=10.0, commission=1.0, slippage_points=0.5)  # 6 a side
        opens = [100, 101, 103, 102, 105, 104]
        # Decisions at the closes of bars 0..3: long, long, short, flat.
        pnl, trades = st.run(opens, [1, 1, -1, 0], 0, market)
        # Long filled at open 1 (101), held to open 3 (102): +10, one side in and one out.
        # Short filled at open 3 (102), held to open 4 (105): -30, one side in and one out.
        self.assertEqual(pnl, [(103 - 101) * 10 - 6, (102 - 103) * 10, (102 - 105) * 10 - 12, -6])
        self.assertEqual(trades, [10 - 12, -30 - 12])

    def test_open_position_is_closed_at_the_end(self):
        market = st.Market(multiplier=1.0, commission=0.0, slippage_points=1.0)
        pnl, trades = st.run([10, 11, 12, 13], [1, 1], 0, market)
        self.assertEqual(pnl, [1 - 1, 1 - 1])
        self.assertEqual(trades, [2 - 2])

    def test_positions_hold_through_zero_and_go_flat_long_only(self):
        self.assertEqual(st.positions([0, 1, 0, -1, 0, 1], 0, 6, False), [0, 1, 1, -1, -1, 1])
        self.assertEqual(st.positions([0, 1, 0, -1, 0, 1], 0, 6, True), [0, 1, 1, 0, 0, 1])

    def test_random_entry_matches_the_engine(self):
        market = st.ES
        opens = walk(400, 4)
        for long_only in (False, True):
            for k in (1, 2, 7, 30):
                seed = random.Random(k)
                got = bt.random_entry(opens, 10, 300, k, long_only, market, seed)
                rng = random.Random(k)
                times = sorted(rng.sample(range(300), k))
                pos = 1 if long_only else rng.choice((1, -1))
                dec, cur = [], 0
                for i in range(300):
                    if times and i == times[0]:
                        times.pop(0)
                        cur = pos
                        pos = (0 if pos else 1) if long_only else -pos
                    dec.append(cur)
                want = sum(st.run(opens, dec, 10, market)[0])
                self.assertAlmostEqual(got, want, places=6)


if __name__ == "__main__":
    unittest.main()
