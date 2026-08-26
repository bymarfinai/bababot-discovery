#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import btc_f85_long_b27do_live_executable_exit_b27dq as dq
import btc_f85_long_f15_short_collision_b27dt as dt
import btc_f85_long_f15_short20_raw_5m_signal_parity_b27dw as dw

PFX = 'BTC_F85_LONG_CAUSAL_AMBIGUOUS_TERMINAL_FIX_B27DX'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SENS = ROOT / f'{PFX}_Sensitivity.csv'
OUT_EXTRA = ROOT / f'{PFX}_ExtraTrade.csv'
OUT_PORT = ROOT / f'{PFX}_Portfolio.csv'
OUT_PAR = ROOT / f'{PFX}_Parity.csv'
OUT_MIS = ROOT / f'{PFX}_Mismatches.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

EXPECTED_EXTRA_ID = 'reference_validation|LONG|RAW_0530|2025-09-11 12:30:00+00:00'
BAR5 = pd.Timedelta(minutes=5)


def utc(x):
    t = pd.Timestamp(x)
    return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(pd.Timestamp(start), side='left'))
    b = int(x5.index.searchsorted(pd.Timestamp(end), side='left'))
    return x5.iloc[a:b]


def fixed_exit(entry_start, exec_end, entry_px, f35, e20, x5):
    q = fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError('empty fixed-exit path for corrected candidate')
    reason = None
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    for ts, r in q.iterrows():
        # Frozen B27DE/B27DQ priority: E20 high-touch before completed-close F35 invalidation.
        if float(r.high) >= float(e20):
            exit_bar_start = pd.Timestamp(ts)
            exit_ts = pd.Timestamp(ts)
            exit_px = float(e20)
            reason = 'TP_E20'
            break
        if float(r.close) < float(f35):
            exit_bar_start = pd.Timestamp(ts)
            exit_ts = pd.Timestamp(ts) + BAR5
            exit_px = float(r.close)
            reason = 'CLOSE_INVALIDATION_F35'
            break
    if reason is None:
        pos = int(x5.index.searchsorted(pd.Timestamp(exec_end), side='left'))
        if pos >= len(x5) or x5.index[pos] != pd.Timestamp(exec_end):
            raise AssertionError(f'missing time-exit bar {exec_end}')
        exit_bar_start = pd.Timestamp(exec_end)
        exit_ts = pd.Timestamp(exec_end)
        exit_px = float(x5.iloc[pos].open)
        reason = 'TIME_EXIT_EXEC_END'
    gross = float(exit_px / float(entry_px) - 1.0)
    net = gross * dq.dn.dl.NOTIONAL - dq.dn.dl.FEE
    return {
        'exit_bar_start': exit_bar_start,
        'exit_ts': exit_ts,
        'exit_px': float(exit_px),
        'exit_reason': reason,
        'gross_return': gross,
        'net_pnl_usd': net,
        'tp_hit': reason == 'TP_E20',
        'time_exit': reason == 'TIME_EXIT_EXEC_END',
    }


def make_extra_fixed(stream, er, x5):
    zone = str(er.source).replace('LONG_', '', 1)
    entry_ts = utc(er.entry_ts)
    clock_min = int(er.clock_min_norm)
    ref_start = entry_ts.normalize() + pd.Timedelta(minutes=clock_min)
    # The identified B27DX omission is RAW_0530 on the same UTC anchor day.
    if zone != 'RAW_0530' or clock_min != 330:
        raise AssertionError(f'unexpected B27DX extra geometry {zone=} {clock_min=}')
    ref_end = ref_start + pd.Timedelta(hours=5, minutes=30)
    exec_start = ref_end
    exec_end = exec_start + pd.Timedelta(hours=6, minutes=30)
    if not (exec_start <= entry_ts < exec_end):
        raise AssertionError('extra entry outside frozen execution window')

    ref = fast_slice(x5, ref_start, ref_end)
    if len(ref) != 66:
        raise AssertionError(f'extra reference bars={len(ref)}')
    H = float(ref.high.max()); L = float(ref.low.min()); R = H - L
    if not dw.near(H, er.H) or not dw.near(L, er.L) or not dw.near(R, er['range']):
        raise AssertionError('extra raw reference H/L/R mismatch')
    hv = ref.high.to_numpy(float); lv = ref.low.to_numpy(float)
    hi = np.flatnonzero(np.isclose(hv, H, rtol=0.0, atol=max(1e-10, abs(H)*1e-12)))
    li = np.flatnonzero(np.isclose(lv, L, rtol=0.0, atol=max(1e-10, abs(L)*1e-12)))
    completion = max(ref.index[int(hi[0])], ref.index[int(li[0])])
    completion_elapsed = float((completion - ref_start) / pd.Timedelta(minutes=1))
    if completion_elapsed < 165.0:
        raise AssertionError('RAW_0530 extra would fail frozen range-completion filter')

    F85 = L + 0.85 * R
    F35 = L + 0.35 * R
    E20 = H + 0.20 * R
    if not (dw.near(F85, er.entry_level) and dw.near(F35, er.stop_level) and dw.near(E20, er.target_level)):
        raise AssertionError('extra F85/F35/E20 mismatch')
    fx = fixed_exit(entry_ts, exec_end, float(er.entry_px), F35, E20, x5)

    z = {c: np.nan for c in stream.columns}
    vals = {
        'partition': str(er.partition),
        'zone': zone,
        'clock_min': clock_min,
        'anchor_date_utc': str(ref_start.date()),
        'reference_start': ref_start,
        'reference_end': ref_end,
        'execution_start': exec_start,
        'execution_end': exec_end,
        'H': H,
        'L': L,
        'range': R,
        'F85': F85,
        'F35': F35,
        'E20': E20,
        'touch_bar_start': utc(er.confirmation_bar_start),
        'same_bar_confirmed': True,
        'entry_executed': True,
        'entry_bar_start': entry_ts,
        'entry_px': float(er.entry_px),
        'entry_fraction': (float(er.entry_px) - L) / R,
        'nominal_rr': (E20 - float(er.entry_px)) / (float(er.entry_px) - F35),
        'case_status': 'TRADE_EXECUTED',
        'primary_eligible': False,
        'range_completion_ts': completion,
        'range_completion_elapsed_min': completion_elapsed,
        'range_completion_age_min': float((exec_start - completion) / pd.Timedelta(minutes=1)),
        'range_completed_second_half': True,
        **fx,
    }
    for k, v in vals.items():
        if k in z:
            z[k] = v
    return pd.DataFrame([z], columns=stream.columns), vals


def attach_live_hybrid_safe(stream, x5):
    live = dq.attach_live_runner(stream, x5)
    h = dt.build_hybrid_safe(stream, live)
    # DQ sensitivity only needs the exit reason to identify exchange-stop fills.
    h['live_exit_reason'] = None
    mask = h.zone.isin(dq.RUNNER_ZONES)
    h.loc[mask, 'live_exit_reason'] = live.loc[mask, 'live_exit_reason'].astype(object).tolist()
    return h, live


def add_ids(q):
    d = q.copy()
    d['entry_bar_start'] = pd.to_datetime(d.entry_bar_start, utc=True)
    d['candidate_id'] = d.partition.astype(str) + '|LONG|' + d.zone.astype(str) + '|' + d.entry_bar_start.astype(str)
    return d


def corrected_entry_table(h):
    L = h.copy()
    L['entry_ts'] = pd.to_datetime(L.entry_bar_start, utc=True)
    out = pd.DataFrame({
        'partition': L.partition.astype(str),
        'side': 'LONG',
        'source': 'LONG_' + L.zone.astype(str),
        'clock_min_norm': pd.to_numeric(L.clock_min).astype(int),
        'entry_ts': L.entry_ts,
        'entry_px': pd.to_numeric(L.entry_px),
        'confirmation_bar_start': pd.to_datetime(L.touch_bar_start, utc=True),
        'H': pd.to_numeric(L.H),
        'L': pd.to_numeric(L.L),
        'range': pd.to_numeric(L['range']),
        'entry_level': pd.to_numeric(L.F85),
        'stop_level': pd.to_numeric(L.F35),
        'target_level': pd.to_numeric(L.E20),
        'touch_elapsed_min': (pd.to_datetime(L.touch_bar_start, utc=True) - pd.to_datetime(L.execution_start, utc=True)) / pd.Timedelta(minutes=1),
    })
    out['candidate_id'] = out.partition.astype(str) + '|LONG|' + L.zone.astype(str) + '|' + out.entry_ts.astype(str)
    return out


def pooled(d):
    return d[d.partition.isin(dt.MAJOR)].copy()


def main():
    x5, coverage = dq.dn.dl.dj.b21.load5()

    # Gate 1: reproduce B27DW's exact one-candidate causal divergence before changing bookkeeping.
    generated, sessions = dw.replay_raw(x5)
    eL_old, eS, prior_hybrid, short_cases, prior_base = dw.canonical(x5)
    gL = generated[generated.side == 'LONG'].copy()
    old_ids = set(eL_old.candidate_id.astype(str))
    gen_ids = set(gL.candidate_id.astype(str))
    missing_old = sorted(old_ids - gen_ids)
    extras = sorted(gen_ids - old_ids)
    if missing_old or extras != [EXPECTED_EXTRA_ID]:
        raise AssertionError(f'B27DX prerequisite divergence changed: missing={missing_old} extras={extras}')
    er = gL[gL.candidate_id == EXPECTED_EXTRA_ID].iloc[0]

    # Gate 2: append only that causal candidate to the pre-runner historical stream.
    fixed_stream = dq.dn.dl.load_stream(x5)
    if len(fixed_stream) != 244:
        raise AssertionError(f'expected prior fixed LONG universe 244, got {len(fixed_stream)}')
    extra_df, extra_vals = make_extra_fixed(fixed_stream, er, x5)
    corrected_fixed = pd.concat([fixed_stream, extra_df], ignore_index=True, sort=False)
    if len(corrected_fixed) != 245:
        raise AssertionError('corrected fixed universe is not prior 244 + exactly one')

    corrected_hybrid, live = attach_live_hybrid_safe(corrected_fixed, x5)
    corrected_hybrid = add_ids(corrected_hybrid)

    # Raw signal identity/geometry against the corrected canonical stream.
    corrected_entries = corrected_entry_table(corrected_hybrid)
    parity_rows = []
    mismatches = []
    dw.compare(parity_rows, mismatches, 'LONG_CORRECTED', gL, corrected_entries)
    parity = pd.DataFrame(parity_rows).rename(columns={'pass_': 'pass'})
    parity.to_csv(OUT_PAR, index=False)
    pd.DataFrame(mismatches, columns=['side','candidate_id','field','generated','expected']).to_csv(OUT_MIS, index=False)
    raw_parity_ok = bool(parity['pass'].all()) and len(mismatches) == 0

    # Re-score corrected B27DQ management and global one-BTC lock.
    sum0, _, details0, pool0 = dq.score_variant(corrected_hybrid, 'B27DX_CORRECTED_LIVE_EXEC_NPLUS2')
    summary_row = sum0[sum0.partition == 'POOLED_MAJOR'].iloc[0]
    corrected_locked = pd.concat(details0, ignore_index=True)
    corrected_locked = add_ids(corrected_locked)

    sens_rows = []
    for bps in (0, 2, 5, 10):
        stressed = dq.apply_stop_slippage(corrected_hybrid, bps)
        ss, _, _, _ = dq.score_variant(stressed, f'B27DX_STOPSLIP_{bps}BPS')
        r = ss[ss.partition == 'POOLED_MAJOR'].iloc[0]
        sens_rows.append({
            'stop_slippage_bps': bps,
            'accepted': int(r.accepted),
            'wr': float(r.wr),
            'pf': float(r.pf),
            'expectancy': float(r.expectancy),
            'total_net': float(r.total_net),
            'max_loss_streak': int(r.max_loss_streak),
        })
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(OUT_SENS, index=False)
    s5 = sens[sens.stop_slippage_bps == 5].iloc[0]

    # Persist the exact corrected extra candidate's fixed and live-executable outcome and lock status.
    ex_lock = corrected_locked[corrected_locked.candidate_id == EXPECTED_EXTRA_ID].copy()
    if len(ex_lock) != 1:
        raise AssertionError(f'extra corrected candidate lock rows={len(ex_lock)}')
    ex_idx = corrected_hybrid.index[corrected_hybrid.candidate_id == EXPECTED_EXTRA_ID]
    if len(ex_idx) != 1:
        raise AssertionError('extra corrected hybrid identity missing/duplicate')
    ix = int(ex_idx[0])
    extra_out = pd.DataFrame([{
        'candidate_id': EXPECTED_EXTRA_ID,
        'partition': str(er.partition),
        'zone': 'RAW_0530',
        'entry_ts': utc(er.entry_ts),
        'entry_px': float(er.entry_px),
        'confirmation_bar_start': utc(er.confirmation_bar_start),
        'H': float(er.H), 'L': float(er.L), 'range': float(er['range']),
        'F85': float(er.entry_level), 'F35': float(er.stop_level), 'E20': float(er.target_level),
        'fixed_exit_ts': utc(extra_vals['exit_ts']),
        'fixed_exit_px': float(extra_vals['exit_px']),
        'fixed_exit_reason': str(extra_vals['exit_reason']),
        'fixed_net_pnl_usd': float(extra_vals['net_pnl_usd']),
        'live_exit_ts': utc(live.iloc[ix].live_exit_ts),
        'live_exit_px': float(live.iloc[ix].live_exit_px),
        'live_exit_reason': str(live.iloc[ix].live_exit_reason),
        'live_net_pnl_usd': float(live.iloc[ix].live_net_pnl_usd),
        'accepted_global_long_lock': bool(ex_lock.iloc[0].accepted),
    }])
    extra_out.to_csv(OUT_EXTRA, index=False)

    # Re-score corrected LONG + frozen SHORT20 FIRST_SIGNAL_WINS.
    rawL = dt.normalize_long(corrected_hybrid)
    acceptedL = dt.normalize_long(corrected_locked, accepted_source=True)
    short20 = dt.normalize_short(short_cases)
    short20 = short20[short20.clock_min_norm == 1200].copy()
    fs = dt.lock_rows(pd.concat([rawL, short20], ignore_index=True), 'B27DX_LONG_PLUS_SHORT20')
    fs_acc = fs[fs.accepted_portfolio.astype(bool)].copy()
    long_m = dt.metrics(pooled(acceptedL))
    combined_m = dt.metrics(pooled(fs_acc))
    fs_long = pooled(fs_acc[fs_acc.side == 'LONG'])
    fs_short = pooled(fs_acc[fs_acc.side == 'SHORT'])
    displaced = set(pooled(acceptedL).candidate_id.astype(str)) - set(fs_long.candidate_id.astype(str))
    portfolio = pd.DataFrame([
        {'scenario': 'CORRECTED_LONG_ONLY', **long_m, 'long_n': long_m['n'], 'short_n': 0, 'delta_vs_long': 0.0, 'displaced_long_n': 0},
        {'scenario': 'CORRECTED_LONG_PLUS_SHORT20', **combined_m, 'long_n': len(fs_long), 'short_n': len(fs_short), 'delta_vs_long': combined_m['net'] - long_m['net'], 'displaced_long_n': len(displaced)},
    ])
    portfolio.to_csv(OUT_PORT, index=False)

    # Formal preregistered gates.
    gate_exact_omission = len(missing_old) == 0 and extras == [EXPECTED_EXTRA_ID]
    gate_universe = len(corrected_fixed) == 245 and len(fixed_stream) == 244
    gate_primary = bool(
        float(summary_row.wr) >= 0.70
        and float(summary_row.pf) >= 2.0
        and float(summary_row.total_net) > 250.0
        and int(summary_row.max_loss_streak) <= 4
    )
    gate_5bps = bool(float(s5.pf) > 1.8 and float(s5.total_net) > 200.0)
    gate_port = bool(combined_m['net'] > long_m['net'])
    support = bool(gate_exact_omission and gate_universe and raw_parity_ok and gate_primary and gate_5bps and gate_port)
    status = 'B27DX_CAUSAL_LONG_CORRECTION_SUPPORTED' if support else 'B27DX_CAUSAL_LONG_CORRECTION_NOT_SUPPORTED'
    OUT_STATUS.write_text(status + '\n')

    summary = pd.DataFrame([
        {'gate': 'exact_one_future_dependent_omission', 'pass': gate_exact_omission, 'actual': f'missing={len(missing_old)} extra={extras}'},
        {'gate': 'corrected_candidate_universe_244_plus_1', 'pass': gate_universe, 'actual': len(corrected_fixed)},
        {'gate': 'corrected_raw_signal_geometry_parity', 'pass': raw_parity_ok, 'actual': f'generated={len(gL)} mismatches={len(mismatches)}'},
        {'gate': 'corrected_long_wr_pf_net_streak', 'pass': gate_primary, 'actual': f'N={int(summary_row.accepted)} WR={summary_row.wr:.6f} PF={summary_row.pf:.6f} net={summary_row.total_net:.6f} maxLS={int(summary_row.max_loss_streak)}'},
        {'gate': 'five_bps_stop_slippage', 'pass': gate_5bps, 'actual': f'WR={s5.wr:.6f} PF={s5.pf:.6f} net={s5.total_net:.6f}'},
        {'gate': 'corrected_long_plus_short20_incremental_positive', 'pass': gate_port, 'actual': f'long={long_m["net"]:.6f} combined={combined_m["net"]:.6f} delta={combined_m["net"]-long_m["net"]:.6f}'},
    ])
    summary.to_csv(OUT_SUM, index=False)

    ex = extra_out.iloc[0]
    lines = [
        '# B27DX — F85 LONG Future-Ambiguous-Terminal Causality Correction — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**; raw causal sessions replayed: **{sessions:,}**.', '',
        'No strategy parameter was changed. The only correction is removal of the future-dependent session veto after a causally completed F85 signal.', '',
        '## Causal identity repair', '',
        f'- Prior canonical LONG candidates: **{len(eL_old)}**.',
        f'- Raw causal LONG candidates: **{len(gL)}**.',
        f'- Missing prior canonical candidates in raw replay: **{len(missing_old)}**.',
        f'- Exact future-dependent omission added: **{EXPECTED_EXTRA_ID}**.',
        f'- Corrected raw-signal geometry mismatches: **{len(mismatches)}**.', '',
        '## Corrected pooled-major LONG', '',
        '| N | WR | PF | Expectancy | Net | Max loss streak |',
        '|---:|---:|---:|---:|---:|---:|',
        f'| {int(summary_row.accepted)} | {pct(summary_row.wr)} | {num(summary_row.pf)} | {usd(summary_row.expectancy)} | {usd(summary_row.total_net)} | {int(summary_row.max_loss_streak)} |', '',
        '## Exact added trade', '',
        f'- Entry: **{ex.entry_ts} @ {float(ex.entry_px):.2f}**.',
        f'- Fixed bookkeeping exit: **{ex.fixed_exit_reason} @ {float(ex.fixed_exit_px):.2f}**, net **{usd(ex.fixed_net_pnl_usd)}**.',
        f'- Frozen B27DQ live-executable exit: **{ex.live_exit_reason} @ {float(ex.live_exit_px):.2f}**, net **{usd(ex.live_net_pnl_usd)}**.',
        f'- Accepted by corrected global LONG lock: **{bool(ex.accepted_global_long_lock)}**.', '',
        '## Stop-slippage sensitivity', '',
        '| Stop slippage | N | WR | PF | Net | Max LS |',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for r in sens.itertuples(index=False):
        lines.append(f'| {int(r.stop_slippage_bps)} bps | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')
    lines += ['', '## Corrected portfolio', '',
              '| Scenario | N | WR | PF | Net | LONG N | SHORT N | Delta vs LONG | Displaced LONG |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in portfolio.itertuples(index=False):
        lines.append(f'| {r.scenario} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} | {int(r.long_n)} | {int(r.short_n)} | {usd(r.delta_vs_long)} | {int(r.displaced_long_n)} |')
    lines += ['', '## Preregistered gates', '']
    for _, r in summary.iterrows():
        lines.append(f'- {r["gate"]}: **{"PASS" if bool(r["pass"]) else "FAIL"}** — {r["actual"]}')
    lines += ['', f'**Status: {status}**', '', 'Research/shadow engineering only. No exchange writes; legacy `bbc_live.py` unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())
    if not support:
        raise AssertionError(status)


if __name__ == '__main__':
    main()
