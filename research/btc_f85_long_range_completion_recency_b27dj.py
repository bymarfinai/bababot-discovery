#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_f85_long_single_position_portfolio_b27dg as dg
import btc_f85_long_0530_2330_filter_b27dh as dh

ROOT = Path(__file__).resolve().parent.parent
B27DH_SUM = ROOT / 'BTC_F85_LONG_0530_2330_FILTER_B27DH_Summary.csv'
OUT_MD = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_Result.md'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_Detail.csv'
OUT_SUM = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_Summary.csv'
OUT_PORT = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_PortfolioSummary.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_RANGE_COMPLETION_RECENCY_B27DJ_Status.txt'

PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
ZONES = ('RAW_0530', 'RAW_2330')
REF_BARS = 66
HALF_REF_MIN = 165.0
BAR5 = pd.Timedelta(minutes=5)


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def close_enough(a, b, tol=1e-9):
    if pd.isna(b):
        return pd.isna(a)
    if math.isinf(float(b)):
        return math.isinf(float(a)) and ((float(a) > 0) == (float(b) > 0))
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_candidates():
    c = dh.load_enriched().copy()
    for col in ('reference_start', 'reference_end', 'execution_start', 'entry_bar_start', 'exit_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    for col in ('H', 'L', 'range', 'net_pnl_usd'):
        c[col] = pd.to_numeric(c[col], errors='coerce')
    c = c[c.zone.isin(('LONDON', 'ALT_0330', *ZONES))].copy()
    assert c.reference_start.notna().all()
    assert c.reference_end.notna().all()
    return c


def attach_range_completion(c: pd.DataFrame, x5: pd.DataFrame):
    q = c.copy()
    rows = []
    parity = []
    for r in q.itertuples(index=False):
        ref = fast_slice(x5, r.reference_start, r.reference_end)
        if len(ref) != REF_BARS:
            raise AssertionError(f'B27DJ reference bar count mismatch {r.zone} {r.reference_start}: {len(ref)}')
        H = float(ref.high.max())
        L = float(ref.low.min())
        hp = close_enough(H, r.H)
        lp = close_enough(L, r.L)
        parity.append({
            'partition': r.partition, 'zone': r.zone, 'reference_start': r.reference_start,
            'check': 'H', 'actual': H, 'expected': r.H, 'pass': hp,
        })
        parity.append({
            'partition': r.partition, 'zone': r.zone, 'reference_start': r.reference_start,
            'check': 'L', 'actual': L, 'expected': r.L, 'pass': lp,
        })
        if not (hp and lp):
            raise AssertionError(f'B27DJ H/L parity failed {r.zone} {r.reference_start}: {H}/{L} vs {r.H}/{r.L}')

        hv = ref.high.to_numpy(float)
        lv = ref.low.to_numpy(float)
        hi = np.flatnonzero(np.isclose(hv, H, rtol=0.0, atol=max(1e-10, abs(H) * 1e-12)))
        li = np.flatnonzero(np.isclose(lv, L, rtol=0.0, atol=max(1e-10, abs(L) * 1e-12)))
        if hi.size == 0 or li.size == 0:
            raise AssertionError('final extreme occurrence not found')
        h_ts = ref.index[int(hi[0])]
        l_ts = ref.index[int(li[0])]
        completion_ts = max(h_ts, l_ts)
        elapsed = float((completion_ts - r.reference_start) / pd.Timedelta(minutes=1))
        age = float((r.execution_start - completion_ts) / pd.Timedelta(minutes=1))
        if elapsed < 0 or age <= 0 or elapsed + age > 330.000001:
            raise AssertionError(f'invalid completion geometry {elapsed=} {age=}')
        rows.append({
            'reference_start': r.reference_start,
            'zone': r.zone,
            'h_formation_ts': h_ts,
            'l_formation_ts': l_ts,
            'range_completion_ts': completion_ts,
            'range_completion_elapsed_min': elapsed,
            'range_completion_age_min': age,
            'range_completed_second_half': bool(elapsed >= HALF_REF_MIN),
        })

    feat = pd.DataFrame(rows)
    keys = ['reference_start', 'zone']
    if feat.duplicated(keys).any():
        # Same reference window can appear only once per rotated clock cohort.
        raise AssertionError('duplicate B27DJ feature keys')
    q = q.merge(feat, on=keys, how='left', validate='many_to_one')
    if q.range_completion_ts.isna().any():
        raise AssertionError('missing B27DJ feature rows')
    return q, pd.DataFrame(parity)


def zone_score(c: pd.DataFrame, zone: str, part: str, use_filter: bool):
    raw = c[(c.partition == part) & (c.zone == zone)].copy()
    f = raw[raw.range_completed_second_half].copy() if use_filter else raw.copy()
    pri = c[(c.partition == part) & c.primary_eligible].copy()
    stream = pd.concat([pri, f], ignore_index=True)
    d = dg.lock(stream, f'B27DJ_{zone}_{part}_{"FILTER" if use_filter else "BASE"}')
    az = d[(d.zone == zone) & d.accepted].copy()
    m = dg.metrics(az)
    return {
        'zone': zone,
        'partition': part,
        'rule': 'RANGE_COMPLETED_SECOND_HALF' if use_filter else 'BASE',
        'raw_n': len(raw),
        'filtered_n': len(f),
        'accepted_n': len(az),
        'blocked_open': len(f) - len(az),
        'accepted_retention': len(az) / len(raw) if len(raw) else np.nan,
        'wins': m['wins'],
        'wr': m['wr'],
        'pf': m['pf'],
        'expectancy': m['expectancy'],
        'total_net': m['total_net'],
    }, d


def raw_parity(c: pd.DataFrame):
    persisted = pd.read_csv(B27DH_SUM)
    rows = []
    for zone in ZONES:
        for part in PARTS:
            actual, _ = zone_score(c, zone, part, use_filter=False)
            q = persisted[(persisted.zone == zone) & (persisted['filter'] == 'BASE') & (persisted.partition == part)]
            assert len(q) == 1, (zone, part, len(q))
            r = q.iloc[0]
            checks = {
                'raw_n': (actual['raw_n'], int(r.raw_n)),
                'accepted_n': (actual['accepted_n'], int(r.accepted_n)),
                'wr': (actual['wr'], float(r.zone_wr)),
                'pf': (actual['pf'], float(r.zone_pf)),
                'expectancy': (actual['expectancy'], float(r.zone_expectancy)),
                'total_net': (actual['total_net'], float(r.zone_total_net)),
            }
            for metric, (a, b) in checks.items():
                ok = int(a) == int(b) if metric in ('raw_n', 'accepted_n') else close_enough(a, b)
                rows.append({'zone': zone, 'partition': part, 'check': f'B27DH_BASE_{metric}', 'actual': a, 'expected': b, 'pass': ok})
    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DJ B27DH BASE parity failed:\n' + out[~out['pass']].to_string(index=False))
    return out


def dev_supported(r):
    return bool(
        r['accepted_n'] >= 20
        and r['accepted_retention'] >= 0.60
        and pd.notna(r['wr']) and r['wr'] >= 0.75
        and pd.notna(r['pf']) and r['pf'] >= 1.30
        and pd.notna(r['expectancy']) and r['expectancy'] > 0
    )


def replication_supported(r):
    return bool(
        r['accepted_n'] >= 10
        and r['accepted_retention'] >= 0.45
        and pd.notna(r['wr']) and r['wr'] >= 0.70
        and pd.notna(r['pf']) and r['pf'] >= 1.20
        and pd.notna(r['expectancy']) and r['expectancy'] > 0
    )


def portfolio(c: pd.DataFrame, supported_zones):
    rows = []
    all_dec = []
    for part in PARTS:
        pri = c[(c.partition == part) & c.primary_eligible].copy()
        adds = []
        for zone in supported_zones:
            raw = c[(c.partition == part) & (c.zone == zone)].copy()
            adds.append(raw[raw.range_completed_second_half].copy())
        stream = pd.concat([pri, *adds], ignore_index=True) if adds else pri.copy()
        d = dg.lock(stream, 'B27DJ_SUPPORTED_PORTFOLIO')
        all_dec.append(d)
        a = d[d.accepted]
        m = dg.metrics(a)
        rows.append({'partition': part, 'candidates': len(d), 'accepted': len(a), 'skipped_open': int((~d.accepted).sum()), **m})
    maj = pd.concat([d for d in all_dec if d.partition.iloc[0] in MAJOR], ignore_index=True)
    a = maj[maj.accepted]
    m = dg.metrics(a)
    rows.append({'partition': 'POOLED_MAJOR', 'candidates': len(maj), 'accepted': len(a), 'skipped_open': int((~maj.accepted).sum()), **m})
    return pd.DataFrame(rows)


def main():
    c = load_candidates()
    x5, coverage = b21.load5()
    c, hl_parity = attach_range_completion(c, x5)
    base_parity = raw_parity(c)
    parity = pd.concat([hl_parity, base_parity], ignore_index=True, sort=False)
    parity.to_csv(OUT_PARITY, index=False)

    # Development is the only partition used for eligibility selection.
    summary_rows = []
    dev_pass = {}
    dev_decisions = []
    for zone in ZONES:
        base, _ = zone_score(c, zone, 'development', use_filter=False)
        filt, d = zone_score(c, zone, 'development', use_filter=True)
        filt['dev_supported'] = dev_supported(filt)
        dev_pass[zone] = bool(filt['dev_supported'])
        summary_rows.extend([base, filt])
        dev_decisions.append(d.assign(evaluation_stage='DEVELOPMENT'))

    replication_pass = {z: False for z in ZONES}
    replication_decisions = []
    for zone in ZONES:
        if not dev_pass[zone]:
            continue
        oks = []
        for part in ('external', 'reference_validation'):
            filt, d = zone_score(c, zone, part, use_filter=True)
            filt['replication_supported_partition'] = replication_supported(filt)
            oks.append(bool(filt['replication_supported_partition']))
            summary_rows.append(filt)
            replication_decisions.append(d.assign(evaluation_stage='HISTORICAL_REPLICATION'))
        replication_pass[zone] = all(oks)

    supported = [z for z in ZONES if dev_pass[z] and replication_pass[z]]
    ports = portfolio(c, supported)
    ports.to_csv(OUT_PORT, index=False)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_SUM, index=False)

    decisions = pd.concat([*dev_decisions, *replication_decisions], ignore_index=True) if replication_decisions else pd.concat(dev_decisions, ignore_index=True)
    decisions.to_csv(OUT_DETAIL, index=False)

    if not any(dev_pass.values()):
        status = 'B27DJ_RANGE_COMPLETION_NOT_SUPPORTED'
    elif not supported:
        status = 'B27DJ_DEV_SUPPORTED_NOT_REPLICATED'
    else:
        status = 'B27DJ_HISTORICAL_REPLICATION_SUPPORTED'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# B27DJ — F85 LONG 05:30 / 23:30 Range-Completion Recency — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**Audit status: PASS.** Every candidate H/L reproduced from the raw 5m reference window and every unfiltered zone reproduced the persisted B27DH BASE metrics before the new discriminator was interpreted.', '',
        'Frozen rule: **RANGE_COMPLETED_SECOND_HALF = final reference range completed at/after minute 165 of the 330-minute reference window.** No alternate cutoff was scored.', '',
        '## Development decision', '',
        '| Zone | Raw N | Filtered | Accepted | Retain | WR | PF | Exp | Net | DEV 75 supported |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for zone in ZONES:
        r = summary[(summary.zone == zone) & (summary.partition == 'development') & (summary.rule == 'RANGE_COMPLETED_SECOND_HALF')].iloc[0]
        lines.append(f'| {zone} | {int(r.raw_n)} | {int(r.filtered_n)} | {int(r.accepted_n)} | {pct(r.accepted_retention)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {"YES" if dev_pass[zone] else "NO"} |')

    lines += ['', '## Reused historical replication', '']
    if not any(dev_pass.values()):
        lines.append('Not opened: neither zone passed the frozen Development gate.')
    else:
        lines += ['| Zone | Partition | Accepted | Retain | WR | PF | Exp | Net | Pass |', '|---|---|---:|---:|---:|---:|---:|---:|---|']
        for zone in ZONES:
            if not dev_pass[zone]:
                continue
            for part in ('external', 'reference_validation'):
                r = summary[(summary.zone == zone) & (summary.partition == part) & (summary.rule == 'RANGE_COMPLETED_SECOND_HALF')].iloc[0]
                ok = replication_supported(r)
                lines.append(f'| {zone} | {part} | {int(r.accepted_n)} | {pct(r.accepted_retention)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {"YES" if ok else "NO"} |')

    lines += ['', '## Supported-zone portfolio', '', f'Historically replication-supported added zones: **{", ".join(supported) if supported else "NONE"}**.', '',
              '| Partition | Candidates | Accepted | Skipped open | WR | PF | Exp | Net |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in ports.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.candidates)} | {int(r.accepted)} | {int(r.skipped_open)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |')

    lines += ['', f'**Status: {status}**', '',
              'Guardrail: external/reference-validation are reused historical confirmation only, not pristine OOS. No live BBC change is authorized.', '',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
