#!/usr/bin/env python3
"""F6.5 — Friday15 frozen upper-wick cut robust-tradeoff test.
Research only; live BBC untouched.

Rule is inherited EXACTLY from F6.4 and may not be modified:
FAILURE_60 AND UPPER_WICK_DOM (upper wick >= 50% of final completed 5m candle)
-> exit BUY at actual +60m open.

This milestone does NOT search thresholds or new features. It asks whether the
F6.4 economic improvement survives simple robustness tests:
1) action-level leave-one-out/jackknife;
2) chronological contiguous block contribution;
3) contribution concentration;
4) Discovery/Validation transfer;
5) winner-clipping guard.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60
import f63_friday_failure60_candle_morphology as f63
import f64_friday_failure60_upperwick_cut as f64

OUT = Path(os.getenv('F65_OUT', 'f65_out'))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = f517.SPLIT_N


def build_rows():
    k = f517.load_klines()
    days = [d for d in pd.date_range(f517.START, f517.END, inclusive='left', freq='D') if d.weekday() == 4]
    rows, parents = [], []
    for i, d in enumerate(days):
        t = pd.Timestamp(d.date(), tz='UTC') + pd.Timedelta(hours=8)
        tr = f517.simulate_parent(k, t)
        parents.append(tr)
        pf = f60.path_features(k, t, tr)
        failure60 = bool(
            pf['alive60'] and pf['progress60'] <= 0 and
            pf['taker60'] < 0 and pf['ema20_dist60'] <= 0
        )
        upper_wick_dom = False
        upper_wick_ratio = np.nan
        managed = float(tr.pnl)
        exit_px = np.nan
        delta = 0.0
        if failure60:
            dt = t + pd.Timedelta(minutes=60)
            cf = f63.candle(k, dt, tr.entry)
            if cf is None:
                raise RuntimeError(f'missing completed 5m candle before +60m for {tr.date}')
            upper_wick_dom = bool(cf['UPPER_WICK_DOM'])
            upper_wick_ratio = float(cf['upper_wick_ratio'])
            if upper_wick_dom:
                exit_px = float(k.loc[dt, 'open'])
                managed = f517.NOTIONAL * (exit_px / tr.entry - 1.0) - f517.ROUND_TRIP_FEE
                delta = managed - float(tr.pnl)
        true_failure = bool(failure60 and upper_wick_dom)
        rows.append({
            'i': i, 'date': tr.date,
            'period': 'discovery' if i < SPLIT else 'validation',
            'parent_pnl': float(tr.pnl), 'managed_pnl': float(managed),
            'parent_win': bool(tr.pnl > 0), 'managed_win': bool(managed > 0),
            'failure60': failure60, 'upper_wick_dom': upper_wick_dom,
            'upper_wick_ratio': upper_wick_ratio, 'true_failure60': true_failure,
            'delta': float(delta), 'exit60_px': exit_px,
        })
    f517.assert_parent(parents)
    return pd.DataFrame(rows)


def contiguous_blocks(df, nblocks):
    # Deterministic contiguous equal-count partition of the 138 Friday trades.
    chunks = np.array_split(np.arange(len(df)), nblocks)
    out = []
    for b, idx in enumerate(chunks, start=1):
        g = df.iloc[idx]
        a = g[g.true_failure60]
        out.append({
            'block': b,
            'start_date': str(g.date.iloc[0]), 'end_date': str(g.date.iloc[-1]),
            'n_trades': int(len(g)), 'actions': int(len(a)),
            'delta': float(a.delta.sum()),
            'positive_actions': int((a.delta > 1e-12).sum()),
            'negative_actions': int((a.delta < -1e-12).sum()),
        })
    return out


def main():
    df = build_rows()
    df.to_csv(OUT / 'f65_rows.csv', index=False)
    sig = df[df.true_failure60].copy().reset_index(drop=True)

    # Exact F6.4 parity guards.
    if len(df) != 138:
        raise RuntimeError(f'parent N parity failed: {len(df)}')
    if len(sig) != 6:
        raise RuntimeError(f'action parity failed: {len(sig)}')
    if int((sig.period == 'discovery').sum()) != 2 or int((sig.period == 'validation').sum()) != 4:
        raise RuntimeError('D/V action parity failed')
    if int(sig.parent_win.sum()) != 0:
        raise RuntimeError('F6.4 parent-winner parity failed')

    full_delta = float(sig.delta.sum())
    d_delta = float(sig[sig.period == 'discovery'].delta.sum())
    v_delta = float(sig[sig.period == 'validation'].delta.sum())

    # Action-level jackknife: remove exactly one of the six frozen actions at a time.
    jack = []
    for j, r in sig.iterrows():
        remain = sig.drop(index=j)
        jack.append({
            'removed_date': str(r.date),
            'removed_delta': float(r.delta),
            'remaining_actions': int(len(remain)),
            'remaining_delta': float(remain.delta.sum()),
        })
    jdf = pd.DataFrame(jack)
    jdf.to_csv(OUT / 'f65_jackknife.csv', index=False)

    # Chronology: report both coarse 4-block and finer 8-block partitions.
    blocks4 = contiguous_blocks(df, 4)
    blocks8 = contiguous_blocks(df, 8)
    pd.DataFrame(blocks4).to_csv(OUT / 'f65_blocks4.csv', index=False)
    pd.DataFrame(blocks8).to_csv(OUT / 'f65_blocks8.csv', index=False)

    pos = sig[sig.delta > 0].sort_values('delta', ascending=False)
    gross_rescue = float(pos.delta.sum())
    adverse_clip = float(-sig[sig.delta < 0].delta.sum())
    top1 = float(pos.delta.iloc[0]) if len(pos) else 0.0
    top2 = float(pos.delta.iloc[:2].sum()) if len(pos) else 0.0
    top1_share = float(top1 / gross_rescue) if gross_rescue > 0 else np.nan
    top2_share = float(top2 / gross_rescue) if gross_rescue > 0 else np.nan

    action_blocks4 = [x for x in blocks4 if x['actions'] > 0]
    action_blocks8 = [x for x in blocks8 if x['actions'] > 0]

    result = {
        'frozen_rule': 'FAILURE_60 AND UPPER_WICK_DOM(>=50%) -> exit actual +60m open',
        'n_trades': int(len(df)), 'actions': int(len(sig)),
        'full_delta': full_delta, 'discovery_delta': d_delta, 'validation_delta': v_delta,
        'positive_actions': int((sig.delta > 1e-12).sum()),
        'negative_actions': int((sig.delta < -1e-12).sum()),
        'gross_rescue_positive_actions': gross_rescue,
        'gross_adverse_clipping': adverse_clip,
        'rescue_to_clip_ratio': float(gross_rescue / adverse_clip) if adverse_clip > 0 else math.inf,
        'best_action_delta': float(sig.delta.max()), 'worst_action_delta': float(sig.delta.min()),
        'jackknife_min_remaining_delta': float(jdf.remaining_delta.min()),
        'jackknife_max_remaining_delta': float(jdf.remaining_delta.max()),
        'jackknife_all_positive': bool((jdf.remaining_delta > 0).all()),
        'top1_share_of_positive_rescue': top1_share,
        'top2_share_of_positive_rescue': top2_share,
        'blocks4': blocks4, 'blocks8': blocks8,
        'action_blocks4_all_positive': bool(all(x['delta'] > 0 for x in action_blocks4)),
        'action_blocks8_positive_count': int(sum(x['delta'] > 0 for x in action_blocks8)),
        'action_blocks8_count': int(len(action_blocks8)),
        'winner_to_nonpositive': int(((df.parent_pnl > 0) & (df.managed_pnl <= 0)).sum()),
        'actions_detail': sig[['i','date','period','parent_pnl','managed_pnl','delta','upper_wick_ratio']].to_dict('records'),
    }

    # Predeclared robustness gate. No requirement that every individual action win;
    # F6.4 already showed one economically trivial adverse action. The question here
    # is whether aggregate benefit is stable when any single observation is removed.
    result['gate'] = {
        'full_delta_positive': bool(full_delta > 0),
        'discovery_positive': bool(d_delta > 0),
        'validation_positive': bool(v_delta > 0),
        'jackknife_all_positive': bool(result['jackknife_all_positive']),
        'four_block_action_buckets_positive': bool(result['action_blocks4_all_positive']),
        'no_parent_winner_clipped': bool(result['winner_to_nonpositive'] == 0),
        'positive_actions_majority': bool(result['positive_actions'] >= 4),
    }
    result['pass'] = bool(all(result['gate'].values()))

    (OUT / 'f65_summary.json').write_text(json.dumps(result, indent=2, default=float))

    money = lambda x: f'${x:+.3f}'
    md = [
        '# Friday15 F6.5 — Frozen Upper-Wick Cut Robust Tradeoff', '',
        f"**Status:** COMPLETE — {'ROBUST PASS' if result['pass'] else 'ROBUST FAIL'}",
        '**Research only; live BBC untouched. Rule unchanged from F6.4.**', '',
        '## Frozen economics',
        f"- Actions: **{result['actions']}** = {result['positive_actions']} positive / {result['negative_actions']} negative",
        f"- Full delta: **{money(full_delta)}**",
        f"- Discovery: **{money(d_delta)}**; Validation: **{money(v_delta)}**",
        f"- Gross rescued loss from positive actions: **{money(gross_rescue)}**",
        f"- Gross adverse clipping: **{money(adverse_clip)}**",
        f"- Rescue / adverse-clip ratio: **{result['rescue_to_clip_ratio']:.1f}x**", '',
        '## Jackknife',
        f"- Remove any one action: remaining delta range **{money(result['jackknife_min_remaining_delta'])} to {money(result['jackknife_max_remaining_delta'])}**",
        f"- All six leave-one-out cases remain positive: **{result['jackknife_all_positive']}**", '',
        '## Concentration',
        f"- Largest positive action = **{100*top1_share:.1f}%** of gross positive rescue",
        f"- Top two = **{100*top2_share:.1f}%** of gross positive rescue", '',
        '## Chronological blocks (4-way)',
    ]
    for x in blocks4:
        md.append(f"- B{x['block']} {x['start_date']}..{x['end_date']}: {x['actions']} actions, delta **{money(x['delta'])}**")
    md += ['', '## Chronological blocks (8-way)']
    for x in blocks8:
        md.append(f"- B{x['block']} {x['start_date']}..{x['end_date']}: {x['actions']} actions, delta **{money(x['delta'])}**")
    md += ['', '## Gate']
    for k, v in result['gate'].items():
        md.append(f'- {k}: **{v}**')
    md += ['', '## Interpretation',
           'F6.5 does not repair the one -$0.029 F6.4 action. It tests whether the unchanged six-action rule remains economically useful despite that exception. A ROBUST PASS means the aggregate rescue survives removal of any one action and transfers across chronology without clipping a parent winner.']
    (OUT / 'F6.5_CHECKPOINT.md').write_text('\n'.join(md) + '\n')
    print(json.dumps(result, indent=2, default=float), flush=True)


if __name__ == '__main__':
    main()
