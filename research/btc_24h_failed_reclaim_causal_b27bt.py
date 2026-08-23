#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_swing_boundary_invalidation_b27bn as b27bn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Result.md'
OUT_EP = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Status.txt'

H4 = pd.Timedelta(hours=4)
BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')
PATHS = ('NO_BREAK','BREAK_NO_RECLAIM','BREAK_RECLAIM_NO_REBREAK','FAILED_RECLAIM')


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pp(v):
    return '-' if pd.isna(v) else f'{100*float(v):+.1f}pp'


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def classify_age2(x5: pd.DataFrame, ep) -> dict:
    origin = str(ep.origin_state)
    assert origin in ORIGINS
    first_ts = pd.Timestamp(ep.first_sideways_ts)
    start = first_ts
    end = start + H4
    q = fast_slice(x5, start, end)
    assert len(q) == 48, (ep.episode_id, len(q), start, end)
    assert q.index[0] == start and q.index[-1] == end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    boundary = float(ep.frozen_boundary)
    c = q.close.to_numpy(float)
    if origin == 'BULL':
        beyond = c < boundary
        safe = c >= boundary
    else:
        beyond = c > boundary
        safe = c <= boundary

    bidx = np.flatnonzero(beyond)
    path = 'NO_BREAK'
    first_break = None
    first_reclaim = None
    first_rebreak = None

    if len(bidx):
        first_break = int(bidx[0])
        ridx = np.flatnonzero(safe[first_break+1:])
        if not len(ridx):
            path = 'BREAK_NO_RECLAIM'
        else:
            first_reclaim = first_break + 1 + int(ridx[0])
            rbidx = np.flatnonzero(beyond[first_reclaim+1:])
            if not len(rbidx):
                path = 'BREAK_RECLAIM_NO_REBREAK'
            else:
                first_rebreak = first_reclaim + 1 + int(rbidx[0])
                path = 'FAILED_RECLAIM'

    final_4h_beyond = bool(beyond[-1])
    exit_effective = first_ts + int(ep.n_intervals) * H4

    confirm_start = pd.NaT
    confirm_complete = pd.NaT
    eligible_open = pd.NaT
    eligible_before_exit = False
    break_to_reclaim = np.nan
    reclaim_to_rebreak = np.nan
    confirmation_to_exit_hours = np.nan

    if path == 'FAILED_RECLAIM':
        confirm_start = q.index[first_rebreak]
        confirm_complete = confirm_start + BAR5
        eligible_open = confirm_complete
        assert first_break < first_reclaim < first_rebreak
        assert bool(beyond[first_break])
        assert bool(safe[first_reclaim])
        assert bool(beyond[first_rebreak])
        break_to_reclaim = float((first_reclaim-first_break) * 5)
        reclaim_to_rebreak = float((first_rebreak-first_reclaim) * 5)
        confirmation_to_exit_hours = float((exit_effective-confirm_complete) / pd.Timedelta(hours=1))
        eligible_before_exit = bool(eligible_open < exit_effective)
        assert eligible_open > confirm_start

    return {
        'episode_id': int(ep.episode_id),
        'partition': str(ep.partition),
        'origin_state': origin,
        'outcome': str(ep.outcome),
        'transition': bool(ep.transition),
        'resume': not bool(ep.transition),
        'n_intervals': int(ep.n_intervals),
        'first_sideways_ts': first_ts,
        'age2_source_start': start,
        'age2_source_end': end,
        'frozen_boundary': boundary,
        'path_class': path,
        'first_break_pos': np.nan if first_break is None else first_break + 1,
        'first_reclaim_pos': np.nan if first_reclaim is None else first_reclaim + 1,
        'first_rebreak_pos': np.nan if first_rebreak is None else first_rebreak + 1,
        'break_to_reclaim_min': break_to_reclaim,
        'reclaim_to_rebreak_min': reclaim_to_rebreak,
        'confirmation_bar_start': confirm_start,
        'confirmation_complete_ts': confirm_complete,
        'eligible_open_ts': eligible_open,
        'exit_effective_ts': exit_effective,
        'confirmation_to_exit_hours': confirmation_to_exit_hours,
        'eligible_before_exit': eligible_before_exit,
        'age2_final_4h_beyond': final_4h_beyond,
    }


def subset(d, part, origin):
    q = d[d.origin_state == origin].copy()
    if part == 'POOLED_OOS':
        return q[q.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR':
        return q[q.partition.isin(MAJOR)].copy()
    return q[q.partition == part].copy()


def quant(g, col, p):
    return float(g[col].quantile(p)) if len(g) and g[col].notna().any() else np.nan


def summarize(d):
    rows = []
    for part in (*MAJOR, 'POOLED_OOS', 'POOLED_MAJOR'):
        for origin in ORIGINS:
            q = subset(d, part, origin)
            fr = q[q.path_class == 'FAILED_RECLAIM']
            non = q[q.path_class != 'FAILED_RECLAIM']
            base = float(q.transition.mean()) if len(q) else np.nan
            fr_rate = float(fr.transition.mean()) if len(fr) else np.nan
            non_rate = float(non.transition.mean()) if len(non) else np.nan
            rows.append({
                'partition': part,
                'origin': origin,
                'path_class': np.nan,
                'cohort_n': len(q),
                'baseline_transition_rate': base,
                'failed_reclaim_n': len(fr),
                'failed_reclaim_transition_rate': fr_rate,
                'non_failed_reclaim_n': len(non),
                'non_failed_reclaim_transition_rate': non_rate,
                'failed_reclaim_lift_vs_non': fr_rate - non_rate if len(fr) and len(non) else np.nan,
                'fr_final_4h_beyond_rate': float(fr.age2_final_4h_beyond.mean()) if len(fr) else np.nan,
                'fr_median_break_to_reclaim_min': quant(fr, 'break_to_reclaim_min', .5),
                'fr_p25_break_to_reclaim_min': quant(fr, 'break_to_reclaim_min', .25),
                'fr_p75_break_to_reclaim_min': quant(fr, 'break_to_reclaim_min', .75),
                'fr_median_reclaim_to_rebreak_min': quant(fr, 'reclaim_to_rebreak_min', .5),
                'fr_p25_reclaim_to_rebreak_min': quant(fr, 'reclaim_to_rebreak_min', .25),
                'fr_p75_reclaim_to_rebreak_min': quant(fr, 'reclaim_to_rebreak_min', .75),
                'fr_median_confirmation_to_exit_hours': quant(fr, 'confirmation_to_exit_hours', .5),
                'fr_p25_confirmation_to_exit_hours': quant(fr, 'confirmation_to_exit_hours', .25),
                'fr_p75_confirmation_to_exit_hours': quant(fr, 'confirmation_to_exit_hours', .75),
            })
            for path in PATHS:
                g = q[q.path_class == path]
                rows.append({
                    'partition': part,
                    'origin': origin,
                    'path_class': path,
                    'cohort_n': len(q),
                    'path_n': len(g),
                    'path_share': len(g)/len(q) if len(q) else np.nan,
                    'path_transition_rate': float(g.transition.mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)


def top_row(s, part, origin):
    q = s[(s.partition == part) & (s.origin == origin) & s.path_class.isna()]
    assert len(q) == 1
    return q.iloc[0]


def path_row(s, part, origin, path):
    q = s[(s.partition == part) & (s.origin == origin) & (s.path_class == path)]
    assert len(q) == 1
    return q.iloc[0]


def main():
    x5, coverage = b21.load5()
    assert len(x5) == 698112
    assert abs(float(coverage) - 1.0) < 1e-12

    reg = b27bn.build_instrumented_regime(x5)
    parent = b27bn.build_episode_rows(reg, b27bn.load_parent_episodes())
    assert len(parent) == 1023
    assert int((parent.origin_state == 'BULL').sum()) == 532
    assert int((parent.origin_state == 'BEAR').sum()) == 491
    assert int(parent.transition.sum()) == 496
    assert int((~parent.transition).sum()) == 527

    cohort = parent[parent.boundary_available & (parent.n_intervals >= 2)].copy()
    assert len(cohort) > 0

    d = pd.DataFrame([classify_age2(x5, ep) for ep in cohort.itertuples(index=False)])
    assert len(d) == len(cohort)
    assert set(d.path_class.unique()).issubset(set(PATHS))
    assert d.path_class.notna().all()

    fr = d[d.path_class == 'FAILED_RECLAIM'].copy()
    gate_chrono = True
    if len(fr):
        gate_chrono = bool(
            (pd.to_datetime(fr.confirmation_complete_ts, utc=True) <= pd.to_datetime(fr.eligible_open_ts, utc=True)).all()
            and fr.eligible_before_exit.all()
        )

    s = summarize(d)

    gate_identity = True
    gate_48 = True
    gate_sample = True
    gate_rate = True
    gate_lift = True
    gate_parts = True

    for origin in ORIGINS:
        r = top_row(s, 'POOLED_OOS', origin)
        gate_sample = gate_sample and int(r.failed_reclaim_n) >= 10
        gate_rate = gate_rate and float(r.failed_reclaim_transition_rate) >= .65
        gate_lift = gate_lift and float(r.failed_reclaim_lift_vs_non) >= .10
        for part in OOS:
            p = top_row(s, part, origin)
            enough = int(p.failed_reclaim_n) >= 3
            positive = (
                enough and
                pd.notna(p.failed_reclaim_transition_rate) and
                pd.notna(p.non_failed_reclaim_transition_rate) and
                float(p.failed_reclaim_transition_rate) > float(p.non_failed_reclaim_transition_rate)
            )
            gate_parts = gate_parts and positive

    supported = all([gate_identity, gate_48, gate_sample, gate_rate, gate_lift, gate_parts, gate_chrono])
    verdict = 'B27BT_CAUSAL_FAILED_RECLAIM_SUPPORTED' if supported else 'B27BT_CAUSAL_FAILED_RECLAIM_NOT_SUPPORTED'

    d.to_csv(OUT_EP, index=False)
    s.to_csv(OUT_SUM, index=False)
    OUT_STATUS.write_text(verdict + '\n')

    lines = [
        '# B27BT — BTC 24H Age-2 Causal Failed-Reclaim Anatomy — Result','',
        '**Audit status: PASS.** All path classes use only the age-2 raw 5m source interval; the containing 4H final close is diagnostic-only and is not used to classify FAILED_RECLAIM.','',
        'Parent identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**','',
        '## Pooled OOS primary readout','',
        '| Origin | Age-2 cohort N | Baseline P(T) | FAILED_RECLAIM N | P(T|FR) | non-FR P(T) | FR lift | FR final-4H beyond diagnostic |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for origin in ORIGINS:
        r = top_row(s, 'POOLED_OOS', origin)
        lines.append(
            f'| {origin} | {int(r.cohort_n)} | {pct(r.baseline_transition_rate)} | '
            f'{int(r.failed_reclaim_n)} | {pct(r.failed_reclaim_transition_rate)} | '
            f'{pct(r.non_failed_reclaim_transition_rate)} | {pp(r.failed_reclaim_lift_vs_non)} | '
            f'{pct(r.fr_final_4h_beyond_rate)} |'
        )

    lines += ['', '## Pooled OOS path anatomy','',
              '| Origin | Path | N | Share | P(TRANSITION) |',
              '|---|---|---:|---:|---:|']
    for origin in ORIGINS:
        for path in PATHS:
            r = path_row(s, 'POOLED_OOS', origin, path)
            lines.append(f'| {origin} | {path} | {int(r.path_n)} | {pct(r.path_share)} | {pct(r.path_transition_rate)} |')

    lines += ['', '## OOS partition stability','',
              '| Partition | Origin | Cohort N | FR N | P(T|FR) | P(T|non-FR) | Lift |',
              '|---|---|---:|---:|---:|---:|---:|']
    for part in OOS:
        for origin in ORIGINS:
            r = top_row(s, part, origin)
            lines.append(
                f'| {part} | {origin} | {int(r.cohort_n)} | {int(r.failed_reclaim_n)} | '
                f'{pct(r.failed_reclaim_transition_rate)} | {pct(r.non_failed_reclaim_transition_rate)} | '
                f'{pp(r.failed_reclaim_lift_vs_non)} |'
            )

    lines += ['', '## Causal FAILED_RECLAIM timing — pooled OOS','',
              '| Origin | Break->reclaim min median [P25,P75] | Reclaim->rebreak min median [P25,P75] | Confirmation->regime-exit h median [P25,P75] |',
              '|---|---|---|---|']
    for origin in ORIGINS:
        r = top_row(s, 'POOLED_OOS', origin)
        lines.append(
            f'| {origin} | '
            f'{r.fr_median_break_to_reclaim_min:.1f} [{r.fr_p25_break_to_reclaim_min:.1f},{r.fr_p75_break_to_reclaim_min:.1f}] | '
            f'{r.fr_median_reclaim_to_rebreak_min:.1f} [{r.fr_p25_reclaim_to_rebreak_min:.1f},{r.fr_p75_reclaim_to_rebreak_min:.1f}] | '
            f'{r.fr_median_confirmation_to_exit_hours:.2f} [{r.fr_p25_confirmation_to_exit_hours:.2f},{r.fr_p75_confirmation_to_exit_hours:.2f}] |'
        )

    lines += ['', '## Frozen support gate','',
              '- Exact raw-data/detector/parent identity: **PASS**.',
              '- Every eligible episode maps to exactly one 48x5m age-2 path class: **PASS**.',
              f'- Pooled-OOS FAILED_RECLAIM N >=10/origin: **{"PASS" if gate_sample else "FAIL"}**.',
              f'- Pooled-OOS P(T|FAILED_RECLAIM) >=65% both origins: **{"PASS" if gate_rate else "FAIL"}**.',
              f'- Pooled-OOS FR-minus-non-FR transition lift >=10pp both origins: **{"PASS" if gate_lift else "FAIL"}**.',
              f'- External + validation positive FR lift with FR N>=3/cell, both origins: **{"PASS" if gate_parts else "FAIL"}**.',
              f'- Causal confirmation and next 5m eligible open before eventual regime exit: **{"PASS" if gate_chrono else "FAIL"}**.',
              '- Containing 4H final-close status excluded from classification/gate: **PASS**.',
              '- No trading/economic/live BBC change: **PASS**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'A supported result validates only a causal transition discriminator and a post-confirmation observation window. It does not authorize a trade.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
