#!/usr/bin/env python3
"""C6: selective walk-forward BTC Friday 15m AI candle identifier.

Every scored Friday is predicted only from models fit on strictly earlier Fridays.
At most one highest-confidence candle is traded per Friday, and only at p>=0.80.
"""
from __future__ import annotations

import json, math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parent.parent
C4 = ROOT / 'BTC_Friday_15m_Candle_Taker_C4_Rows.csv'
C5 = ROOT / 'BTC_Friday_15m_Derivatives_C5_Rows.csv'
OUT_MD = ROOT / 'BTC_Friday_Selective_AI_C6_Result.md'
OUT_JSON = ROOT / 'BTC_Friday_Selective_AI_C6_Result.json'
OUT_CSV = ROOT / 'BTC_Friday_Selective_AI_C6_Predictions.csv'

WARMUP_FRIDAYS = 52
THRESHOLD = 0.80
SEED = 20260819
FEATURES = [
    'signal_ret','body_ratio','upper_ratio','lower_ratio','close_pos','range_open','prior1h_ret',
    'taker_imbalance','taker_delta_vs_prior3','rel_quote_volume_24h','rel_range_prior12',
    'top_vs_global','top_pos_chg15','global_chg15','taker_log','oi_chg15','oi_chg60',
]


def model():
    return HistGradientBoostingClassifier(
        loss='log_loss', learning_rate=0.05, max_iter=100, max_depth=3,
        min_samples_leaf=30, l2_regularization=1.0, random_state=SEED,
    )


def load_rows():
    if not C4.exists() or not C5.exists():
        raise RuntimeError('C4/C5 row artifacts required')
    a = pd.read_csv(C4)
    b = pd.read_csv(C5)
    keep_a = ['signal_ts','taker_imbalance','taker_delta_vs_prior3','rel_quote_volume_24h','rel_range_prior12',
              'cont_pnl','cont_win','rev_pnl','rev_win']
    missing_a = [c for c in keep_a if c not in a.columns]
    missing_b = [c for c in ['signal_ts','friday_wib','entry_ts'] + FEATURES[:7] + FEATURES[11:] +
                 ['cont_pnl','cont_win','rev_pnl','rev_win'] if c not in b.columns]
    if missing_a or missing_b:
        raise RuntimeError(f'missing C4={missing_a} C5={missing_b}')
    a = a[keep_a].copy()
    z = b.merge(a, on='signal_ts', how='inner', suffixes=('_c5','_c4'), validate='one_to_one')
    if z.empty:
        raise RuntimeError('empty C4/C5 inner join')
    violations = 0
    for stem in ('cont_pnl','rev_pnl'):
        d = (pd.to_numeric(z[f'{stem}_c5']) - pd.to_numeric(z[f'{stem}_c4'])).abs()
        violations += int((d > 1e-9).sum())
    for stem in ('cont_win','rev_win'):
        violations += int((pd.to_numeric(z[f'{stem}_c5']).astype(int) != pd.to_numeric(z[f'{stem}_c4']).astype(int)).sum())
    z['cont_pnl'] = pd.to_numeric(z['cont_pnl_c5'])
    z['rev_pnl'] = pd.to_numeric(z['rev_pnl_c5'])
    z['cont_win'] = pd.to_numeric(z['cont_win_c5']).astype(int)
    z['rev_win'] = pd.to_numeric(z['rev_win_c5']).astype(int)
    for c in FEATURES[:7] + FEATURES[11:]:
        z[c] = pd.to_numeric(z[c], errors='coerce')
    for c in FEATURES[7:11]:
        z[c] = pd.to_numeric(z[c], errors='coerce')
    z['signal_ts'] = pd.to_datetime(z.signal_ts, utc=True)
    z['entry_ts'] = pd.to_datetime(z.entry_ts, utc=True)
    z['friday_wib'] = z.friday_wib.astype(str)
    green = z.signal_ret > 0
    z['long_win'] = np.where(green, z.cont_win, z.rev_win).astype(int)
    z['short_win'] = np.where(green, z.rev_win, z.cont_win).astype(int)
    z['long_pnl'] = np.where(green, z.cont_pnl, z.rev_pnl).astype(float)
    z['short_pnl'] = np.where(green, z.rev_pnl, z.cont_pnl).astype(float)
    z = z.sort_values(['friday_wib','signal_ts']).reset_index(drop=True)
    return z, violations


def pwin(clf, X):
    if 1 not in clf.classes_:
        return np.zeros(len(X), dtype=float)
    j = list(clf.classes_).index(1)
    return clf.predict_proba(X)[:, j]


def pf(vals):
    gp = sum(v for v in vals if v > 0)
    gl = -sum(v for v in vals if v < 0)
    return gp/gl if gl > 0 else (999.0 if gp > 0 else None)


def stats(rows):
    vals = [float(r['actual_pnl']) for r in rows]
    if not vals:
        return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    wins = sum(v > 0 for v in vals)
    return {'n':len(vals),'wins':wins,'wr':wins/len(vals),'pnl':sum(vals),'exp':sum(vals)/len(vals),'pf':pf(vals)}


def block_report(top_rows, traded_rows, scored_dates):
    chunks = np.array_split(np.array(scored_dates, dtype=object), 4)
    out = {}
    for i,ch in enumerate(chunks):
        ds = set(ch.tolist())
        tr = [r for r in traded_rows if r['friday_wib'] in ds]
        out[f'B{i+1}'] = {'scored_fridays':len(ds), **stats(tr)}
    return out


def calibration(top_rows):
    buckets = [
        ('<0.50', -1.0, 0.50), ('0.50-0.60',0.50,0.60), ('0.60-0.70',0.60,0.70),
        ('0.70-0.80',0.70,0.80), ('>=0.80',0.80,2.0),
    ]
    out = {}
    for name,lo,hi in buckets:
        z = [r for r in top_rows if r['confidence'] >= lo and r['confidence'] < hi]
        if not z:
            out[name] = {'n':0,'wins':0,'wr':None,'mean_confidence':None,'pnl':0.0}
            continue
        wins = sum(int(r['actual_win']) for r in z)
        out[name] = {'n':len(z),'wins':wins,'wr':wins/len(z),
                     'mean_confidence':float(np.mean([r['confidence'] for r in z])),
                     'pnl':float(sum(r['actual_pnl'] for r in z))}
    return out


def main():
    df, integrity = load_rows()
    dates = sorted(df.friday_wib.unique())
    if len(dates) <= WARMUP_FRIDAYS:
        raise RuntimeError(f'only {len(dates)} Fridays')
    top_rows = []
    train_leak = 0
    for ix, day in enumerate(dates[WARMUP_FRIDAYS:], start=WARMUP_FRIDAYS):
        train_dates = set(dates[:ix])
        train = df[df.friday_wib.isin(train_dates)].copy()
        test = df[df.friday_wib == day].copy()
        if train.empty or test.empty:
            continue
        if max(train.friday_wib) >= day:
            train_leak += 1
        med = {}
        Xtr = train[FEATURES].copy()
        Xte = test[FEATURES].copy()
        for f in FEATURES:
            trv = pd.to_numeric(Xtr[f],errors='coerce').replace([np.inf,-np.inf],np.nan)
            m = float(trv.median())
            if not math.isfinite(m):
                m = 0.0
            med[f] = m
            Xtr[f] = trv.fillna(m)
            Xte[f] = pd.to_numeric(Xte[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(m)
        ml = model(); ms = model()
        ml.fit(Xtr, train.long_win.astype(int))
        ms.fit(Xtr, train.short_win.astype(int))
        pl = pwin(ml, Xte); ps = pwin(ms, Xte)
        candidates = []
        for j,(rid,row) in enumerate(test.iterrows()):
            if pl[j] >= ps[j]:
                side='LONG'; conf=float(pl[j]); aw=int(row.long_win); ap=float(row.long_pnl)
            else:
                side='SHORT'; conf=float(ps[j]); aw=int(row.short_win); ap=float(row.short_pnl)
            candidates.append({'friday_wib':day,'signal_ts':str(row.signal_ts),'entry_ts':str(row.entry_ts),
                               'direction':side,'p_long':float(pl[j]),'p_short':float(ps[j]),'confidence':conf,
                               'actual_win':aw,'actual_pnl':ap,'training_fridays':ix,'training_rows':len(train)})
        candidates.sort(key=lambda r:(-r['confidence'], pd.Timestamp(r['signal_ts'])))
        top_rows.append(candidates[0])
        print(day, candidates[0]['direction'], f"p={candidates[0]['confidence']:.4f}",
              'WIN' if candidates[0]['actual_win'] else 'LOSS', f"pnl={candidates[0]['actual_pnl']:.3f}")
    traded = [r for r in top_rows if r['confidence'] >= THRESHOLD]
    scored_dates = [r['friday_wib'] for r in top_rows]
    s = stats(traded)
    blocks = block_report(top_rows,traded,scored_dates)
    qualifying_blocks = sum(v['n'] >= 5 and v['pnl'] > 0 and v['wr'] is not None and v['wr'] >= .65 for v in blocks.values())
    side = {sd:stats([r for r in traded if r['direction']==sd]) for sd in ('LONG','SHORT')}
    cal = calibration(top_rows)
    all_integrity = integrity + train_leak
    qualify = bool(s['n'] >= 30 and s['wr'] is not None and s['wr'] >= .80 and s['pnl'] > 0 and
                   s['exp'] is not None and s['exp'] > 0 and s['pf'] is not None and s['pf'] > 1.30 and
                   qualifying_blocks >= 3 and all_integrity == 0)
    verdict = 'BTC_FRIDAY_C6_SELECTIVE_AI_80_CANDIDATE' if qualify else 'REJECT_C6_SELECTIVE_AI_IDENTIFIER'
    out = {
        'protocol':'C6','source_join_rows':len(df),'friday_dates_total':len(dates),'warmup_fridays':WARMUP_FRIDAYS,
        'oos_fridays_scored':len(top_rows),'threshold':THRESHOLD,'selected_trades':s,
        'trade_coverage_pct':100*len(traded)/len(top_rows) if top_rows else 0.0,
        'side':side,'blocks':blocks,'qualifying_blocks':qualifying_blocks,'calibration':cal,
        'integrity':{'source_outcome_mismatches':integrity,'training_current_friday_leaks':train_leak,'total':all_integrity},
        'model':{'type':'HistGradientBoostingClassifier','learning_rate':0.05,'max_iter':100,'max_depth':3,
                 'min_samples_leaf':30,'l2_regularization':1.0,'random_state':SEED},
        'features':FEATURES,'verdict':verdict,
        'guardrail':'One top candidate per pseudo-OOS Friday; fixed p>=0.80; no post-result threshold/model/feature rescue.'
    }
    pd.DataFrame(top_rows).to_csv(OUT_CSV,index=False)
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2): return '-' if x is None else f'{x:.{d}f}'
    md = ['# BTC Friday C6 — Selective Walk-Forward AI Result','',
          f"**Verdict: {verdict}**",'',
          f"Source joined rows: **{len(df)}**; Fridays total: **{len(dates)}**; warmup: **{WARMUP_FRIDAYS}**; pseudo-OOS Fridays scored: **{len(top_rows)}**.",
          f"Fixed confidence threshold: **{THRESHOLD:.2f}**; trades: **{s['n']}** ({F(out['trade_coverage_pct'])}% coverage).",
          f"Integrity violations: **{all_integrity}**.",'',
          '## Pseudo-OOS selected trades','',
          '| Trades | Wins | WR | PnL | Exp/trade | PF |','|---:|---:|---:|---:|---:|---:|',
          f"| {s['n']} | {s['wins']} | {F(100*s['wr'] if s['wr'] is not None else None)}% | ${F(s['pnl'])} | ${F(s['exp'],3)} | {F(s['pf'],3)} |",'',
          '## Four chronological OOS blocks','',
          '| Block | Scored Fridays | Trades | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for b,v in blocks.items():
        md.append(f"| {b} | {v['scored_fridays']} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | ${F(v['pnl'])} | {F(v['pf'],3)} |")
    md += ['', '## Top-candidate calibration by fixed probability bucket','',
           '| Bucket | Fridays | Wins | Observed WR | Mean confidence | PnL |','|---|---:|---:|---:|---:|---:|']
    for b,v in cal.items():
        md.append(f"| {b} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | {F(100*v['mean_confidence'] if v['mean_confidence'] is not None else None)}% | ${F(v['pnl'])} |")
    md += ['', '## Direction attribution','', '| Direction | Trades | WR | PnL | PF |','|---|---:|---:|---:|---:|']
    for sd,v in side.items():
        md.append(f"| {sd} | {v['n']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | ${F(v['pnl'])} | {F(v['pf'],3)} |")
    md += ['', f"Promotion-quality blocks: **{qualifying_blocks}/4**.", '',
           'Every Friday shown after warmup is pseudo-OOS: the model was fitted only on strictly earlier Fridays. Observed WR is not a guaranteed future probability.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))

if __name__ == '__main__':
    main()
