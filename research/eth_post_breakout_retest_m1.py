#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
spec = importlib.util.spec_from_file_location('eth_m2_base', BASE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

PFX = 'ETH_POST_BREAKOUT_RETEST_M1'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_TARGETS = ROOT / f'{PFX}_Targets.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
M2_STATUS = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt'
M2_WIN = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Windows.csv'
EXPECTED = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'
CLOCKS = ('ALT_0330', 'RAW_0530', 'LONDON', 'RAW_2330')
TARGETS = {'E05': .05, 'E10': .10, 'E20': .20, 'E30': .30}


def require_upstream():
    if not M2_STATUS.exists() or M2_STATUS.read_text().strip() != EXPECTED:
        raise RuntimeError('corrected M2 status gate failed')
    if not M2_WIN.exists():
        raise RuntimeError('corrected M2 windows missing')


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(['true', '1', 'yes'])


def locate_setup(q: pd.DataFrame, H: float, L: float, h2_ts: pd.Timestamp):
    post = q[q.index >= h2_ts]
    breakout = pd.NaT
    for ts, r in post.iterrows():
        cl = float(r.close)
        if cl < L:
            return {'breakout_state': 'PRE_BREAKOUT_COLLAPSE', 'breakout_ts': pd.NaT,
                    'breakout_on_h2': False, 'retest_state': 'NA', 'retest_ts': pd.NaT,
                    'retest_low': np.nan, 'entry_a_ts': pd.NaT, 'entry_a_open': np.nan,
                    'entry_b_ts': pd.NaT, 'entry_b_open': np.nan}
        if cl > H:
            breakout = ts
            break
    if pd.isna(breakout):
        return {'breakout_state': 'NO_BREAKOUT', 'breakout_ts': pd.NaT,
                'breakout_on_h2': False, 'retest_state': 'NA', 'retest_ts': pd.NaT,
                'retest_low': np.nan, 'entry_a_ts': pd.NaT, 'entry_a_open': np.nan,
                'entry_b_ts': pd.NaT, 'entry_b_open': np.nan}

    a_ts = breakout + m.BAR5
    if a_ts in q.index:
        a_open = float(q.loc[a_ts, 'open'])
    else:
        a_ts, a_open = pd.NaT, np.nan

    first = q[q.index > breakout]
    retest_ts = pd.NaT
    retest_low = np.nan
    retest_state = 'NO_RETEST'
    for ts, r in first.iterrows():
        if float(r.low) <= H:
            retest_ts = ts
            retest_low = float(r.low)
            retest_state = 'RETEST_HOLD' if float(r.close) >= H else 'RETEST_FAIL'
            break

    b_ts, b_open = pd.NaT, np.nan
    if retest_state == 'RETEST_HOLD':
        n = retest_ts + m.BAR5
        if n in q.index:
            op = float(q.loc[n, 'open'])
            if op >= H:
                b_ts, b_open = n, op
            else:
                retest_state = 'ENTRY_BELOW_H'

    return {'breakout_state': 'BREAKOUT', 'breakout_ts': breakout,
            'breakout_on_h2': bool(breakout == h2_ts), 'retest_state': retest_state,
            'retest_ts': retest_ts, 'retest_low': retest_low,
            'entry_a_ts': a_ts, 'entry_a_open': a_open,
            'entry_b_ts': b_ts, 'entry_b_open': b_open}


def target_outcome(q: pd.DataFrame, entry_ts: pd.Timestamp, H: float, R: float, ext: float):
    if pd.isna(entry_ts):
        return {'outcome': 'NO_ENTRY', 'event_ts': pd.NaT, 'minutes': np.nan}
    px = H + ext * R
    for ts, r in q[q.index >= entry_ts].iterrows():
        hit = float(r.high) >= px
        fail = float(r.close) < H
        if hit and fail:
            return {'outcome': 'AMBIGUOUS', 'event_ts': ts, 'minutes': float((ts-entry_ts)/pd.Timedelta(minutes=1))}
        if hit:
            return {'outcome': 'TARGET', 'event_ts': ts, 'minutes': float((ts-entry_ts)/pd.Timedelta(minutes=1))}
        if fail:
            return {'outcome': 'FAIL', 'event_ts': ts, 'minutes': float((ts-entry_ts)/pd.Timedelta(minutes=1))}
    return {'outcome': 'SESSION_END', 'event_ts': pd.NaT, 'minutes': np.nan}


def pre_failure_mfe(q: pd.DataFrame, entry_ts: pd.Timestamp, H: float, R: float):
    if pd.isna(entry_ts):
        return np.nan
    post = q[q.index >= entry_ts]
    fail_idx = post.index[post.close.astype(float) < H]
    if len(fail_idx):
        pre = post[post.index < fail_idx[0]]
    else:
        pre = post
    if len(pre) == 0:
        return 0.0
    return max(0.0, (float(pre.high.max()) - H) / R)


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 09:00', periods=6, freq='5min', tz='UTC')
    q = pd.DataFrame([
        [99.5,100.4,99.2,101.0],   # H2 and breakout close
        [101.0,101.2,99.8,100.4],  # first retest hold
        [100.4,102.0,100.2,101.8], # B entry bar
        [101.8,103.0,101.0,102.7],
        [102.7,103.2,99.5,99.8],
        [99.8,100.0,99.0,99.4],
    ], index=idx, columns=['open','high','low','close'])
    z = locate_setup(q,H,L,idx[0])
    assert z['breakout_ts'] == idx[0] and z['breakout_on_h2']
    assert z['retest_state'] == 'RETEST_HOLD' and z['retest_ts'] == idx[1]
    assert z['entry_a_ts'] == idx[1] and z['entry_b_ts'] == idx[2]

    # Wick-only H2 is not a breakout; later completed close > H is.
    q2 = q.copy(); q2.loc[idx[0], ['high','close']] = [100.5,99.7]; q2.loc[idx[1], ['low','close']] = [100.1,100.6]
    z2 = locate_setup(q2,H,L,idx[0])
    assert z2['breakout_ts'] == idx[1]

    # First retest that closes below H is a failed retest, no second chance.
    q3 = q.copy(); q3.loc[idx[1], ['low','close']] = [99.7,99.8]
    z3 = locate_setup(q3,H,L,idx[0])
    assert z3['retest_state'] == 'RETEST_FAIL' and pd.isna(z3['entry_b_ts'])

    # Same bar reaches E20 and closes below H => ambiguous, not target.
    q4 = q.copy(); q4.loc[idx[2], ['high','close']] = [102.2,99.8]
    o = target_outcome(q4,idx[2],H,10.0,.20)
    assert o['outcome'] == 'AMBIGUOUS'


def qmed(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    return float(s.median()) if len(s) else np.nan


def main():
    require_upstream()
    synthetic_tests()
    W = pd.read_csv(M2_WIN)
    for c in ['reference_start','execution_start','k1','leave_bar','eligible_start','terminal_bar']:
        W[c] = pd.to_datetime(W[c], utc=True, errors='coerce')
    W['clean_bool'] = as_bool(W['clean'])
    C = W[(W.clock.isin(CLOCKS)) & (W.side == 'LONG') & W.clean_bool & (W.terminal == 'H2')].copy()
    if len(C) == 0:
        raise RuntimeError('no clean LONG H2 cohort')

    x5, cov = m.load5()
    details, targets = [], []
    for r in C.itertuples(index=False):
        es = pd.Timestamp(r.execution_start); ee = es + m.EXE
        q = m.sl(x5, es, ee)
        if len(q) != 78:
            raise AssertionError('incomplete frozen execution window')
        H, L = float(r.H), float(r.L); R = H-L
        h2 = pd.Timestamp(r.terminal_bar)
        if not (R > 0 and h2 in q.index):
            raise AssertionError('invalid frozen H/L/H2 identity')
        z = locate_setup(q,H,L,h2)
        row = {'clock':r.clock,'partition':r.partition,'reference_start':r.reference_start,
               'execution_start':es,'H':H,'L':L,'R':R,'h2_ts':h2,**z}
        row['h2_to_breakout_min'] = float((z['breakout_ts']-h2)/pd.Timedelta(minutes=1)) if pd.notna(z['breakout_ts']) else np.nan
        row['breakout_to_retest_min'] = float((z['retest_ts']-z['breakout_ts'])/pd.Timedelta(minutes=1)) if pd.notna(z['retest_ts']) and pd.notna(z['breakout_ts']) else np.nan
        row['retest_penetration_ru'] = max(0.0,(H-float(z['retest_low']))/R) if pd.notna(z['retest_low']) else np.nan
        row['entry_b_fraction'] = (float(z['entry_b_open'])-L)/R if pd.notna(z['entry_b_open']) else np.nan
        row['a_mfe_ru'] = pre_failure_mfe(q,z['entry_a_ts'],H,R)
        row['b_mfe_ru'] = pre_failure_mfe(q,z['entry_b_ts'],H,R)
        details.append(row)
        for method, ets in [('A_IMMEDIATE',z['entry_a_ts']),('B_RETEST',z['entry_b_ts'])]:
            for name,ext in TARGETS.items():
                o = target_outcome(q,ets,H,R,ext)
                targets.append({'clock':r.clock,'partition':r.partition,'reference_start':r.reference_start,
                                'method':method,'target':name,'extension':ext,'entry_ts':ets,**o})

    D = pd.DataFrame(details); T = pd.DataFrame(targets)
    D.to_csv(OUT_DETAIL,index=False); T.to_csv(OUT_TARGETS,index=False)

    rows=[]
    for clock in CLOCKS:
        for part in (*m.PARTS.keys(),'POOLED_MAJOR'):
            g=D[D.clock==clock]
            t=T[T.clock==clock]
            if part=='POOLED_MAJOR':
                g=g[g.partition.isin(m.MAJOR)]; t=t[t.partition.isin(m.MAJOR)]
            else:
                g=g[g.partition==part]; t=t[t.partition==part]
            br=g[g.breakout_state=='BREAKOUT']; ret=br[br.retest_state.isin(['RETEST_HOLD','RETEST_FAIL','ENTRY_BELOW_H'])]
            hold=br[br.retest_state=='RETEST_HOLD']; fail=br[br.retest_state=='RETEST_FAIL']; nore=br[br.retest_state=='NO_RETEST']
            a=br[br.entry_a_ts.notna()]; b=br[br.entry_b_ts.notna()]
            base={'clock':clock,'partition':part,'clean_h2':len(g),'breakouts':len(br),
                  'breakout_rate':len(br)/len(g) if len(g) else np.nan,
                  'breakout_on_h2_rate':float(br.breakout_on_h2.mean()) if len(br) else np.nan,
                  'median_h2_to_breakout_min':qmed(br.h2_to_breakout_min),'entry_a':len(a),
                  'retest_attempts':len(ret),'retest_attempt_rate':len(ret)/len(br) if len(br) else np.nan,
                  'retest_holds':len(hold),'retest_hold_rate':len(hold)/len(ret) if len(ret) else np.nan,
                  'retest_fails':len(fail),'no_retest':len(nore),'entry_b':len(b),
                  'entry_b_rate_vs_breakout':len(b)/len(br) if len(br) else np.nan,
                  'median_breakout_to_retest_min':qmed(ret.breakout_to_retest_min),
                  'median_retest_penetration_ru':qmed(ret.retest_penetration_ru),
                  'median_entry_b_fraction':qmed(b.entry_b_fraction),
                  'median_a_mfe_ru':qmed(a.a_mfe_ru),'median_b_mfe_ru':qmed(b.b_mfe_ru)}
            for method,prefix,den in [('A_IMMEDIATE','a',len(a)),('B_RETEST','b',len(b))]:
                for target in TARGETS:
                    x=t[(t.method==method)&(t.target==target)]
                    if method=='A_IMMEDIATE': x=x[x.entry_ts.notna()]
                    else: x=x[x.entry_ts.notna()]
                    n=int((x.outcome=='TARGET').sum())
                    base[f'{prefix}_{target.lower()}_target']=n
                    base[f'{prefix}_{target.lower()}_rate']=n/den if den else np.nan
                    base[f'{prefix}_{target.lower()}_ambiguous']=int((x.outcome=='AMBIGUOUS').sum())
                    base[f'{prefix}_{target.lower()}_fail']=int((x.outcome=='FAIL').sum())
                    base[f'{prefix}_{target.lower()}_session_end']=int((x.outcome=='SESSION_END').sum())
                    base[f'{prefix}_{target.lower()}_median_min']=qmed(x.loc[x.outcome=='TARGET','minutes'])
            for target in TARGETS:
                ar=base[f'a_{target.lower()}_rate']; brate=base[f'b_{target.lower()}_rate']
                base[f'{target.lower()}_b_minus_a']=brate-ar if not pd.isna(ar) and not pd.isna(brate) else np.nan
            rows.append(base)
    S=pd.DataFrame(rows); S.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text('ETH_POST_BREAKOUT_RETEST_M1_COMPLETED\n')

    lines=['# ETH Post-Breakout Retest — M1 Structural Atlas — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'No PnL/TP/SL optimization. B = first H retest from above that holds, then next 5m open.','',
           '| Habitat | Clean H2 | Breakout | B retest entries | B avail. | A E20 | B E20 | Delta | A E30 | B E30 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    P=S[S.partition=='POOLED_MAJOR']
    for r in P.itertuples(index=False):
        fmt=lambda v: '-' if pd.isna(v) else f'{100*float(v):.1f}%'
        lines.append(f'| {r.clock} | {int(r.clean_h2)} | {int(r.breakouts)} ({fmt(r.breakout_rate)}) | {int(r.entry_b)} | {fmt(r.entry_b_rate_vs_breakout)} | {fmt(r.a_e20_rate)} | {fmt(r.b_e20_rate)} | {fmt(r.e20_b_minus_a)} | {fmt(r.a_e30_rate)} | {fmt(r.b_e30_rate)} |')
    lines += ['', '**Status: ETH_POST_BREAKOUT_RETEST_M1_COMPLETED**','',
              'Atlas only. No entry method is promoted and no next milestone was run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
