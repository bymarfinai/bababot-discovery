"""
Mode 3 CLI Runner — jalanin di Railway lu
============================================

Usage:
  # Test single pair (default config, sweep 3 TP options)
  python run_mode3.py --db /path/to/market_data.db --symbol BTCUSDT

  # Multi-pair sweep
  python run_mode3.py --db market_data.db --pairs BTCUSDT,ETHUSDT,SOLUSDT

  # Custom TP options
  python run_mode3.py --db market_data.db --symbol ETHUSDT --tp 0.003,0.004,0.005

  # Loosen thresholds (if strict gives 0 trades)
  python run_mode3.py --db market_data.db --symbol BTCUSDT --preset medium

  # Save results to JSON
  python run_mode3.py --db market_data.db --pairs ALL --out results.json
"""

import argparse
import json
import sys
import time
from mode3_drc import DRCConfig, run_mode3, load_klines, compute_btc_returns, backtest


ALL_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "LINKUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT", "MATICUSDT",
    "NEARUSDT", "APTUSDT", "ARBUSDT", "1000PEPEUSDT", "WIFUSDT",
]

PRESETS = {
    "strict": dict(
        knn_min_confidence=0.70,
        ensemble_min_confidence=0.60,
        ensemble_min_agree=4,
        joint_confidence_min=0.75,
        joint_gap_min=0.50,
    ),
    "medium": dict(
        knn_min_confidence=0.60,
        ensemble_min_confidence=0.55,
        ensemble_min_agree=3,
        joint_confidence_min=0.65,
        joint_gap_min=0.30,
    ),
    "loose": dict(
        knn_min_confidence=0.55,
        ensemble_min_confidence=0.52,
        ensemble_min_agree=2,
        joint_confidence_min=0.60,
        joint_gap_min=0.20,
    ),
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="Path to market_data.db")
    p.add_argument("--symbol", default=None, help="Single symbol (e.g. BTCUSDT)")
    p.add_argument("--pairs", default=None,
                   help="Comma-separated pairs, or 'ALL' for all 15 pairs")
    p.add_argument("--timeframe", default="15m", help="Timeframe (default 15m)")
    p.add_argument("--days", type=int, default=1825, help="Days of history (default 5yr)")
    p.add_argument("--tp", default="0.003,0.004,0.005",
                   help="Comma-separated TP options as decimals (e.g. 0.003,0.005)")
    p.add_argument("--preset", default="strict",
                   choices=list(PRESETS.keys()), help="Threshold preset")
    p.add_argument("--sl-atr-mult", type=float, default=1.2,
                   help="SL = mult × ATR(14) (default 1.2)")
    p.add_argument("--out", default=None, help="Save results to JSON file")
    p.add_argument("--include-trades", action="store_true",
                   help="Include per-trade log in JSON output")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def make_config(args) -> DRCConfig:
    preset = PRESETS[args.preset]
    return DRCConfig(
        symbol="", timeframe=args.timeframe, days=args.days,
        sl_atr_mult=args.sl_atr_mult,
        **preset,
    )


def format_result(r: dict) -> str:
    sc = r.get('signal_counts', {})
    line = (
        f"  TP {r['tp_pct']*100:.2f}%: "
        f"trades={r['trades']:4d}  "
        f"WR={r['wr']:5.1f}%  "
        f"PPD=${r['profit_per_day']:7.2f}  "
        f"Total=${r['total_pnl_usd']:9.2f}  "
        f"AvgPnL=${r['avg_pnl_usd']:6.2f}  "
        f"MaxDD=${r['max_dd_usd']:7.2f}  "
        f"Hold={r['avg_hold_candles']}c"
    )
    if r['trades'] == 0:
        line += f"    [rejects: A={sc.get('A_low_conf',0)} B={sc.get('B_low_conf',0)} disagree={sc.get('A_B_disagree',0)} joint={sc.get('joint_conf_low',0)} gap={sc.get('gap_low',0)}]"
    return line


def main():
    args = parse_args()

    # Determine pairs
    if args.pairs:
        if args.pairs.upper() == "ALL":
            pairs = ALL_PAIRS
        else:
            pairs = [p.strip().upper() for p in args.pairs.split(",")]
    elif args.symbol:
        pairs = [args.symbol.upper()]
    else:
        print("ERROR: must specify --symbol or --pairs", file=sys.stderr)
        sys.exit(1)

    tp_options = [float(x) for x in args.tp.split(",")]
    base_cfg = make_config(args)

    # Pre-load BTC returns once (used by ensemble correlation model for alts)
    print(f"Loading BTCUSDT {args.timeframe} for correlation model...")
    btc_returns = compute_btc_returns(args.db, args.timeframe)
    print(f"  BTC data: {len(btc_returns) if btc_returns is not None else 0} candles")

    all_results = []
    print(f"\nMODE 3 — DIRECTIONAL REGIME CLASSIFIER")
    print(f"Preset: {args.preset.upper()}  |  TF: {args.timeframe}  |  Days: {args.days}")
    print(f"TP options: {[f'{t*100:.2f}%' for t in tp_options]}")
    print(f"SL = {args.sl_atr_mult} × ATR(14) (bounded 0.1%..0.5%)")
    print(f"KNN k={base_cfg.knn_k}, warmup={base_cfg.knn_warmup}")
    print(f"Joint thresholds: conf>={base_cfg.joint_confidence_min}, gap>={base_cfg.joint_gap_min}")
    print("=" * 110)

    for symbol in pairs:
        t0 = time.time()
        try:
            data = load_klines(args.db, symbol, args.timeframe, days=args.days)
        except Exception as e:
            print(f"\n[{symbol}] LOAD FAILED: {e}")
            continue
        print(f"\n[{symbol}] loaded {len(data['close'])} candles "
              f"({(data['open_time'][-1]-data['open_time'][0])/(1000*86400):.0f} days)")

        for tp in tp_options:
            cfg = DRCConfig(
                symbol=symbol, timeframe=args.timeframe, days=args.days,
                sl_atr_mult=args.sl_atr_mult,
                **PRESETS[args.preset],
            )
            r = backtest(data, cfg, tp_pct=tp,
                         btc_returns=btc_returns if symbol != "BTCUSDT" else None)
            print(format_result(r))
            entry = {
                'symbol': symbol,
                'timeframe': args.timeframe,
                'preset': args.preset,
                **{k: v for k, v in r.items() if k != 'trades_list'},
            }
            if args.include_trades:
                entry['trades_list'] = r['trades_list']
            all_results.append(entry)
        print(f"  ({time.time()-t0:.1f}s)")

    # Summary table
    print("\n" + "=" * 110)
    print("SUMMARY — sorted by (WR desc, PPD desc)")
    print("=" * 110)
    print(f"{'Symbol':<14} {'TP%':>6} {'Trades':>7} {'WR%':>6} {'PPD$':>8} {'Avg$':>7} {'MaxDD$':>8}")
    print("-" * 110)
    ranked = sorted(all_results, key=lambda x: (-x['wr'], -x['profit_per_day']))
    for r in ranked:
        print(f"{r['symbol']:<14} {r['tp_pct']*100:>5.2f}% {r['trades']:>7d} "
              f"{r['wr']:>5.1f}% {r['profit_per_day']:>8.2f} {r['avg_pnl_usd']:>7.2f} "
              f"{r['max_dd_usd']:>8.2f}")

    # Filter candidates matching user target
    print("\n" + "=" * 110)
    print("CANDIDATES — meeting user target: WR>=75%, trades>=30, PPD>0")
    print("=" * 110)
    candidates = [r for r in ranked if r['wr'] >= 75 and r['trades'] >= 30 and r['profit_per_day'] > 0]
    if candidates:
        for r in candidates:
            print(f"  ✅ {r['symbol']} {args.timeframe} TP={r['tp_pct']*100:.2f}%  "
                  f"WR={r['wr']}%  trades={r['trades']}  PPD=${r['profit_per_day']}")
    else:
        print("  (none — try --preset medium or --preset loose to explore)")

    if args.out:
        with open(args.out, "w") as f:
            json.dump({
                'config': {
                    'preset': args.preset, 'timeframe': args.timeframe,
                    'days': args.days, 'sl_atr_mult': args.sl_atr_mult,
                    'tp_options': tp_options,
                },
                'results': all_results,
                'candidates': [
                    {'symbol': r['symbol'], 'tp_pct': r['tp_pct'],
                     'wr': r['wr'], 'trades': r['trades'],
                     'profit_per_day': r['profit_per_day']}
                    for r in candidates
                ],
            }, f, indent=2, default=str)
        print(f"\nResults saved: {args.out}")


if __name__ == "__main__":
    main()
