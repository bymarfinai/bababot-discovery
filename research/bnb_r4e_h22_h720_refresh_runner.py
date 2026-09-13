#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

# Data-acquisition only: use the start of the current UTC day as END, so
# Binance Vision requests only fully completed prior UTC days. This does not
# alter the frozen R4e signal, consensus, anchor, hold, cost, or gate policy.
base.END = pd.Timestamp.now(tz="UTC").normalize()

import bnb_r4e_h22_h720_2026_confirmation as r4e

if __name__ == "__main__":
    r4e.main()
