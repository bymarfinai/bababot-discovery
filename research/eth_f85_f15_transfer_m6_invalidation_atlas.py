#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PFX = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M6'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SEL = ROOT / f'{PFX}_Selection.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
EXPECTED = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'
MAJOR = ('external','development','reference_validation')
LOCKED = {('ALT_0330','F95'), ('RAW_0530','F90'), ('LONDON','F90'), ('RAW_2330','F95')}
DISTANCES = [i/100 for i in range(5,90,5)]

spec = importlib.util.spec_from_file_location('eth_m2_corr', HERE / 'eth_f85_f15_transfer_m2_causal_correction.py')
corr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(corr)
m = corr.m


def hard_event(q, stop_price, fill_ts, terminal):
    post = q[q.index >= fill_ts]
    if pd.notna(terminal):
        post = post[post.index <= terminal]
    hit = post[post.low <= stop_price]
    first = hit.index[0] if len(hit) else pd.NaT
    pre_first = pd.NaT
    if pd.notna(terminal):
        pre = post[post.index < terminal]
        z = pre[pre.low <= stop_price]
        pre_first = z.index[0] if len(z) else pd.NaT
    else:
        pre_first = first
    return first, pre_first


def close_event(q, stop_price, fill_ts, terminal, bar5):
    post = q[q.index >= fill_ts]
    if pd.notna(terminal):
        post = post[post.index < terminal]
    z = post[post.close < stop_price]
    if not len(z):
        return pd.NaT, pd.NaT, np.nan
    inv = z.index[0]
    nxt = inv + bar5
    if nxt not in q.index:
        return pd.NaT, pd.NaT, np.nan
    if pd.notna(terminal) and nxt > terminal:
        return pd.NaT, pd.NaT, np.nan
    return inv, nxt, float(q.loc[nxt, 'open'])


def synthetic_tests():
    idx = pd.date_range('2026-01-05 09:00', periods=5, freq='5min', tz='UTC')
    q = pd.DataFrame({
        'open':[99,96,95,96,94], 'high':[100,99,101,97,95],
        'low':[94,93,90,92,89], 'close':[96,94,99,93,90]
    }, index=idx)
    # same-fill hard stop is conservatively stopped
    a, ap = hard_event(q, 94.5, idx[0], idx[2])
    assert a == idx[0] and ap == idx[0]
    # H2-bar-only hard touch: pre-H2 survives, conservative-through-H2 does not
    q2 = q.copy(); q2.loc[idx[0],'low']=96; q2.loc[idx[1],'low']=96; q2.loc[idx[2],'low']=90
    b, bp = hard_event(q2, 94.5, idx[0], idx[2])
    assert b == idx[2] and pd.isna(bp)
    # completed close immediately before H2 exits at H2-bar open
    q3 = q.copy(); q3.loc[idx[0],'close']=96; q3.loc[idx[1],'close']=94
    inv, ex, _ = close_event(q3, 94.5, idx[0], idx[2], pd.Timedelta(minutes=5))
    assert inv == idx[1] and ex == idx[2]
    # close after terminal is forbidden
    q4 = q.copy(); q4.loc[idx[:3],'close']=[96,96,96]; q4.loc[idx[3],'close']=90
    inv2, ex2, _ = close_event(q4, 94.5, idx[0], idx[2], pd.Timedelta(minutes=5))
    assert pd.isna(inv2) and pd.isna(ex2)


def run_corrected_m2_capture_raw():
    cache = {}
    original = m.load5
    def cached_load5():
        if 'v' not in cache:
            cache['v'] = original()
        return cache['v']
    m.load5 = cached_load5
    corr.main()
    status = m.OUT_STATUS.read_text().strip()
    if status != EXPECTED:
        raise RuntimeError(f'M6 blocked by M2 status {status!r}')
    return cache['v']


def bool_series(s):
    return s.astype(str).str.lower().eq('true')


def summarize(g, mode):
    fills = len(g)
    win = g[g.outcome == 'H2']
    fail = g[g.outcome != 'H2']
    if mode == 'HARD_TOUCH':
        invalid = g.hard_stopped
        win_survive = ~win.hard_stopped
        pre_survive = ~win.hard_pre_h2_stopped
        fail_reject = fail.hard_stopped
        event_col = 'hard_first_ts'
    else:
        invalid = g.close_invalidated
        win_survive = ~win.close_invalidated
        pre_survive = win_survive
        fail_reject = fail.close_invalidated
        event_col = 'close_exit_ts'
    survive_n = int(win_survive.sum())
    not_invalid = g[~invalid]
    cond_h2 = int((not_invalid.outcome == 'H2').sum()) / len(not_invalid) if len(not_invalid) else np.nan
    mins = []
    for r in fail[fail_reject].itertuples(index=False):
        ev = getattr(r, event_col)
        if pd.notna(ev): mins.append(float((pd.Timestamp(ev)-pd.Timestamp(r.fill_ts))/pd.Timedelta(minutes=1)))
    return {
        'fills': fills,
        'baseline_h2_n': len(win),
        'baseline_h2_rate': len(win)/fills if fills else np.nan,
        'winner_survive_n': survive_n,
        'winner_survival_rate': survive_n/len(win) if len(win) else np.nan,
        'winner_kill_rate': 1-survive_n/len(win) if len(win) else np.nan,
        'pre_h2_winner_survival_rate': float(pre_survive.mean()) if len(win) else np.nan,
        'resulting_structural_h2_rate': survive_n/fills if fills else np.nan,
        'failures': len(fail),
        'failure_reject_n': int(fail_reject.sum()) if len(fail) else 0,
        'failure_reject_rate': float(fail_reject.mean()) if len(fail) else np.nan,
        'not_invalidated_n': len(not_invalid),
        'conditional_h2_rate_not_invalidated': cond_h2,
        'median_min_to_failure_invalidation': float(np.median(mins)) if mins else np.nan,
        'same_fill_hard_stop_rate': float(g.hard_same_fill.mean()) if mode == 'HARD_TOUCH' and len(g) else np.nan,
    }


def main():
    synthetic_tests()
    x5, coverage = run_corrected_m2_capture_raw()
    if coverage < .995:
        raise RuntimeError(f'raw 5m coverage too low: {coverage:.6f}')

    S0 = pd.read_csv(m.OUT_SUM)
    screen = S0[(S0.partition == 'POOLED_MAJOR') & (S0.screen == 'SCREEN_PASS')]
    screen_set = {(str(r.clock), str(r.level)) for r in screen.itertuples(index=False)}
    if not LOCKED.issubset(screen_set):
        raise AssertionError(f'locked set lost corrected-M2 SCREEN_PASS identity: {LOCKED-screen_set}')

    C = pd.read_csv(m.OUT_CAND)
    W = pd.read_csv(m.OUT_WIN)
    for c in ['reference_start','execution_start','fill_ts']:
        C[c] = pd.to_datetime(C[c], utc=True, errors='coerce')
    for c in ['reference_start','execution_start','terminal_bar']:
        if c in W: W[c] = pd.to_datetime(W[c], utc=True, errors='coerce')
    C = C[bool_series(C.filled)].copy()
    C = C[C.apply(lambda r: (str(r.clock), str(r.level)) in LOCKED, axis=1)].copy()
    if set((str(r.clock),str(r.level)) for r in C[['clock','level']].drop_duplicates().itertuples(index=False)) != LOCKED:
        raise AssertionError('M6 candidate universe mismatch')
    wm = W[['clock','partition','reference_start','terminal','terminal_bar']].copy()
    C = C.merge(wm, on=['clock','partition','reference_start'], how='left', validate='many_to_one', suffixes=('','_window'))
    if not (C.outcome.astype(str) == C.terminal.astype(str)).all():
        raise AssertionError('candidate/window terminal identity mismatch')

    rows = []
    for r in C.itertuples(index=False):
        es = pd.Timestamp(r.execution_start); ee = es + m.EXE
        q = m.sl(x5, es, ee).copy()
        if len(q) != 78: raise AssertionError(f'incomplete execution window {r.clock} {es}')
        fill = pd.Timestamp(r.fill_ts); terminal = pd.Timestamp(r.terminal_bar) if pd.notna(r.terminal_bar) else pd.NaT
        if str(r.outcome) == 'H2' and (pd.isna(terminal) or not fill < terminal):
            raise AssertionError('H2 terminal must be strictly after fill')
        H=float(r.H); L=float(r.L); R=H-L; f=float(r.fraction)
        if R <= 0: raise AssertionError('invalid frozen range')
        for D in DISTANCES:
            sf = f-D; sp = L + sf*R
            hard_ts, hard_pre_ts = hard_event(q, sp, fill, terminal)
            inv_ts, exit_ts, exit_open = close_event(q, sp, fill, terminal, m.BAR5)
            hard_stopped = pd.notna(hard_ts)
            hard_pre = pd.notna(hard_pre_ts)
            # Cross-check original M2 MAE identity against HARD_TOUCH geometry.
            if pd.notna(r.mae_ru):
                expected_touch = float(r.mae_ru) + 1e-10 >= D
                if hard_stopped != expected_touch:
                    raise AssertionError('hard-stop geometry does not reproduce M2 MAE')
            rows.append({
                'clock':r.clock,'level':r.level,'partition':r.partition,'reference_start':r.reference_start,
                'execution_start':es,'H':H,'L':L,'entry_fraction':f,'fill_ts':fill,'outcome':r.outcome,
                'terminal_bar':terminal,'distance':D,'stop_fraction':sf,'stop_price':sp,
                'hard_stopped':hard_stopped,'hard_first_ts':hard_ts,'hard_pre_h2_stopped':hard_pre,
                'hard_same_fill':bool(hard_stopped and hard_ts == fill),
                'close_invalidated':pd.notna(exit_ts),'close_signal_ts':inv_ts,'close_exit_ts':exit_ts,
                'close_exit_open':exit_open,
            })
    DTL = pd.DataFrame(rows)
    DTL.to_csv(OUT_DETAIL,index=False)

    sums=[]
    for clock,lvl in sorted(LOCKED):
        for mode in ('HARD_TOUCH','CLOSE_NEXT_OPEN'):
            for D in DISTANCES:
                base = DTL[(DTL.clock==clock)&(DTL.level==lvl)&(DTL.distance==D)]
                for part in (*MAJOR,'POOLED_MAJOR'):
                    g = base[base.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else base[base.partition==part]
                    z=summarize(g,mode)
                    sums.append({'clock':clock,'level':lvl,'mode':mode,'distance':D,
                                 'stop_fraction':float(g.stop_fraction.iloc[0]) if len(g) else np.nan,
                                 'partition':part,**z})
    SUM=pd.DataFrame(sums)

    selections=[]
    SUM['screen']=''
    for clock,lvl in sorted(LOCKED):
        for mode in ('HARD_TOUCH','CLOSE_NEXT_OPEN'):
            passes=[]
            for D in DISTANCES:
                rows_d=SUM[(SUM.clock==clock)&(SUM.level==lvl)&(SUM.mode==mode)&(SUM.distance==D)]
                pooled=rows_d[rows_d.partition=='POOLED_MAJOR'].iloc[0]
                majors=rows_d[rows_d.partition.isin(MAJOR)]
                ok=(bool((majors.fills>=30).all()) and
                    float(pooled.winner_survival_rate)>=.90 and
                    bool((majors.winner_survival_rate>=.85).all()) and
                    float(pooled.failure_reject_rate)>=.30 and
                    float(pooled.resulting_structural_h2_rate)>=.75)
                if ok:
                    SUM.loc[(SUM.clock==clock)&(SUM.level==lvl)&(SUM.mode==mode)&(SUM.distance==D)&(SUM.partition=='POOLED_MAJOR'),'screen']='STRUCTURAL_PASS'
                    passes.append(pooled)
            if passes:
                best=sorted(passes,key=lambda r:(-float(r.failure_reject_rate),-float(r.winner_survival_rate),float(r.distance)))[0]
                selections.append({'clock':clock,'level':lvl,'mode':mode,'selected_distance':float(best.distance),
                                   'stop_fraction':float(best.stop_fraction),'winner_survival_rate':float(best.winner_survival_rate),
                                   'failure_reject_rate':float(best.failure_reject_rate),
                                   'resulting_structural_h2_rate':float(best.resulting_structural_h2_rate),
                                   'status':'CANDIDATE'})
            else:
                selections.append({'clock':clock,'level':lvl,'mode':mode,'selected_distance':np.nan,
                                   'stop_fraction':np.nan,'winner_survival_rate':np.nan,'failure_reject_rate':np.nan,
                                   'resulting_structural_h2_rate':np.nan,'status':'NONE'})
    SUM.to_csv(OUT_SUM,index=False)
    SEL=pd.DataFrame(selections); SEL.to_csv(OUT_SEL,index=False)

    lines=['# ETH Transfer — M6 Stop / Invalidation Atlas — Result','',f'Raw 5m coverage: **{coverage:.4%}**.','',
           'Structural only: no target, PnL, PF, fees, leverage, or expectancy.','',
           '| Habitat | Entry | Mode | Candidate | Winner survival | Failure rejection | H2 after protection |','|---|---|---|---:|---:|---:|---:|']
    for r in SEL.itertuples(index=False):
        if r.status=='CANDIDATE':
            cand=f'D{int(round(100*r.selected_distance)):02d} / F{int(round(100*r.stop_fraction)):02d}'
            lines.append(f'| {r.clock} | {r.level} | {r.mode} | {cand} | {100*r.winner_survival_rate:.1f}% | {100*r.failure_reject_rate:.1f}% | {100*r.resulting_structural_h2_rate:.1f}% |')
        else:
            lines.append(f'| {r.clock} | {r.level} | {r.mode} | NONE | - | - | - |')
    status='ETH_M6_INVALIDATION_ATLAS_COMPLETED'
    lines += ['', 'HARD_TOUCH and CLOSE_NEXT_OPEN are not ranked against each other in M6.', '', f'**Status: {status}**', '', 'Stop after M6. No M7 was run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
