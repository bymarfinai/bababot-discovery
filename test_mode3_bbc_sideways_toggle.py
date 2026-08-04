import unittest

from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher


class SidewaysTradeToggleTests(unittest.TestCase):
    def test_disabled_sideways_suppresses_range_entry(self):
        cfg = Mode3BBCConfig(
            enable_sideways_trades=False,
            direct_transition_enabled=False,
            sideways_mtf_15m_enabled=False,
            sideways_body_ratio_min=0.0,
        )
        switcher = Switcher(cfg)
        switcher.state = "SIDEWAYS"

        switcher.process_candle(
            bar_idx=100,
            o=109.0,
            h=110.0,
            l=100.0,
            c=105.0,
            ema20=104.0,
            vah=108.0,
            val=95.0,
            poc=103.0,
        )

        self.assertIsNone(switcher.position)
        self.assertEqual(switcher.state, "SIDEWAYS")

    def test_disabled_sideways_keeps_direct_bull_transition(self):
        cfg = Mode3BBCConfig(
            enable_sideways_trades=False,
            direct_transition_enabled=True,
            bull_mtf_15m_enabled=False,
            bull_body_ratio_min=0.0,
        )
        switcher = Switcher(cfg)
        switcher.state = "SIDEWAYS"

        switcher.process_candle(
            bar_idx=100,
            o=99.0,
            h=103.0,
            l=98.0,
            c=102.0,
            ema20=100.0,
            vah=110.0,
            val=90.0,
            poc=100.0,
        )

        self.assertIsNotNone(switcher.position)
        self.assertEqual(switcher.position.tool, "BULL")
        self.assertEqual(switcher.position.side, "LONG")
        self.assertEqual(switcher.state, "BULL")

    def test_enabled_sideways_preserves_existing_range_entry(self):
        cfg = Mode3BBCConfig(
            enable_sideways_trades=True,
            direct_transition_enabled=False,
            sideways_mtf_15m_enabled=False,
            sideways_body_ratio_min=0.0,
        )
        switcher = Switcher(cfg)
        switcher.state = "SIDEWAYS"

        switcher.process_candle(
            bar_idx=100,
            o=109.0,
            h=110.0,
            l=100.0,
            c=105.0,
            ema20=104.0,
            vah=108.0,
            val=95.0,
            poc=103.0,
        )

        self.assertIsNotNone(switcher.position)
        self.assertEqual(switcher.position.tool, "SIDEWAYS")
        self.assertEqual(switcher.position.side, "SHORT")


if __name__ == "__main__":
    unittest.main()
