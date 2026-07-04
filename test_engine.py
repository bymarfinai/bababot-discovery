"""
Realistic-ish synthetic test: alternating trend regimes + noise.
Purpose: confirm engine CAN trigger trades and doesn't have bugs.
NOT a validity test for the strategy — that requires real data.
"""
import numpy as np
from mode3_drc import DRCConfig, backtest

np.random.seed(7)

n = 25000  # 25k candles ≈ 260 days at 15m
ts_start = 1704067200000  # 2024-01-01
ts = ts_start + np.arange(n) * 15 * 60 * 1000

# Regime-shifting price: 4 regimes cycling
regimes = np.zeros(n)
regime_len = 2000
for i in range(n):
    r_idx = (i // regime_len) % 4
    regimes[i] = r_idx

# Regime 0: uptrend, low vol
# Regime 1: choppy sideways
# Regime 2: downtrend, high vol
# Regime 3: mean-reverting
drift = np.zeros(n)
vol_mult = np.zeros(n)
for i in range(n):
    r = int(regimes[i])
    if r == 0:   drift[i] = 0.0002; vol_mult[i] = 1.0
    elif r == 1: drift[i] = 0.0;    vol_mult[i] = 1.2
    elif r == 2: drift[i] = -0.00015; vol_mult[i] = 1.8
    elif r == 3:
        drift[i] = -0.0001 if np.sin(i * 0.05) > 0 else 0.0001
        vol_mult[i] = 0.8

returns = drift + np.random.randn(n) * 0.0015 * vol_mult
price = 50000 * np.exp(np.cumsum(returns))
high = price * (1 + np.abs(np.random.randn(n) * 0.0008 * vol_mult))
low = price * (1 - np.abs(np.random.randn(n) * 0.0008 * vol_mult))
open_ = np.roll(price, 1); open_[0] = price[0]

# Volume: higher during trending regimes
base_vol = 1000
vol = base_vol * (1 + 0.5 * (np.abs(drift) / 0.0002)) * (1 + np.abs(np.random.randn(n) * 0.3))

data = {
    'open_time': ts.astype(np.int64),
    'open': open_, 'high': high, 'low': low,
    'close': price, 'volume': vol,
}

print(f"Data: {n} candles, price range ${price.min():.0f}–${price.max():.0f}")
print(f"Regimes present: {sorted(set(regimes.astype(int)))}")
print()

# Test with default config
cfg = DRCConfig(symbol="SYNTH", timeframe="15m", days=260, knn_warmup=3000)
print(f"Config: KNN k={cfg.knn_k}, joint_conf_min={cfg.joint_confidence_min}, "
      f"gap_min={cfg.joint_gap_min}, ensemble_agree>={cfg.ensemble_min_agree}")
print("=" * 90)

for tp in [0.003, 0.004, 0.005]:
    r = backtest(data, cfg, tp_pct=tp)
    print(f"\nTP {tp*100:.1f}%:")
    print(f"  Trades: {r['trades']} ({r['wins']}W / {r['losses']}L / {r['timeouts']}TO)")
    print(f"  WR: {r['wr']}%   PPD: ${r['profit_per_day']}   Total: ${r['total_pnl_usd']}")
    print(f"  Avg PnL/trade: ${r['avg_pnl_usd']} ({r['avg_pnl_pct_gross']}% gross)")
    print(f"  Max DD: ${r['max_dd_usd']}   Avg hold: {r['avg_hold_candles']} candles")
    print(f"  Signal breakdown: {r['signal_counts']}")
