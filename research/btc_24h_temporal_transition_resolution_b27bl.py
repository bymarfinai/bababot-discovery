#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EP_FILE = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_SidewaysEpisodes.csv'
OUT_MD = ROOT / 'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Result.md'
OUT_TEMP = ROOT / 'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_TemporalSummary.csv'
OUT_COHORT = ROOT / 'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Cohort.csv'
OUT_STATUS = ROOT / 'BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Status.txt'

MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')
AGES = (1,2,3,4,5,6)  # SIDEWAYS bars completed; 4h each


def fmt_pct(v: float) -> str:
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def load_cohort() -> pd.DataFrame:
    e = pd.read_csv(EP_FILE)
    e['first_sideways_ts'] = pd.to_datetime(e['first_sideways_ts'], utc=True)
    e['last_sideways_ts'] = pd.to_datetime(e['last_sideways_ts'], utc=True)
    q = e[e['partition'].isin(MAJOR) & e['bracketed_directional'].astype(bool)].copy()
    q['n_intervals'] = pd.to_numeric(q['n_intervals'], errors='raise').astype(int)
    q['transition'] = q['opposite_direction_transition'].astype(bool)
    q['resume'] = q['same_direction_resume'].astype(bool)
    assert len(q) == 1023, len(q)
    assert int(q.resume.sum()) == 527
    assert int(q.transition.sum()) == 496
    assert int((q.origin_state == 'BULL').sum()) == 532
    assert int((q.origin_state == 'BEAR').sum()) == 491
    assert (q.resume ^ q.transition).all()
    assert (q.n_intervals >= 1).all()
    assert not q.duplicated(['episode_id']).any()
    # Duration identity from B27BH: first and last SIDEWAYS timestamps are 4h spaced.
    span = ((q.last_sideways_ts - q.first_sideways_ts) / pd.Timedelta(hours=4)).astype(int) + 1
    assert (span == q.n_intervals).all()
    return q.sort_values('first_sideways_ts').reset_index(drop=True)


def subset(q: pd.DataFrame, partition: str, origin: str | None = None) -> pd.DataFrame:
    if partition == 'POOLED_MAJOR':
        z = q[q.partition.isin(MAJOR)].copy()
    elif partition == 'POOLED_OOS':
        z = q[q.partition.isin(OOS)].copy()
    else:
        z = q[q.partition == partition].copy()
    if origin is not None:
        z = z[z.origin_state == origin].copy()
    return z


def temporal_rows(q: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    parts = (*MAJOR,'POOLED_MAJOR','POOLED_OOS')
    for part in parts:
        for origin in (*ORIGINS,'ALL'):
            z = subset(q, part, None if origin=='ALL' else origin)
            n = len(z)
            base_tr = float(z.transition.mean()) if n else np.nan
            for age in AGES:
                pending = z[z.n_intervals > age].copy()
                resolved = z[z.n_intervals <= age].copy()
                # Resolution becomes known at +4h*age after t0 when the next raw directional
                # state appears for episodes whose SIDEWAYS duration <= age.
                trans_at_age = z[(z.n_intervals == age) & z.transition]
                resume_at_age = z[(z.n_intervals == age) & z.resume]
                rows.append({
                    'partition':part,
                    'origin':origin,
                    'age_sideways_bars':age,
                    'hours_after_first_sideways':4*age,
                    'n_total':n,
                    'baseline_transition_rate':base_tr,
                    'resolved_n':len(resolved),
                    'resolved_rate':len(resolved)/n if n else np.nan,
                    'pending_n':len(pending),
                    'pending_rate':len(pending)/n if n else np.nan,
                    'pending_eventual_transition_n':int(pending.transition.sum()) if len(pending) else 0,
                    'pending_eventual_transition_rate':float(pending.transition.mean()) if len(pending) else np.nan,
                    'pending_transition_lift_pp':100*(float(pending.transition.mean())-base_tr) if len(pending) else np.nan,
                    'resume_resolved_exact_age_n':len(resume_at_age),
                    'transition_resolved_exact_age_n':len(trans_at_age),
                })
    return pd.DataFrame(rows)


def getrow(t: pd.DataFrame, part: str, origin: str, age: int) -> pd.Series:
    x=t[(t.partition==part)&(t.origin==origin)&(t.age_sideways_bars==age)]
    assert len(x)==1
    return x.iloc[0]


def main() -> None:
    q=load_cohort()
    t=temporal_rows(q)

    # Frozen gate 1: identity/causality.
    gate_identity=True

    # Gate 2: pooled OOS >=40% resolved by +8h (age 2).
    oos_all_age2=getrow(t,'POOLED_OOS','ALL',2)
    gate_resolve8=float(oos_all_age2.resolved_rate) >= .40

    # Gate 3: for each origin pooled OOS, still pending after one SIDEWAYS bar
    # has >=10pp higher eventual transition probability than baseline.
    gate_lift=True
    gate_n=True
    for origin in ORIGINS:
        r=getrow(t,'POOLED_OOS',origin,1)
        gate_lift = gate_lift and float(r.pending_transition_lift_pp) >= 10.0
        gate_n = gate_n and int(r.pending_n) >= 30

    # Gate 4: same positive survival effect in both OOS partitions for both origins.
    gate_oos_sign=True
    for part in OOS:
        for origin in ORIGINS:
            r=getrow(t,part,origin,1)
            gate_oos_sign = gate_oos_sign and int(r.pending_n) > 0 and float(r.pending_transition_lift_pp) > 0

    # Gate 6: >=70% pooled OOS resolved by +12h (age 3).
    oos_all_age3=getrow(t,'POOLED_OOS','ALL',3)
    gate_resolve12=float(oos_all_age3.resolved_rate) >= .70

    supported=all([gate_identity,gate_resolve8,gate_lift,gate_oos_sign,gate_n,gate_resolve12])
    verdict='B27BL_TEMPORAL_PENDING_STATE_SUPPORTED' if supported else 'B27BL_TEMPORAL_PENDING_STATE_NOT_SUPPORTED'

    q.to_csv(OUT_COHORT,index=False)
    t.to_csv(OUT_TEMP,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BL — BTC 24H Temporal Transition Resolution Audit — Result','',
        '**Audit status: PASS.** Temporal regime-state anatomy only; no classifier/refit, price threshold, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.','',
        'B27BH identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**','',
        'At the first completed SIDEWAYS bar the conceptual state is `PENDING`. An episode resolves only when a later completed 4H bar causally returns to the origin directional state or reaches the opposite directional state.','',
        '## Pooled-OOS temporal resolution','',
        '| Age since first SIDEWAYS | Resolved | Still PENDING | P(transition \| pending) |',
        '|---|---:|---:|---:|'
    ]
    for age in AGES:
        r=getrow(t,'POOLED_OOS','ALL',age)
        lines.append(f'| +{4*age}h | {int(r.resolved_n)}/{int(r.n_total)} = {fmt_pct(r.resolved_rate)} | {int(r.pending_n)} = {fmt_pct(r.pending_rate)} | {fmt_pct(r.pending_eventual_transition_rate)} |')

    lines += ['', '## One-bar survival effect — OOS','',
              'This asks: after the first SIDEWAYS bar, if the next 4H state is **still SIDEWAYS**, how much does eventual opposite-direction transition probability rise relative to first-SIDEWAYS baseline?','',
              '| Partition | Origin | Baseline transition | Still pending N | Transition if still pending | Lift |',
              '|---|---|---:|---:|---:|---:|']
    for part in (*OOS,'POOLED_OOS'):
        for origin in ORIGINS:
            r=getrow(t,part,origin,1)
            lines.append(f'| {part} | {origin} | {fmt_pct(r.baseline_transition_rate)} | {int(r.pending_n)} | {fmt_pct(r.pending_eventual_transition_rate)} | {float(r.pending_transition_lift_pp):+.1f}pp |')

    lines += ['', '## Cause-specific resolution by SIDEWAYS duration — pooled major','',
              '| SIDEWAYS duration | RESUME resolves | TRANSITION resolves | Total resolving at age |',
              '|---|---:|---:|---:|']
    for age in AGES:
        r=getrow(t,'POOLED_MAJOR','ALL',age)
        a=int(r.resume_resolved_exact_age_n); b=int(r.transition_resolved_exact_age_n)
        lines.append(f'| {age} bar / {4*age}h | {a} | {b} | {a+b} |')

    lines += ['', '## Frozen promotion gate','',
              f'- Exact identity / causal timing: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Pooled-OOS resolved by +8h >=40%: **{"PASS" if gate_resolve8 else "FAIL"}** ({fmt_pct(oos_all_age2.resolved_rate)}).',
              f'- Both origins pooled-OOS one-bar pending transition lift >=10pp: **{"PASS" if gate_lift else "FAIL"}**.',
              f'- Positive one-bar survival effect in external AND validation for both origins: **{"PASS" if gate_oos_sign else "FAIL"}**.',
              f'- Pooled-OOS pending N after one bar >=30 per origin: **{"PASS" if gate_n else "FAIL"}**.',
              f'- Pooled-OOS resolved by +12h >=70%: **{"PASS" if gate_resolve12 else "FAIL"}** ({fmt_pct(oos_all_age3.resolved_rate)}).','',
              f'**Frozen verdict: `{verdict}`.**','',
              '## Interpretation boundary','',
              'A supported result validates only the temporal `PENDING`-state concept: SIDEWAYS age itself contains causal information and many episodes resolve naturally without forcing a first-bar classification. It does not yet define the production detector state machine or any trading behavior.','',
              'Research only. Live BBC unchanged.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
