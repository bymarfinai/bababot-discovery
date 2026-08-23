#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_24h_regime_detector_audit_b27bg as b27bg

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_Result.md'
OUT_PAT = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_FlipbackPatterns.csv'
OUT_EP = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_SidewaysEpisodes.csv'
OUT_SUM = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_Status.txt'

H4 = pd.Timedelta(hours=4)
STATES = ('BULL', 'BEAR', 'SIDEWAYS')
MAJOR = ('external', 'development', 'reference_validation')
PATTERNS = (
    'BULL->SIDEWAYS->BULL',
    'BEAR->SIDEWAYS->BEAR',
    'BULL->BEAR->BULL',
    'BEAR->BULL->BEAR',
    'SIDEWAYS->BULL->SIDEWAYS',
    'SIDEWAYS->BEAR->SIDEWAYS',
)


def fmt_pct(v: float) -> str:
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def qtile(s: pd.Series, q: float) -> float:
    x = pd.to_numeric(s, errors='coerce').dropna()
    return float(x.quantile(q)) if len(x) else np.nan


def pattern_rows(reg: pd.DataFrame, part: str) -> tuple[pd.DataFrame, int]:
    z = b27bg.subset_rows(reg, part).sort_values('effective_ts').reset_index(drop=True)
    a = z.regime.shift(1)
    b = z.regime
    c = z.regime.shift(-1)
    g1 = z.effective_ts - z.effective_ts.shift(1)
    g2 = z.effective_ts.shift(-1) - z.effective_ts
    centered = (g1 == H4) & (g2 == H4) & a.notna() & c.notna() & (a != b)
    flip = centered & (c == a) & (b != a)
    rows = z.loc[flip, ['effective_ts','partition']].copy()
    rows['a'] = a.loc[flip].to_numpy()
    rows['b'] = b.loc[flip].to_numpy()
    rows['c'] = c.loc[flip].to_numpy()
    rows['pattern'] = rows.a + '->' + rows.b + '->' + rows.c
    assert set(rows.pattern.unique()).issubset(set(PATTERNS))
    return rows, int(centered.sum())


def episode_anatomy(reg: pd.DataFrame) -> pd.DataFrame:
    z = reg.sort_values('effective_ts').reset_index(drop=True).copy()
    eps = []
    for eid, g in z.groupby('episode_id', sort=True):
        if str(g.iloc[0].regime) != 'SIDEWAYS':
            continue
        i0, i1 = int(g.index.min()), int(g.index.max())
        prev = z.iloc[i0-1] if i0 > 0 else None
        nxt = z.iloc[i1+1] if i1+1 < len(z) else None
        gap_prev = prev is None or (g.iloc[0].effective_ts - prev.effective_ts != H4)
        gap_next = nxt is None or (nxt.effective_ts - g.iloc[-1].effective_ts != H4)
        prev_state = None if prev is None else str(prev.regime)
        next_state = None if nxt is None else str(nxt.regime)
        bracketed = (
            not gap_prev and not gap_next and
            prev_state in ('BULL','BEAR') and next_state in ('BULL','BEAR')
        )
        cls = None
        if bracketed:
            cls = f'{prev_state}->SIDEWAYS->{next_state}'
        n = int(len(g))
        eps.append({
            'episode_id': int(eid),
            'first_sideways_ts': g.iloc[0].effective_ts,
            'last_sideways_ts': g.iloc[-1].effective_ts,
            'partition': g.iloc[0].partition,
            'n_intervals': n,
            'duration_hours': 4*n,
            'origin_state': prev_state,
            'exit_state': next_state,
            'bracketed_directional': bool(bracketed),
            'class': cls,
            'same_direction_resume': bool(bracketed and prev_state == next_state),
            'opposite_direction_transition': bool(bracketed and prev_state != next_state),
            'gap_or_boundary': bool(gap_prev or gap_next),
        })
    out = pd.DataFrame(eps)
    assert not out.empty
    return out


def partition_pattern_summary(reg: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for part in (*MAJOR, 'POOLED_MAJOR'):
        p, den = pattern_rows(reg, part)
        total = len(p)
        for pat in PATTERNS:
            n=int((p.pattern==pat).sum())
            rows.append({
                'partition':part,
                'pattern':pat,
                'n':n,
                'share_of_flipbacks':n/total if total else np.nan,
                'flipbacks_total':total,
                'eligible_centers':den,
                'flipback_rate':total/den if den else np.nan,
            })
    return pd.DataFrame(rows)


def episode_summary(ep: pd.DataFrame) -> pd.DataFrame:
    classes = (
        'BULL->SIDEWAYS->BULL','BEAR->SIDEWAYS->BEAR',
        'BULL->SIDEWAYS->BEAR','BEAR->SIDEWAYS->BULL'
    )
    rows=[]
    for part in (*MAJOR,'POOLED_MAJOR'):
        q=ep[ep.partition.isin(MAJOR)].copy() if part=='POOLED_MAJOR' else ep[ep.partition==part].copy()
        b=q[q.bracketed_directional].copy()
        total=len(b)
        for cls in classes:
            x=b[b['class']==cls]
            rows.append({
                'partition':part,'class':cls,'n':len(x),
                'share':len(x)/total if total else np.nan,
                'median_intervals':float(x.n_intervals.median()) if len(x) else np.nan,
                'p75_intervals':qtile(x.n_intervals,.75),
                'p90_intervals':qtile(x.n_intervals,.90),
                'one_bar_n':int((x.n_intervals==1).sum()),
                'two_bar_n':int((x.n_intervals==2).sum()),
                'three_plus_n':int((x.n_intervals>=3).sum()),
                'bracketed_total':total,
            })
    return pd.DataFrame(rows)


def main() -> None:
    x5, coverage = b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12

    reg, _ = b27bg.build_effective(x5)
    reg = reg.sort_values('effective_ts').reset_index(drop=True)

    # Reproduce the exact B27BG pooled-major flip-back denominator/numerator first.
    pooled_pat, pooled_den = pattern_rows(reg,'POOLED_MAJOR')
    assert pooled_den == 2202, (pooled_den, 'expected B27BG denominator 2202')
    assert len(pooled_pat) == 459, (len(pooled_pat), 'expected B27BG flipbacks 459')
    assert pooled_pat.pattern.value_counts().sum() == 459

    ps = partition_pattern_summary(reg)
    ep = episode_anatomy(reg)
    es = episode_summary(ep)

    # Mandatory exhaustiveness.
    assert int(ps[(ps.partition=='POOLED_MAJOR')].n.sum()) == 459
    bracketed = ep[ep.partition.isin(MAJOR) & ep.bracketed_directional].copy()
    assert bracketed['class'].notna().all()
    assert bracketed['class'].isin(es['class'].unique()).all()

    ppool=ps[ps.partition=='POOLED_MAJOR'].set_index('pattern')
    side_mid = int(ppool.loc['BULL->SIDEWAYS->BULL','n'] + ppool.loc['BEAR->SIDEWAYS->BEAR','n'])
    side_mid_share = side_mid/459
    primary = 'SIDEWAYS_MIDDLE_DOMINATES_ONE_BAR_FLIPBACKS' if side_mid_share > .50 else 'SIDEWAYS_MIDDLE_DOES_NOT_DOMINATE_ONE_BAR_FLIPBACKS'

    same_n=int(bracketed.same_direction_resume.sum())
    opp_n=int(bracketed.opposite_direction_transition.sum())
    btotal=len(bracketed)

    # Origin-specific resume/transition.
    origin_stats=[]
    for origin in ('BULL','BEAR'):
        q=bracketed[bracketed.origin_state==origin]
        origin_stats.append({
            'origin':origin,'n':len(q),
            'resume_n':int(q.same_direction_resume.sum()),
            'resume_rate':float(q.same_direction_resume.mean()) if len(q) else np.nan,
            'opposite_n':int(q.opposite_direction_transition.sum()),
            'opposite_rate':float(q.opposite_direction_transition.mean()) if len(q) else np.nan,
        })
    os=pd.DataFrame(origin_stats)

    pooled_pat.to_csv(OUT_PAT,index=False)
    ep.to_csv(OUT_EP,index=False)
    pd.concat([
        ps.assign(table='flipback_patterns'),
        es.assign(table='sideways_episode_classes')
    ], ignore_index=True, sort=False).to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(primary+'\n')

    lines=[
        '# B27BH — BTC 24H SIDEWAYS Transition Anatomy Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Regime-state anatomy only; no future return, trade direction, entry, stop, target, fee, WR, PF, or PnL was used.','',
        'B27BG exact pooled flip-back reproduction: **459 / 2,202 = 20.8%**.','',
        '## One-interval flip-back anatomy — pooled major','',
        '| Pattern | N | Share of all 459 flip-backs |','|---|---:|---:|'
    ]
    for pat in PATTERNS:
        z=ppool.loc[pat]
        lines.append(f'| {pat} | {int(z.n)} | {fmt_pct(z.share_of_flipbacks)} |')
    lines += ['',f'**SIDEWAYS as the middle state accounts for {side_mid}/{459} = {fmt_pct(side_mid_share)} of all one-bar flip-backs.**','',f'**Frozen primary readout: `{primary}`.**','',
              '## One-interval flip-backs by major partition','',
              '| Partition | BULL-SIDEWAYS-BULL | BEAR-SIDEWAYS-BEAR | BULL-BEAR-BULL | BEAR-BULL-BEAR | SIDEWAYS-BULL-SIDEWAYS | SIDEWAYS-BEAR-SIDEWAYS | Total |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for part in MAJOR:
        q=ps[ps.partition==part].set_index('pattern')
        vals=[int(q.loc[p,'n']) for p in PATTERNS]
        lines.append(f'| {part} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} | {vals[4]} | {vals[5]} | {sum(vals)} |')

    epool=es[es.partition=='POOLED_MAJOR'].set_index('class')
    lines += ['', '## Bracketed SIDEWAYS episode bridge anatomy — pooled major','',
              '| SIDEWAYS episode class | N | Share | Median | P75 | P90 | 1 bar | 2 bars | 3+ bars |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cls in ('BULL->SIDEWAYS->BULL','BEAR->SIDEWAYS->BEAR','BULL->SIDEWAYS->BEAR','BEAR->SIDEWAYS->BULL'):
        z=epool.loc[cls]
        lines.append(f'| {cls} | {int(z.n)} | {fmt_pct(z.share)} | {z.median_intervals:.1f} / {4*z.median_intervals:.0f}h | {z.p75_intervals:.1f} | {z.p90_intervals:.1f} | {int(z.one_bar_n)} | {int(z.two_bar_n)} | {int(z.three_plus_n)} |')
    lines += ['',f'- Complete directionally bracketed SIDEWAYS episodes: **{btotal}**.',
              f'- Resume same directional state: **{same_n}/{btotal} = {fmt_pct(same_n/btotal if btotal else np.nan)}**.',
              f'- Exit to opposite directional state: **{opp_n}/{btotal} = {fmt_pct(opp_n/btotal if btotal else np.nan)}**.']
    for _,z in os.iterrows():
        lines.append(f'- From {z.origin}: resume **{int(z.resume_n)}/{int(z.n)} = {fmt_pct(z.resume_rate)}**; opposite transition **{int(z.opposite_n)}/{int(z.n)} = {fmt_pct(z.opposite_rate)}**.')

    cens=ep[ep.partition.isin(MAJOR) & ~ep.bracketed_directional]
    lines += ['',f'- SIDEWAYS episodes not directionally bracketed / boundary-gap-censored: **{len(cens)}** (reported separately; excluded from bridge denominator).','',
              '## Interpretation boundary','',
              'This result only describes the existing detector state machine. It does not redesign SIDEWAYS. Any persistence/hysteresis/confirmation change requires a new preregistered experiment.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
