#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_swing_boundary_invalidation_b27bn as b27bn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_BULL_SIDEWAYS_5M_PRE_SECOND_RETEST_B27BP_Result.md'
OUT_EP = ROOT / 'BTC_24H_BULL_SIDEWAYS_5M_PRE_SECOND_RETEST_B27BP_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_BULL_SIDEWAYS_5M_PRE_SECOND_RETEST_B27BP_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_BULL_SIDEWAYS_5M_PRE_SECOND_RETEST_B27BP_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
H4 = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
STATUSES = (
    'NO_R1','BREAK_ON_FIRST_ARRIVAL','BREAK_DURING_R1','R1_NO_CAUSAL_LEAVE',
    'CLEAN_WINDOW_NO_R2','R2_DEFENDED','R2_BREAK'
)


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pp(v):
    return '-' if pd.isna(v) else f'{100*float(v):+.1f}pp'


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def parent_bull():
    e = b27bn.load_parent_episodes()
    b = e[e.origin_state == 'BULL'].copy()
    assert len(b) == 532
    assert int(b.same_direction_resume.sum()) == 281
    assert int(b.opposite_direction_transition.sum()) == 251
    assert int(b[b.partition.isin(OOS)].shape[0]) == 313
    return b


def episode_row(x5, reg, ep):
    z = reg.sort_values('effective_ts').reset_index(drop=True)
    by_ts = {pd.Timestamp(t): i for i,t in enumerate(z.effective_ts)}
    first_ts = pd.Timestamp(ep.first_sideways_ts)
    i = by_ts[first_ts]
    prev = z.iloc[i-1]
    assert str(prev.regime) == 'BULL'
    assert pd.Timestamp(prev.effective_ts) == first_ts - H4
    boundary = float(prev.lsl) if pd.notna(prev.lsl) else np.nan
    start = pd.Timestamp(prev.effective_ts)
    end = pd.Timestamp(ep.last_sideways_ts)
    d = int(ep.n_intervals)
    q = fast_slice(x5, start, end)
    assert len(q) == d * 48, (ep.episode_id, len(q), d)
    assert q.index[0] == start
    if len(q) > 1:
        assert (q.index.to_series().diff().dropna() == BAR5).all()

    base = {
        'episode_id': int(ep.episode_id),
        'partition': str(ep.partition),
        'outcome': 'RESUME' if bool(ep.same_direction_resume) else 'TRANSITION',
        'resume': bool(ep.same_direction_resume),
        'transition': bool(ep.opposite_direction_transition),
        'first_sideways_ts': first_ts,
        'monitor_start': start,
        'monitor_end': end,
        'n_sideways_intervals': d,
        'frozen_swing_low': boundary,
        'boundary_available': bool(pd.notna(boundary)),
        'status': 'NO_R1',
        'r1_start': pd.NaT,
        'r1_end': pd.NaT,
        'r1_bars': 0,
        'leave_bar_start': pd.NaT,
        'leave_complete_ts': pd.NaT,
        'eligible_start': pd.NaT,
        'r2_bar_start': pd.NaT,
        'r2_complete_ts': pd.NaT,
        'r2_defended': False,
        'r2_break': False,
        'clean_window': False,
        'positive_pre_r2_window': False,
        'pre_r2_window_bars': np.nan,
        'pre_r2_window_minutes': np.nan,
        'r1_end_to_leave_complete_minutes': np.nan,
    }
    if pd.isna(boundary):
        return base

    r1_start_pos = None
    r1_end_pos = None

    # First arrival to frozen swing low.
    for k,(ts,r) in enumerate(q.iterrows()):
        if float(r.low) > boundary:
            continue
        if float(r.close) < boundary:
            base.update({'status':'BREAK_ON_FIRST_ARRIVAL','r2_break':False})
            return base
        r1_start_pos = k
        r1_end_pos = k
        base['r1_start'] = ts
        break

    if r1_start_pos is None:
        return base

    # Contiguous defended R1 episode, then require one completed non-touch leave bar.
    leave_pos = None
    for k in range(r1_start_pos + 1, len(q)):
        ts = q.index[k]; r = q.iloc[k]
        if float(r.close) < boundary:
            base.update({
                'status':'BREAK_DURING_R1',
                'r1_end':q.index[r1_end_pos],
                'r1_bars':int(r1_end_pos-r1_start_pos+1),
            })
            return base
        defended = float(r.low) <= boundary and float(r.close) >= boundary
        if defended:
            r1_end_pos = k
            continue
        # With no close-break and not a defended touch, low must be > boundary.
        assert float(r.low) > boundary
        leave_pos = k
        break

    base['r1_end'] = q.index[r1_end_pos]
    base['r1_bars'] = int(r1_end_pos-r1_start_pos+1)

    if leave_pos is None:
        base['status'] = 'R1_NO_CAUSAL_LEAVE'
        return base

    leave_start = q.index[leave_pos]
    leave_complete = leave_start + BAR5
    eligible_start = leave_complete
    base.update({
        'leave_bar_start': leave_start,
        'leave_complete_ts': leave_complete,
        'eligible_start': eligible_start,
        'clean_window': True,
        'r1_end_to_leave_complete_minutes': float((leave_complete - (q.index[r1_end_pos] + BAR5))/pd.Timedelta(minutes=1)),
    })
    assert eligible_start > q.index[r1_end_pos]

    # Retest #2 is first later 5m arrival after the completed causal leave.
    for k in range(leave_pos + 1, len(q)):
        ts = q.index[k]; r = q.iloc[k]
        assert ts >= eligible_start
        if float(r.low) > boundary:
            continue
        r2_complete = ts + BAR5
        nwin = int((ts - eligible_start) / BAR5)
        assert nwin >= 0
        defended = float(r.close) >= boundary
        status = 'R2_DEFENDED' if defended else 'R2_BREAK'
        base.update({
            'status':status,
            'r2_bar_start':ts,
            'r2_complete_ts':r2_complete,
            'r2_defended':bool(defended),
            'r2_break':bool(not defended),
            'positive_pre_r2_window':bool(ts > eligible_start),
            'pre_r2_window_bars':nwin,
            'pre_r2_window_minutes':float((ts-eligible_start)/pd.Timedelta(minutes=1)),
        })
        assert ts >= eligible_start
        return base

    base['status'] = 'CLEAN_WINDOW_NO_R2'
    # Full remaining clean window until SIDEWAYS monitoring ends.
    nwin = int((end - eligible_start) / BAR5)
    assert nwin >= 0
    base['pre_r2_window_bars'] = nwin
    base['pre_r2_window_minutes'] = float((end-eligible_start)/pd.Timedelta(minutes=1))
    return base


def subset(d, part):
    if part == 'POOLED_OOS': return d[d.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR': return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition == part].copy()


def summarize(d):
    rows=[]
    for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
        q=subset(d,part)
        known=q[q.boundary_available].copy()
        baseline=float(known.resume.mean()) if len(known) else np.nan
        clean=known[known.clean_window].copy()
        r2=clean[clean.status.isin(['R2_DEFENDED','R2_BREAK'])].copy()
        for status in ('ALL',*STATUSES):
            g=known if status=='ALL' else known[known.status==status]
            rows.append({
                'partition':part,'status':status,'n':len(g),
                'share':len(g)/len(known) if len(known) else np.nan,
                'resume_n':int(g.resume.sum()) if len(g) else 0,
                'transition_n':int(g.transition.sum()) if len(g) else 0,
                'resume_rate':float(g.resume.mean()) if len(g) else np.nan,
                'transition_rate':float(g.transition.mean()) if len(g) else np.nan,
                'baseline_resume_rate':baseline,
                'clean_window_n':len(clean) if status=='ALL' else np.nan,
                'clean_window_rate':len(clean)/len(known) if status=='ALL' and len(known) else np.nan,
                'r2_arrival_n':len(r2) if status=='ALL' else np.nan,
                'r2_given_clean':len(r2)/len(clean) if status=='ALL' and len(clean) else np.nan,
                'positive_pre_r2_window_n':int(r2.positive_pre_r2_window.sum()) if status=='ALL' else np.nan,
                'median_pre_r2_window_min':float(r2.pre_r2_window_minutes.median()) if status=='ALL' and len(r2) else np.nan,
                'p25_pre_r2_window_min':float(r2.pre_r2_window_minutes.quantile(.25)) if status=='ALL' and len(r2) else np.nan,
                'p75_pre_r2_window_min':float(r2.pre_r2_window_minutes.quantile(.75)) if status=='ALL' and len(r2) else np.nan,
                'median_pre_r2_window_bars':float(r2.pre_r2_window_bars.median()) if status=='ALL' and len(r2) else np.nan,
            })
    return pd.DataFrame(rows)


def getrow(s,part,status):
    q=s[(s.partition==part)&(s.status==status)]
    assert len(q)==1
    return q.iloc[0]


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0) < 1e-12
    reg=b27bn.build_instrumented_regime(x5)
    e=parent_bull()
    rows=[episode_row(x5,reg,ep) for ep in e.itertuples(index=False)]
    d=pd.DataFrame(rows)
    assert len(d)==532
    assert int(d.resume.sum())==281 and int(d.transition.sum())==251
    assert set(d.status.unique()).issubset(set(STATUSES))
    s=summarize(d)

    oos=subset(d,'POOLED_OOS')
    boundary_rate=float(oos.boundary_available.mean())
    known=oos[oos.boundary_available]
    clean=known[known.clean_window]
    defended=known[known.status=='R2_DEFENDED']
    broken=known[known.status=='R2_BREAK']

    gate_identity=True
    gate_boundary=boundary_rate>=.95
    gate_clean=len(clean)>=40
    gate_r2_sample=len(defended)>=20 and len(broken)>=20
    pooled_sign=(len(defended)>0 and len(broken)>0 and float(defended.resume.mean()) > float(broken.resume.mean()))
    gate_part_sign=True
    part_detail=[]
    for part in OOS:
        q=known[known.partition==part]
        a=q[q.status=='R2_DEFENDED']; b=q[q.status=='R2_BREAK']
        enough=len(a)>=5 and len(b)>=5
        pos=enough and float(a.resume.mean()) > float(b.resume.mean())
        gate_part_sign = gate_part_sign and pos
        part_detail.append((part,len(a),float(a.resume.mean()) if len(a) else np.nan,len(b),float(b.resume.mean()) if len(b) else np.nan,pos))

    # Chronology: every R2 must begin at/after eligible start; defended/break are exclusive.
    r2all=d[d.status.isin(['R2_DEFENDED','R2_BREAK'])]
    gate_chrono=bool((pd.to_datetime(r2all.r2_bar_start,utc=True) >= pd.to_datetime(r2all.eligible_start,utc=True)).all())
    gate_exclusive=bool((r2all.r2_defended ^ r2all.r2_break).all())

    supported=all([gate_identity,gate_boundary,gate_clean,gate_r2_sample,pooled_sign,gate_part_sign,gate_chrono,gate_exclusive])
    verdict='B27BP_BULL_5M_TWO_RETEST_GEOMETRY_SUPPORTED' if supported else 'B27BP_BULL_5M_TWO_RETEST_GEOMETRY_NOT_SUPPORTED'

    d.to_csv(OUT_EP,index=False)
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    all_oos=getrow(s,'POOLED_OOS','ALL')
    rd=getrow(s,'POOLED_OOS','R2_DEFENDED')
    rb=getrow(s,'POOLED_OOS','R2_BREAK')
    lines=[
        '# B27BP — BTC 24H BULL→SIDEWAYS 5m Pre-Second-Retest Anatomy — Result','',
        '**Audit status: PASS.** Regime microstructure only; no entry price, trade direction, stop, target, fee, WR, PF, PnL, or live change was used.','',
        'Parent identity reproduced exactly: **532 BULL-origin episodes = 281 RESUME + 251 TRANSITION; pooled OOS 313.**','',
        'The frozen swing low is known at the last completed BULL state. 5m monitoring starts immediately then, so Retest #1 / leave / Retest #2 chronology is causal.','',
        '## Pooled OOS','',
        f'- Frozen boundary available: **{int(known.shape[0])}/313 = {pct(boundary_rate)}**.',
        f'- Clean Retest#1 -> completed leave windows: **{len(clean)} / {len(known)} = {pct(len(clean)/len(known) if len(known) else np.nan)}**.',
        f'- Retest #2 arrivals after a clean leave: **{int(all_oos.r2_arrival_n)} / {int(all_oos.clean_window_n)} = {pct(all_oos.r2_given_clean)}**.',
        f'- Positive-duration pre-R2 windows: **{int(all_oos.positive_pre_r2_window_n)} / {int(all_oos.r2_arrival_n)}** R2-arrival cases.',
        f'- Median eligible-start -> R2 arrival: **{float(all_oos.median_pre_r2_window_min):.1f} min** ({float(all_oos.median_pre_r2_window_bars):.1f} completed 5m bars before R2); P25 **{float(all_oos.p25_pre_r2_window_min):.1f} min**, P75 **{float(all_oos.p75_pre_r2_window_min):.1f} min**.','',
        '### Exact 5m path status','',
        '| Status | N | Share | RESUME | TRANSITION | RESUME rate |',
        '|---|---:|---:|---:|---:|---:|'
    ]
    for st in STATUSES:
        r=getrow(s,'POOLED_OOS',st)
        lines.append(f'| {st} | {int(r.n)} | {pct(r.share)} | {int(r.resume_n)} | {int(r.transition_n)} | {pct(r.resume_rate)} |')

    lines += ['', '### Retest #2 outcome readout','',
              f'- BULL-origin baseline RESUME rate: **{pct(all_oos.baseline_resume_rate)}**.',
              f'- `R2_DEFENDED`: N **{int(rd.n)}**, RESUME **{pct(rd.resume_rate)}**, TRANSITION **{pct(rd.transition_rate)}**.',
              f'- `R2_BREAK`: N **{int(rb.n)}**, RESUME **{pct(rb.resume_rate)}**, TRANSITION **{pct(rb.transition_rate)}**.',
              f'- Defended-minus-break RESUME separation: **{pp(float(rd.resume_rate)-float(rb.resume_rate)) if pd.notna(rd.resume_rate) and pd.notna(rb.resume_rate) else "-"}**.','',
              '## OOS partition stability','',
              '| Partition | R2 defended N | RESUME | R2 break N | RESUME | Defended > break? |',
              '|---|---:|---:|---:|---:|---|']
    for part,na,ra,nb,rbv,pos in part_detail:
        lines.append(f'| {part} | {na} | {pct(ra)} | {nb} | {pct(rbv)} | {"YES" if pos else "NO"} |')

    lines += ['', '## Frozen support gate','',
              f'- Exact source/detector/parent identity: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Boundary available >=95% pooled OOS: **{"PASS" if gate_boundary else "FAIL"}**.',
              f'- Clean inter-retest window N >=40 pooled OOS: **{"PASS" if gate_clean else "FAIL"}**.',
              f'- R2_DEFENDED and R2_BREAK N >=20 pooled OOS: **{"PASS" if gate_r2_sample else "FAIL"}**.',
              f'- Pooled OOS RESUME(R2_DEFENDED) > RESUME(R2_BREAK): **{"PASS" if pooled_sign else "FAIL"}**.',
              f'- Same positive sign in external and validation with >=5/cell: **{"PASS" if gate_part_sign else "FAIL"}**.',
              f'- Retest #2 strictly after completed causal leave / event exclusivity: **{"PASS" if gate_chrono and gate_exclusive else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'Interpretation boundary: a supported result means only that the exact 5m two-retest geometry carries stable continuation-vs-breakdown information. It does not yet promote F15/F85 or any entry.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
