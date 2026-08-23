#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EP_FILE = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_SidewaysEpisodes.csv'
OUT_MD = ROOT / 'BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_Result.md'
OUT_CSV = ROOT / 'BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_Hazards.csv'
OUT_STATUS = ROOT / 'BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_Status.txt'

MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')
AGES = tuple(range(1,7))


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def load_eps():
    e = pd.read_csv(EP_FILE)
    b = e[e['partition'].isin(MAJOR) & e['bracketed_directional'].astype(bool)].copy()
    b['n_intervals'] = pd.to_numeric(b['n_intervals'], errors='raise').astype(int)
    b['same_direction_resume'] = b['same_direction_resume'].astype(bool)
    b['opposite_direction_transition'] = b['opposite_direction_transition'].astype(bool)
    assert len(b) == 1023, len(b)
    assert int(b.same_direction_resume.sum()) == 527
    assert int(b.opposite_direction_transition.sum()) == 496
    assert int((b.origin_state == 'BULL').sum()) == 532
    assert int((b.origin_state == 'BEAR').sum()) == 491
    assert (b.same_direction_resume ^ b.opposite_direction_transition).all()
    assert (b.n_intervals >= 1).all()
    return b


def subset(e, part, origin):
    q = e.copy()
    if part == 'POOLED_OOS':
        q = q[q.partition.isin(OOS)]
    elif part == 'POOLED_MAJOR':
        q = q[q.partition.isin(MAJOR)]
    else:
        q = q[q.partition == part]
    if origin != 'ALL':
        q = q[q.origin_state == origin]
    return q


def hazard_rows(e):
    rows=[]
    parts=(*MAJOR,'POOLED_OOS','POOLED_MAJOR')
    for part in parts:
        for origin in (*ORIGINS,'ALL'):
            q=subset(e,part,origin)
            for k in AGES:
                risk=q[q.n_intervals >= k]
                n=len(risk)
                resume=int(((risk.n_intervals == k) & risk.same_direction_resume).sum())
                trans=int(((risk.n_intervals == k) & risk.opposite_direction_transition).sum())
                survive=int((risk.n_intervals > k).sum())
                assert resume + trans + survive == n
                hr=resume/n if n else np.nan
                ht=trans/n if n else np.nan
                hs=survive/n if n else np.nan
                if n:
                    assert abs((hr+ht+hs)-1.0) < 1e-12
                rows.append({
                    'partition':part,'origin':origin,'age':k,'risk_n':n,
                    'resume_exit_n':resume,'transition_exit_n':trans,'survive_n':survive,
                    'h_resume':hr,'h_transition':ht,'h_survive':hs,
                    'transition_minus_resume':ht-hr if n else np.nan,
                })
    return pd.DataFrame(rows)


def row(h, part, origin, age):
    q=h[(h.partition==part)&(h.origin==origin)&(h.age==age)]
    assert len(q)==1
    return q.iloc[0]


def main():
    e=load_eps()
    h=hazard_rows(e)

    gate_identity=True
    gate_age1=True
    gate_age23=True
    gate_margin=True
    gate_n=True

    for origin in ORIGINS:
        r1=row(h,'POOLED_OOS',origin,1)
        gate_age1 = gate_age1 and float(r1.h_resume) > float(r1.h_transition)
        r2=row(h,'POOLED_OOS',origin,2)
        r3=row(h,'POOLED_OOS',origin,3)
        gate_age23 = gate_age23 and (
            float(r2.h_transition) > float(r2.h_resume) or
            float(r3.h_transition) > float(r3.h_resume)
        )
        for part in OOS:
            a1=row(h,part,origin,1)
            a2=row(h,part,origin,2)
            gate_margin = gate_margin and float(a2.transition_minus_resume) > float(a1.transition_minus_resume)
        for k in (1,2,3):
            gate_n = gate_n and int(row(h,'POOLED_OOS',origin,k).risk_n) >= 30

    supported=all([gate_identity,gate_age1,gate_age23,gate_margin,gate_n])
    verdict='B27BM_PHASED_SIDEWAYS_HAZARD_SUPPORTED' if supported else 'B27BM_PHASED_SIDEWAYS_HAZARD_NOT_SUPPORTED'

    h.to_csv(OUT_CSV,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BM — BTC 24H SIDEWAYS Age-Hazard Audit — Result','',
        '**Audit status: PASS.** Cause-specific temporal regime anatomy only; no classifier/refit, price threshold, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.','',
        'B27BH identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**','',
        'Hazards are conditional on the SIDEWAYS episode still being alive at the stated age. `h_resume + h_transition + h_survive = 1` by construction.','',
        '## Pooled OOS cause-specific hazards','',
        '| Origin | Age | Risk N | h RESUME | h TRANSITION | h SURVIVE | TRANSITION-RESUME |',
        '|---|---:|---:|---:|---:|---:|---:|'
    ]
    for origin in ORIGINS:
        for k in (1,2,3,4,5,6):
            r=row(h,'POOLED_OOS',origin,k)
            lines.append(f'| {origin} | {k} / {4*k}h | {int(r.risk_n)} | {pct(r.h_resume)} | {pct(r.h_transition)} | {pct(r.h_survive)} | {100*float(r.transition_minus_resume):+.1f}pp |')

    lines += ['', '## OOS partition stability — ages 1 and 2','',
              '| Partition | Origin | Age1 T-R | Age2 T-R | Upward shift? |',
              '|---|---|---:|---:|---|']
    for part in OOS:
        for origin in ORIGINS:
            a1=row(h,part,origin,1); a2=row(h,part,origin,2)
            up=float(a2.transition_minus_resume) > float(a1.transition_minus_resume)
            lines.append(f'| {part} | {origin} | {100*float(a1.transition_minus_resume):+.1f}pp | {100*float(a2.transition_minus_resume):+.1f}pp | {"YES" if up else "NO"} |')

    lines += ['', '## Pooled-major combined-origin descriptive hazard','',
              '| Age | Risk N | h RESUME | h TRANSITION | h SURVIVE | T-R |',
              '|---:|---:|---:|---:|---:|---:|']
    for k in AGES:
        r=row(h,'POOLED_MAJOR','ALL',k)
        lines.append(f'| {k} / {4*k}h | {int(r.risk_n)} | {pct(r.h_resume)} | {pct(r.h_transition)} | {pct(r.h_survive)} | {100*float(r.transition_minus_resume):+.1f}pp |')

    lines += ['', '## Frozen support gate','',
              f'- Exact parent identity / hazard accounting: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Both origins pooled-OOS age1 resume hazard > transition hazard: **{"PASS" if gate_age1 else "FAIL"}**.',
              f'- Both origins pooled-OOS have transition hazard > resume hazard at age2 or age3: **{"PASS" if gate_age23 else "FAIL"}**.',
              f'- Age1->age2 T-R margin shifts upward in external AND validation for both origins: **{"PASS" if gate_margin else "FAIL"}**.',
              f'- OOS risk N >=30 per origin at ages1-3: **{"PASS" if gate_n else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              '## Interpretation boundary','',
              'A supported result would validate only a reproducible age-dependent SIDEWAYS hazard shape. It would not yet define a production PENDING state or any trading behavior. Ages 4-6 are descriptive only and cannot rescue the primary gate.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
