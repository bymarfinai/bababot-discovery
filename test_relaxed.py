"""Verify engine triggers with slightly relaxed thresholds — sanity check only."""
import numpy as np
from mode3_drc import DRCConfig, backtest

np.random.seed(7)
n = 25000
ts = 1704067200000 + np.arange(n) * 15 * 60 * 1000

# Stronger regime-shifting data
returns = np.zeros(n)
regime_len = 3000
for i in range(n):
    r = (i // regime_len) % 3
    if r == 0:   returns[i] = 0.0005 + np.random.randn() * 0.001  # strong uptrend
    elif r == 1: returns[i] = -0.0004 + np.random.randn() * 0.001 # strong downtrend
    else:        returns[i] = np.random.randn() * 0.0015          # choppy

price = 50000 * np.exp(np.cumsum(returns))
high = price * (1 + np.abs(np.random.randn(n) * 0.0006))
low = price * (1 - np.abs(np.random.randn(n) * 0.0006))
open_ = np.roll(price, 1); open_[0] = price[0]
vol = 1000 * (1 + np.abs(np.random.randn(n) * 0.4))

data = {
    'open_time': ts.astype(np.int64),
    'open': open_, 'high': high, 'low': low, 'close': price, 'volume': vol,
}

# Try 3 config levels: strict → relaxed
configs = [
    ("STRICT (target 75%+ WR)", DRCConfig(knn_min_confidence=0.70,
        ensemble_min_confidence=0.60, ensemble_min_agree=4,
        joint_confidence_min=0.75, joint_gap_min=0.50, knn_warmup=3000)),
    ("MEDIUM (target 65%+ WR)", DRCConfig(knn_min_confidence=0.60,
        ensemble_min_confidence=0.55, ensemble_min_agree=3,
        joint_confidence_min=0.65, joint_gap_min=0.30, knn_warmup=3000)),
    ("LOOSE (verify engine works)", DRCConfig(knn_min_confidence=0.50,
        ensemble_min_confidence=0.50, ensemble_min_agree=2,
        joint_confidence_min=0.55, joint_gap_min=0.15, knn_warmup=3000)),
]

for name, cfg in configs:
    print(f"\n{'='*80}\n{name}\n{'='*80}")
    for tp in [0.004]:
        r = backtest(data, cfg, tp_pct=tp)
        sc = r['signal_counts']
        print(f"TP {tp*100:.1f}%:  Trades={r['trades']} ({r['wins']}W/{r['losses']}L/{r['timeouts']}TO)  "
              f"WR={r['wr']}%  PPD=${r['profit_per_day']}  Avg=${r['avg_pnl_usd']}")
        print(f"  Signal counts: A_low={sc.get('A_low_conf',0)}  B_low={sc.get('B_low_conf',0)}  "
              f"disagree={sc.get('A_B_disagree',0)}  joint_low={sc.get('joint_conf_low',0)}  "
              f"gap_low={sc.get('gap_low',0)}  OK={sc.get('OK',0)}")
