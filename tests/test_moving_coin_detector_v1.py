import unittest

from moving_coin_detector.scanner import DetectorConfig, Features, classify


class MovingCoinDetectorTests(unittest.TestCase):
    def setUp(self):
        self.cfg = DetectorConfig(signal_threshold=68, ignition_threshold=60, edge_margin=10)

    def feature(self, **kw):
        base = dict(
            symbol="TESTUSDT",
            price=100.0,
            ret_5m_pct=0.0,
            ret_15m_pct=0.0,
            ret_1h_pct=0.0,
            ret_24h_pct=0.0,
            quote_volume_24h=50_000_000,
            volume_ratio=1.0,
            range_ratio=1.0,
            close_location=0.5,
            prev_20_high=100.0,
            prev_20_low=100.0,
            distance_to_high_pct=0.0,
            distance_to_low_pct=0.0,
            breakout_up_pct=0.0,
            breakdown_down_pct=0.0,
            ema20=100.0,
            ema50=100.0,
            ema_gap_pct=0.0,
            taker_buy_sell_ratio=1.0,
            oi_change_30m_pct=0.0,
            funding_rate=0.0,
            spread_bps=2.0,
        )
        base.update(kw)
        return Features(**base)

    def test_fresh_long_expansion_scores_long(self):
        f = self.feature(
            price=101.0,
            ret_5m_pct=0.9,
            ret_15m_pct=1.7,
            ret_1h_pct=2.8,
            ret_24h_pct=8.0,
            volume_ratio=2.5,
            range_ratio=1.8,
            close_location=0.92,
            prev_20_high=100.6,
            distance_to_high_pct=0.3976,
            distance_to_low_pct=2.4,
            breakout_up_pct=0.3976,
            ema20=100.5,
            ema50=99.8,
            ema_gap_pct=0.70,
            taker_buy_sell_ratio=1.75,
            oi_change_30m_pct=1.1,
        )
        r = classify(f, self.cfg)
        self.assertEqual(r.direction, "LONG")
        self.assertEqual(r.stage, "EXPANSION")
        self.assertGreaterEqual(r.score, 68)
        self.assertGreaterEqual(r.edge, 10)

    def test_fresh_short_expansion_scores_short(self):
        f = self.feature(
            price=99.0,
            ret_5m_pct=-0.9,
            ret_15m_pct=-1.7,
            ret_1h_pct=-2.8,
            ret_24h_pct=-8.0,
            volume_ratio=2.4,
            range_ratio=1.8,
            close_location=0.08,
            prev_20_low=99.4,
            distance_to_high_pct=-2.0,
            distance_to_low_pct=-0.4024,
            breakdown_down_pct=0.4024,
            ema20=99.5,
            ema50=100.2,
            ema_gap_pct=-0.70,
            taker_buy_sell_ratio=0.57,
            oi_change_30m_pct=1.2,
        )
        r = classify(f, self.cfg)
        self.assertEqual(r.direction, "SHORT")
        self.assertEqual(r.stage, "EXPANSION")
        self.assertGreaterEqual(r.score, 68)

    def test_flat_market_is_no_trade(self):
        r = classify(self.feature(), self.cfg)
        self.assertEqual(r.stage, "NO_TRADE")

    def test_extended_move_gets_chase_penalty(self):
        fresh = self.feature(
            ret_5m_pct=0.8,
            ret_15m_pct=1.6,
            ret_1h_pct=3.0,
            ret_24h_pct=10.0,
            volume_ratio=2.0,
            range_ratio=1.5,
            close_location=0.9,
            breakout_up_pct=0.3,
            distance_to_high_pct=0.3,
            distance_to_low_pct=4.0,
            ema20=101,
            ema50=99,
            taker_buy_sell_ratio=1.6,
            oi_change_30m_pct=0.8,
        )
        extended = self.feature(**{**fresh.__dict__, "ret_24h_pct": 70.0, "ret_1h_pct": 9.0})
        a = classify(fresh, self.cfg)
        b = classify(extended, self.cfg)
        self.assertLess(b.score, a.score)


if __name__ == "__main__":
    unittest.main()
