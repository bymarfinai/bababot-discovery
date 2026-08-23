#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_london_ny_4h_regime_alignment_b27ag as b27ag

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Result.md'
OUT_SUM = ROOT / 'BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Summary.csv'
OUT_TRANS = ROOT / 'BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Transitions.csv'
OUT_EP = ROOT / 'BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Episodes.csv'
OUT_STATUS = ROOT / 'BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Status.txt'
B27BE_RESULT = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Result.md'

STATES = ('BULL', 'BEAR', 'SIDEWAYS')
MAJOR = ('external', 'development', 'reference_validation')
H4 = pd.Timedelta(hours=4)


def assign_partition(ts: pd.Timestamp) -> str | None:
    for name, (a, b) in b22b.PARTS.items():
        if a <= ts < b:
            return name
    return None


def qtile(x: pd.Series, q: float) -> float:
    return float(pd.to_numeric(x, errors='coerce').dropna().quantile(q)) if len(x) else np.nan


def build_effective(x5: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    reg = b27ag.build_regime(x5).copy()
    assert set(reg['regime'].dropna().unique()) == set(STATES)
    assert (reg['n5'] == 48).all()
    reg['source_bar_start'] = reg.index
    reg['effective_ts'] = pd.to_datetime(reg['available_ts'], utc=True)
    assert (reg['effective_ts'] == reg.index + H4).all()
    assert reg['effective_ts'].is_monotonic_increasing

    # Episode segmentation is global and never reset at reporting partitions.
    gap = reg['effective_ts'].diff()
    new_ep = reg['regime'].ne(reg['regime'].shift(1)) | gap.ne(H4)
    reg['episode_id'] = new_ep.cumsum().astype(int)
    reg['state_age_intervals'] = reg.groupby('episode_id').cumcount() + 1
    reg['partition'] = reg['effective_ts'].map(assign_partition)
    reg['day_type'] = np.where(reg['effective_ts'].dt.weekday >= 5, 'WEEKEND', 'WEEKDAY')

    assert B27BE_RESULT.exists(), 'B27BE persisted result missing'
    b27be_hash = hashlib.sha256(B27BE_RESULT.read_bytes()).hexdigest()
    return reg.reset_index(drop=True), b27be_hash


def episode_table(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for eid, g in reg.groupby('episode_id', sort=True):
        g = g.sort_values('effective_ts')
        rows.append({
            'episode_id': int(eid),
            'regime': str(g.iloc[0].regime),
            'first_effective_ts': g.iloc[0].effective_ts,
            'last_effective_ts': g.iloc[-1].effective_ts,
            'first_partition': g.iloc[0].partition,
            'n_intervals': int(len(g)),
            'duration_hours': int(len(g) * 4),
        })
    e = pd.DataFrame(rows)
    assert not e.empty
    return e


def transition_table(reg: pd.DataFrame) -> pd.DataFrame:
    z = reg.sort_values('effective_ts').reset_index(drop=True)
    nxt = z.shift(-1)
    valid = (nxt['effective_ts'] - z['effective_ts']) == H4
    t = pd.DataFrame({
        'from_ts': z.loc[valid, 'effective_ts'].to_numpy(),
        'to_ts': nxt.loc[valid, 'effective_ts'].to_numpy(),
        'from_state': z.loc[valid, 'regime'].to_numpy(),
        'to_state': nxt.loc[valid, 'regime'].to_numpy(),
        'from_partition': z.loc[valid, 'partition'].to_numpy(),
        'to_partition': nxt.loc[valid, 'partition'].to_numpy(),
    })
    t['changed'] = t.from_state != t.to_state
    t['direct_bull_bear'] = (
        ((t.from_state == 'BULL') & (t.to_state == 'BEAR')) |
        ((t.from_state == 'BEAR') & (t.to_state == 'BULL'))
    )
    t['to_sideways_from_directional'] = t.from_state.isin(['BULL','BEAR']) & (t.to_state == 'SIDEWAYS')
    return t


def subset_rows(reg: pd.DataFrame, part: str) -> pd.DataFrame:
    if part == 'POOLED_MAJOR':
        return reg[reg.partition.isin(MAJOR)].copy()
    return reg[reg.partition == part].copy()


def subset_trans(t: pd.DataFrame, part: str) -> pd.DataFrame:
    # Both ends must belong to the requested reporting universe.
    if part == 'POOLED_MAJOR':
        return t[t.from_partition.isin(MAJOR) & t.to_partition.isin(MAJOR)].copy()
    return t[(t.from_partition == part) & (t.to_partition == part)].copy()


def subset_eps(e: pd.DataFrame, part: str) -> pd.DataFrame:
    if part == 'POOLED_MAJOR':
        return e[e.first_partition.isin(MAJOR)].copy()
    return e[e.first_partition == part].copy()


def flipback_stats(reg: pd.DataFrame, part: str) -> tuple[int, int, float]:
    z = subset_rows(reg, part).sort_values('effective_ts').reset_index(drop=True)
    if len(z) < 3:
        return 0, 0, np.nan
    a = z.regime.shift(1)
    b = z.regime
    c = z.regime.shift(-1)
    g1 = z.effective_ts - z.effective_ts.shift(1)
    g2 = z.effective_ts.shift(-1) - z.effective_ts
    consecutive = (g1 == H4) & (g2 == H4)
    centered = consecutive & a.notna() & c.notna() & (a != b)
    flips = centered & (c == a) & (b != a)
    den = int(centered.sum())
    num = int(flips.sum())
    return num, den, (num / den if den else np.nan)


def summarize(reg: pd.DataFrame, e: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    out = []
    for part in (*MAJOR, 'POOLED_MAJOR'):
        r = subset_rows(reg, part)
        tt = subset_trans(t, part)
        ee = subset_eps(e, part)
        flip_n, flip_den, flip_rate = flipback_stats(reg, part)

        if part == 'POOLED_MAJOR':
            pstart = b22b.PARTS['external'][0]
            pend = b22b.PARTS['reference_validation'][1]
        else:
            pstart, pend = b22b.PARTS[part]
        weeks = max(float((pend - pstart) / pd.Timedelta(days=7)), 1e-9)
        changes = int(tt.changed.sum())

        for state in STATES:
            rr = r[r.regime == state]
            tr = tt[tt.from_state == state]
            ep = ee[ee.regime == state]
            occupancy = float(len(rr) / len(r)) if len(r) else np.nan
            persistence = float((tr.to_state == state).mean()) if len(tr) else np.nan
            out.append({
                'partition': part,
                'regime': state,
                'intervals': int(len(rr)),
                'occupancy': occupancy,
                'episodes': int(len(ep)),
                'episode_median_intervals': float(ep.n_intervals.median()) if len(ep) else np.nan,
                'episode_p75_intervals': qtile(ep.n_intervals, .75),
                'episode_p90_intervals': qtile(ep.n_intervals, .90),
                'episode_max_intervals': int(ep.n_intervals.max()) if len(ep) else 0,
                'episode_median_hours': float(ep.duration_hours.median()) if len(ep) else np.nan,
                'persistence': persistence,
                'flip_back_n': flip_n,
                'flip_back_den': flip_den,
                'flip_back_rate': flip_rate,
                'state_changes': changes,
                'changes_per_week': float(changes / weeks),
                'direct_bull_bear_changes': int(tt.direct_bull_bear.sum()),
                'to_sideways_from_directional_changes': int(tt.to_sideways_from_directional.sum()),
            })
    return pd.DataFrame(out)


def transition_matrix(t: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for part in (*MAJOR, 'POOLED_MAJOR'):
        tt=subset_trans(t,part)
        for a in STATES:
            qa=tt[tt.from_state==a]
            den=len(qa)
            for b in STATES:
                n=int((qa.to_state==b).sum())
                rows.append({'partition':part,'from_state':a,'to_state':b,'n':n,'prob':(n/den if den else np.nan)})
    return pd.DataFrame(rows)


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main() -> None:
    x5, coverage = b21.load5()
    assert len(x5) == 698112
    assert abs(float(coverage) - 1.0) < 1e-12

    reg, b27be_hash = build_effective(x5)
    e = episode_table(reg)
    t = transition_table(reg)
    s = summarize(reg, e, t)
    tm = transition_matrix(t)

    # Mandatory chronology checks.
    assert set(reg.regime.unique()) == set(STATES)
    assert not reg.duplicated(['effective_ts']).any()
    assert (reg.state_age_intervals >= 1).all()
    assert (t.to_ts - t.from_ts == H4).all()

    # Frozen quality gate.
    gate_counts = True
    gate_persist = True
    for part in MAJOR:
        for state in STATES:
            z=s[(s.partition==part)&(s.regime==state)].iloc[0]
            gate_counts = gate_counts and int(z.intervals) >= 100
        for state in ('BULL','BEAR'):
            z=s[(s.partition==part)&(s.regime==state)].iloc[0]
            gate_persist = gate_persist and float(z.persistence) >= .60

    sp = s[s.partition.isin(MAJOR)].pivot(index='regime', columns='partition', values='occupancy')
    max_occ_diff = 0.0
    for state in STATES:
        vals=sp.loc[state].dropna().astype(float).to_numpy()
        if len(vals): max_occ_diff=max(max_occ_diff,float(vals.max()-vals.min()))

    pooled = s[s.partition=='POOLED_MAJOR'].set_index('regime')
    flip_rate = float(pooled.loc['BULL','flip_back_rate'])  # identical repeated metric across regime rows
    bull_med = float(pooled.loc['BULL','episode_median_intervals'])
    bear_med = float(pooled.loc['BEAR','episode_median_intervals'])
    stable = bool(gate_counts and gate_persist and flip_rate <= .20 and bull_med >= 2 and bear_med >= 2 and max_occ_diff <= .20)
    verdict = 'B27BG_REGIME_DETECTOR_STABLE' if stable else 'B27BG_REGIME_DETECTOR_NEEDS_REDESIGN'

    # Persist detailed audit tables.
    s.to_csv(OUT_SUM,index=False)
    tm.to_csv(OUT_TRANS,index=False)
    e.to_csv(OUT_EP,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    # Weekday/weekend occupancy pooled major, descriptive only.
    ww=[]
    pm=reg[reg.partition.isin(MAJOR)].copy()
    for dt in ('WEEKDAY','WEEKEND'):
        q=pm[pm.day_type==dt]
        for state in STATES:
            ww.append((dt,state,int((q.regime==state).sum()),float((q.regime==state).mean())))

    lines=[
        '# B27BG — BTC 24H Causal Regime Detector Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** This experiment audits regime identity/persistence only. No future return, liquidity direction, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, or PnL was used.','',
        f'Frozen B27BE result SHA256 observed during audit: `{b27be_hash}`.','',
        '## Major-partition detector summary','',
        '| Partition | State | Intervals | Occupancy | Episodes | Median episode | P75 | P90 | Max | Next-state persistence | Changes/week |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in (*MAJOR,'POOLED_MAJOR'):
        for state in STATES:
            z=s[(s.partition==part)&(s.regime==state)].iloc[0]
            lines.append(
                f'| {part} | {state} | {int(z.intervals)} | {fmt_pct(z.occupancy)} | {int(z.episodes)} | '
                f'{z.episode_median_intervals:.1f} bars / {z.episode_median_hours:.0f}h | {z.episode_p75_intervals:.1f} | '
                f'{z.episode_p90_intervals:.1f} | {int(z.episode_max_intervals)} | {fmt_pct(z.persistence)} | {z.changes_per_week:.2f} |'
            )

    lines += ['', '## Pooled-major transition matrix', '', '| From -> To | BULL | BEAR | SIDEWAYS |', '|---|---:|---:|---:|---:|']
    for a in STATES:
        vals=[]
        for b in STATES:
            z=tm[(tm.partition=='POOLED_MAJOR')&(tm.from_state==a)&(tm.to_state==b)].iloc[0]
            vals.append(fmt_pct(z.prob))
        lines.append(f'| {a} | {vals[0]} | {vals[1]} | {vals[2]} |')

    pt=subset_trans(t,'POOLED_MAJOR')
    changes=int(pt.changed.sum())
    direct=int(pt.direct_bull_bear.sum())
    via=int(pt.to_sideways_from_directional.sum())
    flip_n,flip_den,flip=flipback_stats(reg,'POOLED_MAJOR')
    lines += ['', '## Transition / noise diagnostics','',
        f'- Pooled state changes: **{changes:,}**.',
        f'- Direct BULL<->BEAR changes: **{direct:,}** ({fmt_pct(direct/changes if changes else np.nan)} of changes).',
        f'- Directional -> SIDEWAYS changes: **{via:,}** ({fmt_pct(via/changes if changes else np.nan)} of changes).',
        f'- One-interval flip-backs A->B->A: **{flip_n:,}/{flip_den:,} = {fmt_pct(flip)}** under the preregistered denominator.',
        f'- Maximum major-partition occupancy drift for any state: **{100*max_occ_diff:.1f} percentage points**.','',
        '## Weekday/weekend occupancy — descriptive only','',
        '| Day type | BULL | BEAR | SIDEWAYS |','|---|---:|---:|---:|']
    for dt in ('WEEKDAY','WEEKEND'):
        vals={state:rate for d,state,n,rate in ww if d==dt}
        lines.append(f'| {dt} | {fmt_pct(vals["BULL"])} | {fmt_pct(vals["BEAR"])} | {fmt_pct(vals["SIDEWAYS"])} |')

    lines += ['', '## Frozen detector-quality gate','',
        f'- Every state >=100 intervals in every major partition: **{"PASS" if gate_counts else "FAIL"}**.',
        f'- BULL and BEAR persistence >=60% in every major partition: **{"PASS" if gate_persist else "FAIL"}**.',
        f'- Pooled flip-back rate <=20%: **{"PASS" if flip <= .20 else "FAIL"}** ({fmt_pct(flip)}).',
        f'- Pooled median BULL episode >=2 bars: **{"PASS" if bull_med >= 2 else "FAIL"}** ({bull_med:.1f}).',
        f'- Pooled median BEAR episode >=2 bars: **{"PASS" if bear_med >= 2 else "FAIL"}** ({bear_med:.1f}).',
        f'- Major-partition occupancy drift <=20pp: **{"PASS" if max_occ_diff <= .20 else "FAIL"}** ({100*max_occ_diff:.1f}pp).','',
        f'**Frozen verdict: {verdict}.**','',
        'B27BG does not determine trade direction. If this detector is accepted, the next experiment must separately study directional behavior inside each frozen regime before any entry-location research.','',
        'Research only. Live BBC unchanged.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
