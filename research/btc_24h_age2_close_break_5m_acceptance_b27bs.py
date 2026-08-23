#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_swing_boundary_invalidation_b27bn as b27bn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_AGE2_CLOSE_BREAK_5M_ACCEPTANCE_B27BS_Result.md'
OUT_EP = ROOT / 'BTC_24H_AGE2_CLOSE_BREAK_5M_ACCEPTANCE_B27BS_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_AGE2_CLOSE_BREAK_5M_ACCEPTANCE_B27BS_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_AGE2_CLOSE_BREAK_5M_ACCEPTANCE_B27BS_Status.txt'

H4 = pd.Timedelta(hours=4)
BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pp(v):
    return '-' if pd.isna(v) else f'{100*float(v):+.1f}pp'


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def decisive_row(x5: pd.DataFrame, ep) -> dict:
    origin = str(ep.origin_state)
    age = int(ep.first_close_break_age)
    assert age in (1,2)
    first_ts = pd.Timestamp(ep.first_sideways_ts)
    start = first_ts + (age - 2) * H4
    end = start + H4
    q = fast_slice(x5, start, end)
    assert len(q) == 48, (ep.episode_id, len(q), start, end)
    assert q.index[0] == start and q.index[-1] == end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    boundary = float(ep.frozen_boundary)
    c = q.close.to_numpy(float)
    if origin == 'BULL':
        beyond = c < boundary
        reclaim_mask = c >= boundary
    else:
        assert origin == 'BEAR'
        beyond = c > boundary
        reclaim_mask = c <= boundary

    idx = np.flatnonzero(beyond)
    assert len(idx) >= 1
    first = int(idx[0])
    later_reclaim = bool(reclaim_mask[first+1:].any()) if first < 47 else False
    no_reclaim = not later_reclaim
    post = beyond[first:]
    acceptance_share = float(post.mean())
    streak = 0
    for v in beyond[::-1]:
        if bool(v): streak += 1
        else: break
    assert bool(beyond[-1]), '4H close-break requires final 5m close beyond boundary'

    return {
        'episode_id': int(ep.episode_id),
        'partition': str(ep.partition),
        'origin_state': origin,
        'outcome': str(ep.outcome),
        'transition': bool(ep.transition),
        'n_intervals': int(ep.n_intervals),
        'first_close_break_age': age,
        'first_sideways_ts': first_ts,
        'decisive_4h_start': start,
        'decisive_4h_end': end,
        'frozen_boundary': boundary,
        'first_break_pos': first + 1,
        'minutes_remaining_after_first_break': float((47-first)*5),
        'reclaim_after_break': later_reclaim,
        'no_reclaim': no_reclaim,
        'acceptance_share': acceptance_share,
        'final_acceptance_streak': int(streak),
    }


def subset(d, part, origin):
    q=d[d.origin_state == origin].copy()
    if part == 'POOLED_OOS': return q[q.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR': return q[q.partition.isin(MAJOR)].copy()
    return q[q.partition == part].copy()


def quant(g, col, p):
    return float(g[col].quantile(p)) if len(g) else np.nan


def summarize(d):
    rows=[]
    for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            nr=q[q.no_reclaim]; rc=q[~q.no_reclaim]
            for outcome in ('ALL','RESUME','TRANSITION'):
                g=q if outcome=='ALL' else q[q.outcome==outcome]
                rows.append({
                    'partition':part,'origin':origin,'outcome':outcome,'n':len(g),
                    'no_reclaim_n':len(nr) if outcome=='ALL' else np.nan,
                    'reclaim_n':len(rc) if outcome=='ALL' else np.nan,
                    'transition_rate_no_reclaim':float(nr.transition.mean()) if outcome=='ALL' and len(nr) else np.nan,
                    'transition_rate_reclaim':float(rc.transition.mean()) if outcome=='ALL' and len(rc) else np.nan,
                    'transition_lift':float(nr.transition.mean()-rc.transition.mean()) if outcome=='ALL' and len(nr) and len(rc) else np.nan,
                    'median_first_break_pos':quant(g,'first_break_pos',.5),
                    'p25_first_break_pos':quant(g,'first_break_pos',.25),
                    'p75_first_break_pos':quant(g,'first_break_pos',.75),
                    'median_acceptance_share':quant(g,'acceptance_share',.5),
                    'p25_acceptance_share':quant(g,'acceptance_share',.25),
                    'p75_acceptance_share':quant(g,'acceptance_share',.75),
                    'median_final_streak':quant(g,'final_acceptance_streak',.5),
                    'p25_final_streak':quant(g,'final_acceptance_streak',.25),
                    'p75_final_streak':quant(g,'final_acceptance_streak',.75),
                })
    return pd.DataFrame(rows)


def getrow(s,part,origin,outcome='ALL'):
    q=s[(s.partition==part)&(s.origin==origin)&(s.outcome==outcome)]
    assert len(q)==1
    return q.iloc[0]


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0) < 1e-12
    reg=b27bn.build_instrumented_regime(x5)
    parent=b27bn.build_episode_rows(reg,b27bn.load_parent_episodes())

    cohort=parent[
        parent.boundary_available &
        (parent.n_intervals >= 2) &
        parent.first_close_break_age.notna() &
        (parent.first_close_break_age <= 2)
    ].copy()

    expected={
        ('external','BULL'):40, ('development','BULL'):29, ('reference_validation','BULL'):26,
        ('external','BEAR'):19, ('development','BEAR'):23, ('reference_validation','BEAR'):14,
    }
    for (part,origin),n in expected.items():
        got=len(cohort[(cohort.partition==part)&(cohort.origin_state==origin)])
        assert got==n,(part,origin,got,n)
    assert len(cohort[cohort.origin_state=='BULL'])==95
    assert len(cohort[cohort.origin_state=='BEAR'])==56

    rows=[decisive_row(x5,ep) for ep in cohort.itertuples(index=False)]
    d=pd.DataFrame(rows)
    s=summarize(d)

    gate_identity=True
    gate_48=True
    gate_sample=True
    gate_pool=True
    gate_lift=True
    gate_parts=True
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        gate_sample = gate_sample and int(r.no_reclaim_n)>=10 and int(r.reclaim_n)>=10
        gate_pool = gate_pool and float(r.transition_rate_no_reclaim) > float(r.transition_rate_reclaim)
        gate_lift = gate_lift and float(r.transition_lift) >= .10
        for part in OOS:
            p=getrow(s,part,origin)
            enough=int(p.no_reclaim_n)>=3 and int(p.reclaim_n)>=3
            gate_parts = gate_parts and enough and float(p.transition_lift)>0

    supported=all([gate_identity,gate_48,gate_sample,gate_pool,gate_lift,gate_parts])
    verdict='B27BS_5M_CLOSE_BREAK_ACCEPTANCE_SUPPORTED' if supported else 'B27BS_5M_CLOSE_BREAK_ACCEPTANCE_NOT_SUPPORTED'

    d.to_csv(OUT_EP,index=False)
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BS — BTC 24H Age-2 Close-Break 5m Acceptance Anatomy — Result','',
        '**Audit status: PASS.** Structural microstructure only; no trading/economic rule or live change was used.','',
        'Frozen cohort identity reproduced exactly: **BULL 95 (OOS 66); BEAR 56 (OOS 33)** age-2 cumulative close-break episodes.','',
        '## Primary OOS readout','',
        '| Origin | Cohort N | NO_RECLAIM N | P(T | NO_RECLAIM) | RECLAIM N | P(T | RECLAIM) | Lift |',
        '|---|---:|---:|---:|---:|---:|---:|'
    ]
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        lines.append(f'| {origin} | {int(r.n)} | {int(r.no_reclaim_n)} | {pct(r.transition_rate_no_reclaim)} | {int(r.reclaim_n)} | {pct(r.transition_rate_reclaim)} | {pp(r.transition_lift)} |')
    lines += ['', '## OOS partition stability','',
              '| Partition | Origin | NO_RECLAIM N | P(T|NR) | RECLAIM N | P(T|R) | Lift |',
              '|---|---|---:|---:|---:|---:|---:|']
    for part in OOS:
        for origin in ORIGINS:
            r=getrow(s,part,origin)
            lines.append(f'| {part} | {origin} | {int(r.no_reclaim_n)} | {pct(r.transition_rate_no_reclaim)} | {int(r.reclaim_n)} | {pct(r.transition_rate_reclaim)} | {pp(r.transition_lift)} |')
    lines += ['', '## 5m anatomy by eventual outcome — pooled OOS','',
              '| Origin | Outcome | N | First break pos median [P25,P75] | Acceptance share median [P25,P75] | Final streak median [P25,P75] |',
              '|---|---|---:|---|---|---|']
    for origin in ORIGINS:
        for outcome in ('RESUME','TRANSITION'):
            r=getrow(s,'POOLED_OOS',origin,outcome)
            lines.append(
                f'| {origin} | {outcome} | {int(r.n)} | {r.median_first_break_pos:.1f} [{r.p25_first_break_pos:.1f},{r.p75_first_break_pos:.1f}] | '
                f'{pct(r.median_acceptance_share)} [{pct(r.p25_acceptance_share)},{pct(r.p75_acceptance_share)}] | '
                f'{r.median_final_streak:.1f} [{r.p25_final_streak:.1f},{r.p75_final_streak:.1f}] |'
            )
    lines += ['', '## Frozen support gate','',
              '- Exact raw/detector/parent/cohort identity: **PASS**.',
              '- Every decisive 4H bar = 48 continuous 5m bars with a 5m close-break: **PASS**.',
              f'- Pooled-OOS NO_RECLAIM and RECLAIM N >=10/origin: **{"PASS" if gate_sample else "FAIL"}**.',
              f'- Pooled-OOS P(T|NO_RECLAIM) > P(T|RECLAIM), both origins: **{"PASS" if gate_pool else "FAIL"}**.',
              f'- Pooled-OOS transition lift >=10pp, both origins: **{"PASS" if gate_lift else "FAIL"}**.',
              f'- Positive sign external + validation with >=3/cell, both origins: **{"PASS" if gate_parts else "FAIL"}**.',
              '- Causal intrabar-only features / no live change: **PASS**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'A supported result validates only intrabar acceptance/reclaim information after the age-2 close-break. It does not authorize a trade.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
