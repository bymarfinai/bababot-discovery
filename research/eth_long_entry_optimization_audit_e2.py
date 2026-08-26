#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX = 'ETH_LONG_ENTRY_OPTIMIZATION_AUDIT_E2'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SEL = ROOT / f'{PFX}_Selection.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
DEPTHS = (0.65, 0.675, 0.70, 0.725, 0.75, 0.775, 0.80)
MODES = (
    'BLIND_LIMIT',
    'BLIND_NEXT_OPEN',
    'SAME_BAR_REJECTION_NEXT_OPEN',
    'EARLY_RECLAIM_NEXT_OPEN',
    'NEXT_BAR_CONFIRM_NEXT_OPEN',
    'SAME_BAR_REJECTION_CLOSE_DIAG',
    'EARLY_RECLAIM_CLOSE_DIAG',
)
SELECTABLE = MODES[:5]
TARGET_EXT = 0.10
BOUND_FRAC = 0.15
NOTIONAL = 500.0
FEE = 0.40


def fs(x: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(b, side='left'))
    return x.iloc[i:j]


def load_windows() -> pd.DataFrame:
    w = pd.read_csv(WINDOWS)
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','terminal_bar_start','session_end'):
        if c in w.columns:
            w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    needed = {'partition','date_utc','signal_ts','eligible_start','terminal_bar_start','session_end','H','L','range','window_status'}
    missing = needed.difference(w.columns)
    if missing:
        raise AssertionError(f'missing window columns: {sorted(missing)}')
    if w.duplicated(['partition','date_utc','signal_ts']).any():
        raise AssertionError('duplicate frozen window identity')
    return w.sort_values(['partition','signal_ts']).reset_index(drop=True)


def preterminal_slice(x5: pd.DataFrame, r) -> tuple[pd.DataFrame, pd.Timestamp]:
    if pd.isna(r.eligible_start):
        return x5.iloc[0:0], pd.NaT
    start = pd.Timestamp(r.eligible_start)
    terminal = pd.Timestamp(r.terminal_bar_start) if pd.notna(r.terminal_bar_start) else pd.Timestamp(r.session_end)
    if terminal <= start:
        return x5.iloc[0:0], terminal
    return fs(x5, start, terminal), terminal


def first_touch(x5: pd.DataFrame, r, frac: float):
    H = float(r.H); L = float(r.L); R = float(r.range); level = L + frac * R
    q, terminal = preterminal_slice(x5, r)
    if q.empty:
        return pd.NaT, level, terminal
    for ts, b in q.iterrows():
        if float(b.low) <= level <= float(b.high):
            return pd.Timestamp(ts), level, terminal
    return pd.NaT, level, terminal


def bar_at(x5: pd.DataFrame, ts: pd.Timestamp):
    p = int(x5.index.searchsorted(ts, side='left'))
    if p >= len(x5) or x5.index[p] != ts:
        raise AssertionError(f'missing 5m bar {ts}')
    return x5.iloc[p]


def confirmation_for_mode(x5: pd.DataFrame, r, touch: pd.Timestamp, level: float, terminal: pd.Timestamp, mode: str):
    if pd.isna(touch):
        return pd.NaT, 'NO_TOUCH'
    if mode in ('BLIND_LIMIT','BLIND_NEXT_OPEN'):
        return touch, 'TOUCH'

    if mode in ('SAME_BAR_REJECTION_NEXT_OPEN','SAME_BAR_REJECTION_CLOSE_DIAG'):
        b = bar_at(x5, touch)
        if float(b.close) > level:
            return touch, 'SAME_BAR_REJECTION'
        return pd.NaT, 'NO_SAME_BAR_REJECTION'

    if mode in ('EARLY_RECLAIM_NEXT_OPEN','EARLY_RECLAIM_CLOSE_DIAG'):
        q = fs(x5, touch, terminal)
        for ts, b in q.iterrows():
            if float(b.close) > level:
                return pd.Timestamp(ts), 'EARLY_RECLAIM'
        return pd.NaT, 'NO_RECLAIM_PRE_TERMINAL'

    if mode == 'NEXT_BAR_CONFIRM_NEXT_OPEN':
        confirm = touch + BAR5
        # Confirmation must complete before a terminal event bar begins.
        if confirm >= terminal:
            return pd.NaT, 'NO_NEXT_BAR_PRE_TERMINAL'
        b = bar_at(x5, confirm)
        if float(b.close) > level:
            return confirm, 'NEXT_BAR_CONFIRM'
        return pd.NaT, 'NEXT_BAR_NOT_ABOVE_LEVEL'

    raise ValueError(mode)


def build_entry(x5: pd.DataFrame, r, frac: float, mode: str) -> dict:
    H = float(r.H); L = float(r.L); R = float(r.range)
    touch, level, terminal = first_touch(x5, r, frac)
    base = {
        'partition': r.partition, 'date_utc': r.date_utc, 'signal_ts': pd.Timestamp(r.signal_ts),
        'window_status': r.window_status, 'depth': frac, 'depth_name': f'F{frac*100:g}', 'mode': mode,
        'H': H, 'L': L, 'range': R, 'entry_level': level,
        'touch_bar_start': touch, 'terminal_bar_start': terminal, 'session_end': pd.Timestamp(r.session_end),
    }
    if pd.isna(touch):
        return {**base, 'confirmation_bar_start': pd.NaT, 'entry_executed': False,
                'entry_status': 'NO_TOUCH', 'entry_ts': pd.NaT, 'entry_px': np.nan,
                'entry_fraction_actual': np.nan, 'partial_entry_bar': False}

    conf, conf_status = confirmation_for_mode(x5, r, touch, level, terminal, mode)
    if pd.isna(conf):
        return {**base, 'confirmation_bar_start': pd.NaT, 'entry_executed': False,
                'entry_status': conf_status, 'entry_ts': pd.NaT, 'entry_px': np.nan,
                'entry_fraction_actual': np.nan, 'partial_entry_bar': False}

    if mode == 'BLIND_LIMIT':
        entry_ts = touch
        entry_px = level
        partial = True
    elif mode.endswith('_CLOSE_DIAG'):
        # Diagnostic: assume exact fill at the completed confirmation close; position exists from next bar start.
        b = bar_at(x5, conf)
        entry_ts = conf + BAR5
        entry_px = float(b.close)
        partial = False
    else:
        entry_ts = conf + BAR5
        if entry_ts >= pd.Timestamp(r.session_end):
            return {**base, 'confirmation_bar_start': conf, 'entry_executed': False,
                    'entry_status': 'NO_NEXT_OPEN', 'entry_ts': entry_ts, 'entry_px': np.nan,
                    'entry_fraction_actual': np.nan, 'partial_entry_bar': False}
        if entry_ts > terminal:
            return {**base, 'confirmation_bar_start': conf, 'entry_executed': False,
                    'entry_status': 'ENTRY_AFTER_TERMINAL', 'entry_ts': entry_ts, 'entry_px': np.nan,
                    'entry_fraction_actual': np.nan, 'partial_entry_bar': False}
        entry_px = float(bar_at(x5, entry_ts).open)
        partial = False

    actual = (entry_px - L) / R
    boundary = L + BOUND_FRAC * R
    if not (boundary < entry_px < H):
        return {**base, 'confirmation_bar_start': conf, 'entry_executed': False,
                'entry_status': 'INVALID_ENTRY_GEOMETRY', 'entry_ts': entry_ts, 'entry_px': entry_px,
                'entry_fraction_actual': actual, 'partial_entry_bar': partial}

    return {**base, 'confirmation_bar_start': conf, 'entry_executed': True,
            'entry_status': conf_status, 'entry_ts': entry_ts, 'entry_px': entry_px,
            'entry_fraction_actual': actual, 'partial_entry_bar': partial}


def solve_exit(x5: pd.DataFrame, e: dict) -> dict:
    if not e['entry_executed']:
        return {'exit_ts': pd.NaT, 'exit_px': np.nan, 'exit_reason': 'NO_ENTRY',
                'net_pnl_usd': np.nan, 'hold_minutes': np.nan, 'mae_r': np.nan, 'mfe_r': np.nan}
    entry_ts = pd.Timestamp(e['entry_ts']); end = pd.Timestamp(e['session_end'])
    entry = float(e['entry_px']); H = float(e['H']); L = float(e['L']); R = float(e['range'])
    target = H + TARGET_EXT * R; boundary = L + BOUND_FRAC * R
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError('missing entry bar for exit')

    reason = None; exit_ts = pd.NaT; exit_px = np.nan; exit_k = None
    partial = bool(e['partial_entry_bar'])
    for k, (ts, b) in enumerate(q.iterrows()):
        hi = float(b.high); cl = float(b.close)
        if not (partial and k == 0) and hi >= target:
            reason = 'TP_E10'; exit_ts = pd.Timestamp(ts); exit_px = target; exit_k = k; break
        if cl < boundary:
            reason = 'CLOSE_INVALIDATION_F15'; exit_ts = pd.Timestamp(ts) + BAR5; exit_px = cl; exit_k = k; break
    if reason is None:
        p = int(x5.index.searchsorted(end, side='left'))
        if p >= len(x5) or x5.index[p] != end:
            raise AssertionError('missing session-end bar')
        reason = 'TIME_EXIT_SESSION_END'; exit_ts = end; exit_px = float(x5.iloc[p].open); exit_k = len(q) - 1

    # MAE/MFE exclude the ambiguous fill bar for an intrabar BLIND_LIMIT fill.
    start_k = 1 if partial else 0
    path = q.iloc[start_k:exit_k+1] if exit_k is not None and exit_k >= start_k else q.iloc[0:0]
    if len(path):
        min_low = float(path.low.min()); max_high = float(path.high.max())
        mae = max(0.0, (entry - min_low) / R)
        mfe = max(0.0, (max_high - entry) / R)
    else:
        mae = mfe = 0.0
    net = (float(exit_px) / entry - 1.0) * NOTIONAL - FEE
    return {'exit_ts': exit_ts, 'exit_px': float(exit_px), 'exit_reason': reason,
            'net_pnl_usd': float(net), 'hold_minutes': float((exit_ts-entry_ts)/pd.Timedelta(minutes=1)),
            'mae_r': float(mae), 'mfe_r': float(mfe)}


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_ls(vals):
    best = cur = 0
    for v in vals:
        if float(v) <= 0: cur += 1; best = max(best, cur)
        else: cur = 0
    return best


def metrics(g: pd.DataFrame, opps: int) -> dict:
    ex = g[g.entry_executed.astype(bool)].sort_values('entry_ts').copy() if len(g) else g
    if not len(ex):
        return {'opportunities':opps,'n':0,'exec_rate':0.0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'net':0.0,
                'max_ls':0,'median_actual_f':np.nan,'median_mae_r':np.nan,'median_mfe_r':np.nan,'tp_rate':np.nan}
    p = ex.net_pnl_usd.astype(float)
    return {'opportunities':opps,'n':len(ex),'exec_rate':len(ex)/opps if opps else np.nan,
            'wr':float((p>0).mean()),'pf':float(pf(p)),'exp':float(p.mean()),'net':float(p.sum()),
            'max_ls':max_ls(p.tolist()),'median_actual_f':float(ex.entry_fraction_actual.median()),
            'median_mae_r':float(ex.mae_r.median()),'median_mfe_r':float(ex.mfe_r.median()),
            'tp_rate':float((ex.exit_reason=='TP_E10').mean())}


def dev_base_ok(r) -> bool:
    return bool(r.n >= 30 and r.wr >= 0.70 and r.pf >= 1.20 and r.exp > 0)


def dev_neighbor_ok(r) -> bool:
    return bool(r.n >= 30 and r.wr >= 0.68 and r.pf >= 1.10 and r.exp > 0)


def select_from_development(sm: pd.DataFrame) -> pd.DataFrame:
    dev = sm[(sm.partition=='development') & sm['mode'].isin(SELECTABLE)].copy()
    rows=[]
    for mode in SELECTABLE:
        m = dev[dev['mode']==mode].set_index('depth')
        for i, f in enumerate(DEPTHS):
            if f not in m.index: continue
            c = m.loc[f]
            if not dev_base_ok(c): continue
            neigh=[]
            for j in (i-1,i+1):
                if 0 <= j < len(DEPTHS):
                    nf=DEPTHS[j]
                    if nf in m.index and dev_neighbor_ok(m.loc[nf]):
                        neigh.append(nf)
            if not neigh: continue
            for nf in neigh:
                n=m.loc[nf]
                rows.append({'mode':mode,'depth':f,'neighbor_depth':nf,
                             'robustness_pf':min(float(c.pf),float(n.pf)),
                             'robustness_exp':min(float(c.exp),float(n.exp)),
                             'center_pf':float(c.pf),'center_exp':float(c.exp),
                             'center_wr':float(c.wr),'center_n':int(c.n),
                             'neighbor_pf':float(n.pf),'neighbor_exp':float(n.exp),
                             'neighbor_wr':float(n.wr),'neighbor_n':int(n.n)})
    if not rows:
        return pd.DataFrame(columns=['mode','depth','neighbor_depth','robustness_pf','robustness_exp','center_pf','center_exp','center_wr','center_n','neighbor_pf','neighbor_exp','neighbor_wr','neighbor_n'])
    z=pd.DataFrame(rows).sort_values(['robustness_pf','robustness_exp','center_pf','center_exp'],ascending=[False,False,False,False]).reset_index(drop=True)
    return z


def validation_gate(sm: pd.DataFrame, selected: pd.Series):
    mode=selected['mode']; depth=float(selected['depth'])
    # All neighbors qualifying in development are frozen before validation; at least one must validate.
    sel=select_from_development(sm)
    nbrs=sorted(set(sel[(sel['mode']==mode)&np.isclose(sel.depth,depth)].neighbor_depth.astype(float).tolist()))
    val=sm[(sm.partition=='reference_validation')&(sm['mode']==mode)]
    center=val[np.isclose(val.depth,depth)]
    center_ok=False
    if len(center)==1:
        r=center.iloc[0]
        center_ok=bool(r.n>=15 and r.wr>=.70 and r.pf>=1.20 and r.exp>0)
    nbr_eval=[]; neighbor_ok=False
    for nf in nbrs:
        q=val[np.isclose(val.depth,nf)]
        ok=False
        if len(q)==1:
            r=q.iloc[0]; ok=bool(r.n>=15 and r.wr>=.65 and r.pf>=1.00 and r.exp>0)
        nbr_eval.append((nf,ok))
        neighbor_ok = neighbor_ok or ok
    return center_ok, neighbor_ok, nbr_eval


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'


def synthetic_tests():
    # A causal touch/rejection case that distinguishes limit vs next-open execution.
    idx=pd.date_range('2026-01-05 14:00',periods=6,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':97.0,'high':98.0,'low':96.0,'close':97.8},
        {'open':98.2,'high':99.0,'low':97.7,'close':98.8},
        {'open':98.8,'high':101.2,'low':98.5,'close':100.5},
        {'open':100.5,'high':102,'low':100,'close':101.2},
        {'open':101.2,'high':102,'low':100.5,'close':101.0},
        {'open':101.0,'high':102,'low':100.8,'close':101.1},
    ],index=idx)
    class R: pass
    r=R(); r.partition='x'; r.date_utc='2026-01-05'; r.signal_ts=idx[0]-BAR5; r.window_status='H2_ARRIVAL'
    r.eligible_start=idx[0]; r.terminal_bar_start=idx[2]; r.session_end=idx[-1]+BAR5; r.H=100.; r.L=90.; r.range=10.
    e=build_entry(x,r,.75,'SAME_BAR_REJECTION_NEXT_OPEN')
    assert e['entry_executed'] and e['entry_ts']==idx[1] and abs(e['entry_px']-98.2)<1e-12
    b=build_entry(x,r,.75,'BLIND_LIMIT')
    assert b['entry_executed'] and b['entry_ts']==idx[0] and abs(b['entry_px']-97.5)<1e-12


def main():
    synthetic_tests()
    x5, coverage = ethdata.load5()
    w = load_windows()
    rows=[]
    for r in w.itertuples(index=False):
        for f in DEPTHS:
            for mode in MODES:
                e=build_entry(x5,r,f,mode)
                rows.append({**e,**solve_exit(x5,e)})
    d=pd.DataFrame(rows).sort_values(['partition','mode','depth','signal_ts']).reset_index(drop=True)
    d.to_csv(OUT_TRADES,index=False)

    sums=[]
    for part in PARTS:
        opp=int((w.partition==part).sum())
        for mode in MODES:
            for f in DEPTHS:
                g=d[(d.partition==part)&(d['mode']==mode)&np.isclose(d.depth,f)]
                sums.append({'partition':part,'mode':mode,'depth':f,'depth_name':f'F{f*100:g}',**metrics(g,opp)})
    sm=pd.DataFrame(sums)
    sm.to_csv(OUT_SUM,index=False)

    selected=select_from_development(sm)
    if len(selected):
        winner=selected.iloc[0].copy()
        center_ok,neighbor_ok,nbr_eval=validation_gate(sm,winner)
        winner['validation_center_ok']=center_ok; winner['validation_neighbor_ok']=neighbor_ok
        winner['validation_pass']=bool(center_ok and neighbor_ok)
        winner['validation_neighbor_results']=';'.join(f'F{x*100:g}:{"PASS" if ok else "FAIL"}' for x,ok in nbr_eval)
        status='ETH_LONG_ENTRY_OPTIMIZATION_E2_ROBUST_PLATEAU_SUPPORTED' if bool(winner['validation_pass']) else 'ETH_LONG_ENTRY_OPTIMIZATION_E2_VALIDATION_FAILED'
        outsel=pd.DataFrame([winner])
    else:
        winner=None; status='ETH_LONG_ENTRY_OPTIMIZATION_E2_NO_DEVELOPMENT_PLATEAU'
        outsel=pd.DataFrame(columns=list(selected.columns)+['validation_center_ok','validation_neighbor_ok','validation_pass','validation_neighbor_results'])
    outsel.to_csv(OUT_SEL,index=False)
    OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG Entry Optimization Audit E2 — Result','',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**; frozen windows: **{len(w):,}**.','',
        'Frozen economics: E10 target + D60/F15 completed-close invalidation, $500 fixed notional, $0.40 fee. Selection uses development only; diagnostic close-fill modes cannot be selected.','',
        '## Development entry surface (selectable modes)','',
        '| Mode | Depth | N | WR | PF | Exp | Net | Exec | Median actual f | MAE/R | MFE/R | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    dev=sm[(sm.partition=='development')&sm['mode'].isin(SELECTABLE)]
    for r in dev.itertuples(index=False):
        md.append(f'| {r.mode} | {r.depth_name} | {r.n} | {pct(r.wr)} | {num(r.pf)} | ${num(r.exp)} | ${num(r.net)} | {pct(r.exec_rate)} | {num(r.median_actual_f)} | {num(r.median_mae_r)} | {num(r.median_mfe_r)} | {r.max_ls} |')

    md += ['','## Development plateau selection','']
    if winner is None:
        md += ['No executable mode/depth satisfied the preregistered development center + adjacent-depth plateau gate.']
    else:
        mode=str(winner['mode']); depth=float(winner['depth']); nf=float(winner['neighbor_depth'])
        md += [f'Frozen development winner: **{mode} / F{depth*100:g}**, qualifying adjacent depth **F{nf*100:g}**.',
               f'Robustness PF floor: **{num(winner["robustness_pf"])}**; robustness expectancy floor: **${num(winner["robustness_exp"])}**.','',
               '### Frozen winner across partitions','',
               '| Partition | Depth | N | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for part in PARTS:
            for f in sorted(set([depth,nf])):
                q=sm[(sm.partition==part)&(sm['mode']==mode)&np.isclose(sm.depth,f)]
                if len(q):
                    r=q.iloc[0]; md.append(f'| {part} | F{f*100:g} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.exp)} | ${num(r.net)} | {int(r.max_ls)} |')
        md += ['',f'Validation center: **{"PASS" if bool(winner["validation_center_ok"]) else "FAIL"}**; validation neighbor: **{"PASS" if bool(winner["validation_neighbor_ok"]) else "FAIL"}** ({winner["validation_neighbor_results"]}).']

    md += ['','## Diagnostic confirmation-close executions (not selectable)','',
           '| Partition | Mode | Depth | N | WR | PF | Exp | Net |','|---|---|---:|---:|---:|---:|---:|---:|']
    diag=sm[(sm.partition.isin(('development','reference_validation')))&(~sm['mode'].isin(SELECTABLE))]
    for r in diag.itertuples(index=False):
        md.append(f'| {r.partition} | {r.mode} | {r.depth_name} | {r.n} | {pct(r.wr)} | {num(r.pf)} | ${num(r.exp)} | ${num(r.net)} |')

    md += ['',f'**Status: {status}**','', 'Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
