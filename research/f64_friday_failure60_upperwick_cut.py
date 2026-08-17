#!/usr/bin/env python3
"""F6.4 — Friday15 frozen true-failure upper-wick cut counterfactual.
Research only; live BBC untouched.

Frozen from F6.3 (no threshold changes):
TRUE_FAILURE_60 iff:
- F6.1 FAILURE_60 is present at +60m, AND
- the final completed 5m candle before +60m has upper wick >= 50% of candle range.

Counterfactual action:
- exit at actual +60m open.
All other Friday trades keep the frozen parent unchanged.

Purpose:
Test whether the six F6.3 dominant-upper-wick failures are economically worth
cutting without broadening the rule, changing the 50% morphology threshold,
or adding any new filter.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60
import f63_friday_failure60_candle_morphology as f63

OUT = Path(os.getenv('F64_OUT', 'f64_out'))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = f517.SPLIT_N


def metrics(p):
    p = np.asarray(p, dtype=float)
    w = int((p > 0).sum())
    gp = float(p[p > 0].sum())
    gl = float(-p[p <= 0].sum())
    eq = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = float((peak[1:] - eq).max()) if len(eq) else 0.0
    ls = cur = 0
    for x in p:
        if x <= 0:
            cur += 1
            ls = max(ls, cur)
        else:
            cur = 0
    return {
        'n': int(len(p)), 'wins': w, 'losses': int(len(p)-w),
        'wr': float(w/len(p)) if len(p) else np.nan,
        'pnl': float(p.sum()), 'exp': float(p.mean()) if len(p) else np.nan,
        'pf': float(gp/gl) if gl > 0 else math.inf,
        'dd': dd, 'ls': int(ls),
        'gross_profit': gp, 'gross_loss': gl,
    }


def main():
    k = f517.load_klines()
    days = [d for d in pd.date_range(f517.START, f517.END, inclusive='left', freq='D') if d.weekday() == 4]
    rows = []
    parents = []

    for i, d in enumerate(days):
        t = pd.Timestamp(d.date(), tz='UTC') + pd.Timedelta(hours=8)  # 15:00 WIB
        tr = f517.simulate_parent(k, t)
        parents.append(tr)
        pf = f60.path_features(k, t, tr)
        failure60 = bool(
            pf['alive60'] and
            pf['progress60'] <= 0 and
            pf['taker60'] < 0 and
            pf['ema20_dist60'] <= 0
        )

        upper_wick_dom = False
        upper_wick_ratio = np.nan
        candle_body_ratio = np.nan
        candle_close_loc = np.nan
        managed = float(tr.pnl)
        exit_px = np.nan
        delta = 0.0

        if failure60:
            dt = t + pd.Timedelta(minutes=60)
            cf = f63.candle(k, dt, tr.entry)
            if cf is None:
                raise RuntimeError(f'missing completed 5m candle before +60m for {tr.date}')
            upper_wick_ratio = float(cf['upper_wick_ratio'])
            candle_body_ratio = float(cf['body_ratio'])
            candle_close_loc = float(cf['close_loc'])
            upper_wick_dom = bool(cf['UPPER_WICK_DOM'])

            if upper_wick_dom:
                exit_px = float(k.loc[dt, 'open'])
                managed = f517.NOTIONAL * (exit_px / tr.entry - 1.0) - f517.ROUND_TRIP_FEE
                delta = managed - float(tr.pnl)

        true_failure = bool(failure60 and upper_wick_dom)
        rows.append({
            'i': i,
            'period': 'discovery' if i < SPLIT else 'validation',
            'date': tr.date,
            'entry': tr.entry,
            'parent_pnl': float(tr.pnl),
            'parent_win': bool(tr.pnl > 0),
            'failure60': failure60,
            'upper_wick_dom': upper_wick_dom,
            'upper_wick_ratio': upper_wick_ratio,
            'body_ratio': candle_body_ratio,
            'close_loc': candle_close_loc,
            'true_failure60': true_failure,
            'progress60': pf['progress60'],
            'taker60': pf['taker60'],
            'ema20_dist60': pf['ema20_dist60'],
            'managed_pnl': float(managed),
            'managed_win': bool(managed > 0),
            'delta': float(delta),
            'exit60_px': exit_px,
            'improved': bool(delta > 1e-12),
            'damaged': bool(delta < -1e-12),
            'winner_to_loss': bool(tr.pnl > 0 and managed <= 0),
            'loss_to_win': bool(tr.pnl <= 0 and managed > 0),
        })

    f517.assert_parent(parents)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'f64_rows.csv', index=False)

    # F6.3 parity guard: exact frozen morphology signal must remain 6 = 2D + 4V,
    # and all six must be parent losers.
    sig = df[df.true_failure60]
    d_sig = sig[sig.i < SPLIT]
    v_sig = sig[sig.i >= SPLIT]
    if len(sig) != 6 or len(d_sig) != 2 or len(v_sig) != 4:
        raise RuntimeError(f'F6.3 signal parity failed: full={len(sig)}, D={len(d_sig)}, V={len(v_sig)}')
    if int(sig.parent_win.sum()) != 0:
        raise RuntimeError(f'F6.3 winner parity failed: {int(sig.parent_win.sum())}/6 parent winners')

    parent = metrics(df.parent_pnl)
    managed = metrics(df.managed_pnl)
    d = df[df.i < SPLIT]
    v = df[df.i >= SPLIT]

    action_stats = {
        'actions': int(len(sig)),
        'improved': int(sig.improved.sum()),
        'damaged': int(sig.damaged.sum()),
        'parent_loss_sum': float(sig.parent_pnl.sum()),
        'managed_loss_sum': float(sig.managed_pnl.sum()),
        'rescue_delta': float(sig.delta.sum()),
        'avg_parent_pnl': float(sig.parent_pnl.mean()),
        'avg_managed_pnl': float(sig.managed_pnl.mean()),
        'avg_delta': float(sig.delta.mean()),
        'best_delta': float(sig.delta.max()),
        'worst_delta': float(sig.delta.min()),
    }

    result = {
        'frozen_rule': 'FAILURE_60 AND UPPER_WICK_DOM(upper wick >= 50% range) -> exit actual +60m open',
        'parent': parent,
        'managed': managed,
        'delta': float(managed['pnl'] - parent['pnl']),
        'wr_delta_pp': float(100.0 * (managed['wr'] - parent['wr'])),
        'dd_delta': float(managed['dd'] - parent['dd']),
        'action_stats': action_stats,
        'winner_to_loss': int(df.winner_to_loss.sum()),
        'loss_to_win': int(df.loss_to_win.sum()),
        'discovery': {
            'parent': metrics(d.parent_pnl),
            'managed': metrics(d.managed_pnl),
            'delta': float(d.delta.sum()),
            'actions': int(d.true_failure60.sum()),
        },
        'validation': {
            'parent': metrics(v.parent_pnl),
            'managed': metrics(v.managed_pnl),
            'delta': float(v.delta.sum()),
            'actions': int(v.true_failure60.sum()),
        },
        'actions': sig[['i','period','date','parent_pnl','managed_pnl','delta','upper_wick_ratio','progress60','taker60','ema20_dist60']].to_dict('records'),
    }

    # Economic promotion gate: this intervention is designed to shrink known losses,
    # not manufacture wins. WR improvement is therefore reported but not required.
    result['gate'] = {
        'overall_delta_positive': bool(result['delta'] > 0),
        'discovery_delta_positive': bool(result['discovery']['delta'] > 0),
        'validation_delta_positive': bool(result['validation']['delta'] > 0),
        'no_winner_to_loss': bool(result['winner_to_loss'] == 0),
        'all_six_parent_losers': bool(int(sig.parent_win.sum()) == 0),
        'all_action_deltas_nonnegative': bool((sig.delta >= -1e-12).all()),
        'drawdown_nonworse': bool(managed['dd'] <= parent['dd'] + 1e-12),
    }
    result['pass'] = bool(all(result['gate'].values()))

    (OUT / 'f64_summary.json').write_text(json.dumps(result, indent=2, default=float))

    pct = lambda x: f'{100*x:.2f}%'
    money = lambda x: f'${x:+.3f}'
    md = [
        '# Friday15 F6.4 — Frozen TRUE_FAILURE Upper-Wick Cut', '',
        f"**Status:** COMPLETE — {'PASS' if result['pass'] else 'FAIL'}",
        '**Research only:** live BBC untouched', '',
        '## Frozen rule',
        '`FAILURE_60 AND UPPER_WICK_DOM (upper wick >=50% of final completed 5m candle range)` -> exit at actual +60m open.',
        'No threshold change, no extra filter, no alternate exit.', '',
        '## Result',
        f"- Parent: **{parent['wins']}W/{parent['losses']}L, WR {pct(parent['wr'])}, {money(parent['pnl'])}**, PF {parent['pf']:.3f}, DD {money(parent['dd'])}",
        f"- Managed: **{managed['wins']}W/{managed['losses']}L, WR {pct(managed['wr'])}, {money(managed['pnl'])}**, PF {managed['pf']:.3f}, DD {money(managed['dd'])}",
        f"- PnL delta: **{money(result['delta'])}**",
        f"- Actions: **{action_stats['actions']}**; improved {action_stats['improved']}; damaged {action_stats['damaged']}",
        f"- Six-action parent PnL: **{money(action_stats['parent_loss_sum'])}** -> managed **{money(action_stats['managed_loss_sum'])}**; rescue **{money(action_stats['rescue_delta'])}**",
        f"- Winner->loss: **{result['winner_to_loss']}**; loss->win: **{result['loss_to_win']}**", '',
        '## Chronology',
        f"- Discovery: {result['discovery']['actions']} actions, delta **{money(result['discovery']['delta'])}**",
        f"- Validation: {result['validation']['actions']} actions, delta **{money(result['validation']['delta'])}**", '',
        '## Gate',
    ]
    for k0, v0 in result['gate'].items():
        md.append(f'- {k0}: **{v0}**')
    md += ['', '## Interpretation',
           'This milestone only asks whether the frozen F6.3 dominant-upper-wick subset is economically worth cutting. It does not generalize the signal to the other FAILURE_60 trades and does not change Friday entry/TP/SL/hold geometry.']
    (OUT / 'F6.4_CHECKPOINT.md').write_text('\n'.join(md) + '\n')
    print(json.dumps(result, indent=2, default=float), flush=True)


if __name__ == '__main__':
    main()
