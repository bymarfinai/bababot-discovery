from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Same-directory import when executed as `python research/...py`, matching B27EN.
import bnb_session_native_london_ny_long_m1_structure_b27em as b27em

TARGET = 'BNBUSDT'
BAR5 = pd.Timedelta(minutes=5)
DEV_START = pd.Timestamp('2022-01-01', tz='UTC')
DEV_END = pd.Timestamp('2025-01-01', tz='UTC')

OUT_DETAIL = ROOT / 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M3_ENTRY_B27EO_Detail.csv'
OUT_SUM = ROOT / 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M3_ENTRY_B27EO_Summary.csv'
OUT_MD = ROOT / 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M3_ENTRY_B27EO_Result.md'
OUT_STATUS = ROOT / 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M3_ENTRY_B27EO_Status.txt'

CANDIDATES = ['E0_NEXT_OPEN','E1_FIRST_BULL_CLOSE','E2_F95_RECLAIM','E3_F90_RECLAIM','E4_F85_RECLAIM','E5_MICRO_HL_BULL']


def terminal_on_bar(row, H, L):
    h2 = float(row.high) >= H
    opp = float(row.close) < L
    if h2 and opp:
        return 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
    if h2:
        return 'H2_ARRIVAL'
    if opp:
        return 'OPPOSITE_BREAK_BEFORE_H2'
    return None


def candidate_signal(name, cur, prev, levels):
    o,h,l,c = map(float, [cur.open, cur.high, cur.low, cur.close])
    if name == 'E1_FIRST_BULL_CLOSE':
        return c > o
    if name == 'E2_F95_RECLAIM':
        z = levels['F95']; return l <= z and c > z
    if name == 'E3_F90_RECLAIM':
        z = levels['F90']; return l <= z and c > z
    if name == 'E4_F85_RECLAIM':
        z = levels['F85']; return l <= z and c > z
    if name == 'E5_MICRO_HL_BULL':
        if prev is None: return False
        return l > float(prev.low) and c > float(prev.close) and c > o
    raise ValueError(name)


def prefill_terminal(exe, leave_ts, fill_ts, H, L):
    # Completed bars known before fill. fill_ts is bar-open timestamp.
    q = exe[(exe.index >= leave_ts) & (exe.index < fill_ts)]
    for ts,row in q.iterrows():
        term = terminal_on_bar(row,H,L)
        if term:
            return term, ts
    return None, pd.NaT


def postfill_outcome(exe, fill_ts, H, L):
    q = exe[exe.index >= fill_ts]
    for ts,row in q.iterrows():
        term = terminal_on_bar(row,H,L)
        if term:
            return term, ts
    return 'NO_H2_BY_END', pd.NaT


def post_entry_mae(exe, fill_ts, terminal_start, H, R):
    if pd.isna(terminal_start):
        q = exe[exe.index >= fill_ts]
    else:
        q = exe[(exe.index >= fill_ts) & (exe.index < terminal_start)]
    if q.empty:
        return 0.0
    min_low = float(q.low.min())
    return max(0.0, (H-min_low)/R)


def discover_candidate(name, exe, leave_ts, H, L, R):
    levels = {'F95':L+.95*R,'F90':L+.90*R,'F85':L+.85*R}
    if name == 'E0_NEXT_OPEN':
        fill_ts = leave_ts
        if fill_ts not in exe.index:
            return {'candidate':name,'eligible':False,'reason':'MISSING_FILL_BAR'}
        px=float(exe.loc[fill_ts].open)
        if not (L < px < H):
            return {'candidate':name,'eligible':False,'reason':'NO_VALID_FILL'}
        outcome,term_ts = postfill_outcome(exe,fill_ts,H,L)
        return make_row(name, True, '', leave_ts, fill_ts, px, outcome, term_ts, exe,H,R)

    prev = None
    q = exe[exe.index >= leave_ts]
    for ts,row in q.iterrows():
        term = terminal_on_bar(row,H,L)
        if term:
            return {'candidate':name,'eligible':False,'reason':'TERMINAL_BEFORE_SIGNAL'}
        if candidate_signal(name,row,prev,levels):
            fill_ts = ts + BAR5
            if fill_ts not in exe.index:
                return {'candidate':name,'eligible':False,'reason':'NO_NEXT_BAR_FILL'}
            existing, _ = prefill_terminal(exe,leave_ts,fill_ts,H,L)
            if existing:
                return {'candidate':name,'eligible':False,'reason':'TERMINAL_BEFORE_FILL'}
            px=float(exe.loc[fill_ts].open)
            if not (L < px < H):
                return {'candidate':name,'eligible':False,'reason':'NO_VALID_FILL'}
            outcome,term_ts = postfill_outcome(exe,fill_ts,H,L)
            return make_row(name, True, '', leave_ts, fill_ts, px, outcome, term_ts, exe,H,R)
        prev=row
    return {'candidate':name,'eligible':False,'reason':'NO_SIGNAL_BY_END'}


def make_row(name,eligible,reason,leave_ts,fill_ts,px,outcome,term_ts,exe,H,R):
    mins_leave_entry=float((fill_ts-leave_ts)/pd.Timedelta(minutes=1))
    mins_entry_h2=np.nan
    if outcome=='H2_ARRIVAL' and not pd.isna(term_ts):
        mins_entry_h2=float(((term_ts+BAR5)-fill_ts)/pd.Timedelta(minutes=1))
    return {
        'candidate':name,'eligible':eligible,'reason':reason,
        'entry_ts':fill_ts,'entry_px':px,
        'entry_depth_R':float((H-px)/R),
        'minutes_leave_to_entry':mins_leave_entry,
        'outcome':outcome,'terminal_start':term_ts,
        'minutes_entry_to_h2':mins_entry_h2,
        'post_entry_mae_R':post_entry_mae(exe,fill_ts,term_ts,H,R),
    }


def build_rows(x5):
    base = b27em.session_rows(x5)
    dev = base[(base.partition=='development') & base.leave.fillna(False).astype(bool)].copy()
    if len(dev)!=97:
        raise AssertionError(f'expected 97 development leaves, got {len(dev)}')
    if int((dev.terminal=='H2_ARRIVAL').sum())!=76:
        raise AssertionError('expected 76 development H2')
    rows=[]
    for _,s in dev.iterrows():
        ny_open=pd.Timestamp(s.ny_open_utc); ny_close=pd.Timestamp(s.ny_close_utc)
        exe=b27em.fs(x5,ny_open,ny_close)
        H=float(s.H); L=float(s.L); R=float(s.R); leave_ts=pd.Timestamp(s.leave_ts)
        for cand in CANDIDATES:
            z=discover_candidate(cand,exe,leave_ts,H,L,R)
            z.update({'local_date':s.local_date,'upstream_terminal':s.terminal,'H':H,'L':L,'R':R,'leave_ts':leave_ts})
            rows.append(z)
    return pd.DataFrame(rows)


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def summarize(d):
    out=[]
    upstream_h2_dates=set(d.loc[d.upstream_terminal=='H2_ARRIVAL','local_date'].unique())
    for cand in CANDIDATES:
        q=d[d.candidate==cand]
        e=q[q.eligible.fillna(False).astype(bool)]
        h=e[e.outcome=='H2_ARRIVAL']
        non=e[e.outcome!='H2_ARRIVAL']
        captured=len(set(h.local_date) & upstream_h2_dates)
        out.append({
            'candidate':cand,'eligible':len(e),'eligible_rate':len(e)/97,
            'h2':len(h),'h2_rate':len(h)/len(e) if len(e) else np.nan,
            'non_h2':len(non),'winner_capture':captured/76,
            'median_leave_entry_min':pd.to_numeric(e.minutes_leave_to_entry,errors='coerce').median() if len(e) else np.nan,
            'median_entry_h2_min':pd.to_numeric(h.minutes_entry_to_h2,errors='coerce').median() if len(h) else np.nan,
            'median_entry_depth_R':pd.to_numeric(e.entry_depth_R,errors='coerce').median() if len(e) else np.nan,
            'median_mae_R':pd.to_numeric(e.post_entry_mae_R,errors='coerce').median() if len(e) else np.nan,
            'p75_mae_R':pd.to_numeric(e.post_entry_mae_R,errors='coerce').quantile(.75) if len(e) else np.nan,
        })
    s=pd.DataFrame(out)
    return s.sort_values(['h2_rate','winner_capture','median_leave_entry_min'],ascending=[False,False,True]).reset_index(drop=True)


def main():
    prereg=ROOT/'BNB_SESSION_NATIVE_LONDON_NY_LONG_M3_ENTRY_B27EO_Preregistration.md'
    if not prereg.exists(): raise AssertionError('B27EO preregistration missing')
    x5,coverage=b27em.data_base.load5(TARGET)
    if coverage<.995: raise AssertionError(f'coverage gate failed {coverage}')
    d=build_rows(x5)
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    lines=[
        '# BNB Session-Native London→New York LONG M3 K1→H2 Entry Discovery — B27EO Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**.','',
        'Discovery uses **development only (2022-01-01 → 2025-01-01)**. Validation partitions remain hidden from candidate selection.','',
        'Population integrity: **97 causal leaves**, including **76 upstream H2** and **21 upstream non-H2**.','',
        'B27EO compares only entries occurring causally after K1 leave and before H2/opposite terminal. No TP/SL/PnL/fees.','',
        '| Rank | Candidate | Eligible | H2 after entry | H2 rate | Winner capture | Med leave→entry | Med entry→H2 | Med entry depth | Med MAE | P75 MAE |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for i,r in s.iterrows():
        lines.append(f'| {i+1} | {r.candidate} | {int(r.eligible)}/97 ({pct(r.eligible_rate)}) | {int(r.h2)} | {pct(r.h2_rate)} | {pct(r.winner_capture)} | {r.median_leave_entry_min:.1f}m | {r.median_entry_h2_min:.1f}m | {r.median_entry_depth_R:.3f}R | {r.median_mae_R:.3f}R | {r.p75_mae_R:.3f}R |')
    best=s.iloc[0]
    lines += ['', '## Development-only descriptive leader','',
              f'By the preregistered ranking contract, **{best.candidate}** ranks first on development: H2-after-entry **{pct(best.h2_rate)}**, winner capture **{pct(best.winner_capture)}**, median leave→entry **{best.median_leave_entry_min:.1f}m**.','',
              'This is **not a promoted trading setup**. It is only the candidate that may deserve a separately frozen validation milestone.','',
              '**Status: B27EO_BNB_K1_H2_ENTRY_DISCOVERY_DEV_COMPLETE**','',
              'STOP: no validation reveal, TP/SL, economics, H3, breakout-retest, SHORT, or live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EO_BNB_K1_H2_ENTRY_DISCOVERY_DEV_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
