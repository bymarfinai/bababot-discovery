from __future__ import annotations

from pathlib import Path
import math
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET = 'BNBUSDT'
BAR5 = pd.Timedelta(minutes=5)
DEV_START = pd.Timestamp('2022-01-01T00:00:00Z')
DEV_END = pd.Timestamp('2025-01-01T00:00:00Z')
EXT_R = 0.30
STOP_R = 0.30
NOTIONAL = b27es.ILLUSTRATIVE_NOTIONAL
PFX = 'BNB_NATIVE_TIMEZONE_M13_B27EY'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_YEARLY = ROOT / f'{PFX}_Yearly.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

ZONES = [
    ('Z00', 0), ('Z04', 4), ('Z08', 8),
    ('Z12', 12), ('Z16', 16), ('Z20', 20),
]


def utc_index(x: pd.DataFrame) -> pd.DataFrame:
    y = x.copy()
    idx = pd.DatetimeIndex(y.index)
    if idx.tz is None:
        idx = idx.tz_localize('UTC')
    else:
        idx = idx.tz_convert('UTC')
    y.index = idx
    return y.sort_index()


def win(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return x[(x.index >= start) & (x.index < end)].copy()


def classify_structure(ref: pd.DataFrame, exe: pd.DataFrame):
    if len(ref) < 47 or len(exe) < 47:
        return {'status': 'INCOMPLETE_WINDOW'}
    H = float(ref.high.max())
    L = float(ref.low.min())
    R = H - L
    if not np.isfinite(R) or R <= 0:
        return {'status': 'BAD_RANGE'}

    state = 'SEEK_K1'
    k1_ts = pd.NaT
    leave_ts = pd.NaT
    h2_ts = pd.NaT
    entry_ts = pd.NaT
    entry_px = np.nan
    entry_signal_ts = pd.NaT
    terminal = 'NO_EVENT_BY_END'
    prev = None

    for ts, row in exe.iterrows():
        o, h, l, c = map(float, [row.open, row.high, row.low, row.close])
        high_touch = (h >= H) and (c <= H)
        low_touch = (l <= L) and (c >= L)
        break_high = c > H
        break_low = c < L

        if state == 'SEEK_K1':
            if (high_touch and low_touch) or (high_touch and break_low) or (low_touch and break_high):
                terminal = 'AMBIGUOUS_BEFORE_K1'
                break
            if break_high:
                terminal = 'BREAK_ABOVE_BEFORE_K1'
                break
            if break_low:
                terminal = 'BREAK_BELOW_BEFORE_K1'
                break
            if low_touch:
                terminal = 'LOW_VISIT_BEFORE_K1'
                break
            if high_touch:
                k1_ts = ts
                state = 'K1_EPISODE'
            prev = row
            continue

        if state == 'K1_EPISODE':
            same_high = (h >= H) and (c <= H)
            if same_high:
                prev = row
                continue
            leave_ts = ts
            state = 'AFTER_LEAVE'
            # The leave candle is a completed post-K1 candle and may itself be a
            # Micro-HL signal, but structural terminal owns the signal bar.

        if state == 'AFTER_LEAVE':
            hit_h2 = h >= H
            hit_opp = c < L
            if hit_h2 and hit_opp:
                terminal = 'AMBIGUOUS_AFTER_LEAVE'
                break
            if hit_h2:
                h2_ts = ts
                terminal = 'H2'
                break
            if hit_opp:
                terminal = 'OPPOSITE_BREAK'
                break

            if pd.isna(entry_ts) and prev is not None:
                micro = (l > float(prev.low)) and (c > float(prev.close)) and (c > o)
                if micro:
                    fill_ts = ts + BAR5
                    if fill_ts in exe.index:
                        entry_signal_ts = ts
                        entry_ts = fill_ts
                        entry_px = float(exe.loc[fill_ts].open)
                    # If the next open is outside the execution block there is no entry.
            prev = row
            continue

        prev = row

    if state == 'K1_EPISODE' and pd.isna(leave_ts):
        terminal = 'NO_CAUSAL_LEAVE_BY_END'
    elif state == 'SEEK_K1' and terminal == 'NO_EVENT_BY_END':
        terminal = 'NO_K1_BY_END'
    elif state == 'AFTER_LEAVE' and terminal == 'NO_EVENT_BY_END':
        terminal = 'NO_H2_BY_END'

    return {
        'status': 'OK', 'H': H, 'L': L, 'R': R,
        'k1_ts': k1_ts, 'leave_ts': leave_ts, 'h2_ts': h2_ts,
        'terminal': terminal, 'entry_signal_ts': entry_signal_ts,
        'entry_ts': entry_ts, 'entry_px': entry_px,
    }


def structural_after_entry(exe: pd.DataFrame, entry_ts: pd.Timestamp, H: float, L: float):
    if pd.isna(entry_ts):
        return 'NO_ENTRY'
    q = exe[exe.index >= entry_ts]
    for _, row in q.iterrows():
        h = float(row.high); c = float(row.close)
        hit_h = h >= H
        hit_l = c < L
        if hit_h and hit_l:
            return 'AMBIGUOUS'
        if hit_h:
            return 'H2'
        if hit_l:
            return 'OPPOSITE_BREAK'
    return 'NO_H2_BY_END'


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg > 0:
        return pos / neg
    return math.inf if pos > 0 else np.nan


def max_dd(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').fillna(0.0).to_numpy(float)
    if len(x) == 0:
        return np.nan
    eq = np.cumsum(x)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def build(x5: pd.DataFrame):
    x5 = utc_index(x5)
    dates = pd.date_range(DEV_START.normalize(), DEV_END.normalize(), freq='D', inclusive='left')
    rows = []
    for d in dates:
        for zone, hour in ZONES:
            ref_start = d + pd.Timedelta(hours=hour)
            ref_end = ref_start + pd.Timedelta(hours=4)
            exe_start = ref_end
            exe_end = exe_start + pd.Timedelta(hours=4)
            if ref_start < DEV_START or exe_end > DEV_END:
                continue
            ref = win(x5, ref_start, ref_end)
            exe = win(x5, exe_start, exe_end)
            st = classify_structure(ref, exe)
            rec = {
                'zone': zone, 'session_date': str(d.date()), 'year': int(d.year),
                'ref_start': ref_start, 'ref_end': ref_end,
                'exec_start': exe_start, 'exec_end': exe_end,
                'ref_bars': len(ref), 'exec_bars': len(exe),
                'status': st.get('status'),
            }
            rec.update(st)
            rec['has_k1'] = bool(pd.notna(rec.get('k1_ts', pd.NaT)))
            rec['has_leave'] = bool(pd.notna(rec.get('leave_ts', pd.NaT)))
            rec['upstream_h2'] = bool(rec.get('terminal') == 'H2')
            rec['has_entry'] = bool(pd.notna(rec.get('entry_ts', pd.NaT)))
            rec['h2_after_entry'] = False
            rec['trade_net_win'] = False
            rec['trade_net_return'] = np.nan
            rec['trade_pnl_usd_500'] = np.nan
            rec['trade_exit_type'] = None
            rec['trade_exit_ts'] = pd.NaT
            rec['trade_rr'] = np.nan
            if rec['has_entry'] and st.get('status') == 'OK':
                H = float(st['H']); L = float(st['L']); R = float(st['R'])
                ent_ts = pd.Timestamp(st['entry_ts']); ent_px = float(st['entry_px'])
                sa = structural_after_entry(exe, ent_ts, H, L)
                rec['entry_structural_terminal'] = sa
                rec['h2_after_entry'] = (sa == 'H2')
                q = exe[exe.index >= ent_ts]
                if not q.empty:
                    z = b27es.simulate_one(q, ent_px, H, R, EXT_R, STOP_R)
                    rec['trade_net_win'] = bool(z['net_win'])
                    rec['trade_net_return'] = float(z['net_return'])
                    rec['trade_pnl_usd_500'] = float(z['pnl_usd_500'])
                    rec['trade_exit_type'] = str(z['exit_type'])
                    rec['trade_exit_ts'] = pd.Timestamp(z['exit_ts'])
                    target = H + EXT_R * R
                    stop = ent_px - STOP_R * R
                    risk = ent_px - stop
                    rec['trade_rr'] = (target - ent_px) / risk if risk > 0 else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


def summarize(d: pd.DataFrame):
    out = []
    for zone, _ in ZONES:
        q = d[(d.zone == zone) & (d.status == 'OK')].copy()
        leaves = q[q.has_leave.astype(bool)]
        ent = q[q.has_entry.astype(bool)].sort_values(['session_date', 'entry_ts'])
        n = len(ent)
        wr = float(ent.trade_net_win.mean()) if n else np.nan
        avg = float(pd.to_numeric(ent.trade_net_return, errors='coerce').mean()) if n else np.nan
        pnl = float(pd.to_numeric(ent.trade_pnl_usd_500, errors='coerce').sum()) if n else 0.0
        pfx = pf(ent.trade_pnl_usd_500) if n else np.nan
        dd = max_dd(ent.trade_pnl_usd_500) if n else np.nan
        h2_leave = float(leaves.upstream_h2.mean()) if len(leaves) else np.nan
        h2_entry = float(ent.h2_after_entry.mean()) if n else np.nan
        med_rr = float(pd.to_numeric(ent.trade_rr, errors='coerce').median()) if n else np.nan
        if n >= 30 and wr >= .70 and pfx > 1.0:
            label = '70_PERCENT_CANDIDATE'
        elif n >= 30 and wr >= .65 and pfx > 1.0:
            label = 'NEAR_CANDIDATE'
        else:
            label = 'NO_CANDIDATE'
        out.append({
            'zone': zone, 'sessions': len(q), 'k1': int(q.has_k1.sum()),
            'leaves': int(q.has_leave.sum()), 'upstream_h2': int(q.upstream_h2.sum()),
            'upstream_h2_rate': h2_leave, 'entries': n,
            'h2_after_entry': int(ent.h2_after_entry.sum()) if n else 0,
            'h2_after_entry_rate': h2_entry,
            'actual_net_wr': wr, 'avg_net_return': avg,
            'total_pnl_usd_500': pnl, 'profit_factor': pfx,
            'max_dd_usd_500': dd, 'median_rr': med_rr, 'candidate_label': label,
        })
    s = pd.DataFrame(out)
    eligible = s[s.entries >= 30].copy().sort_values(
        ['actual_net_wr', 'profit_factor', 'avg_net_return', 'entries'],
        ascending=[False, False, False, False]
    )
    ranks = {z: i + 1 for i, z in enumerate(eligible.zone.tolist())}
    s['wr_rank_n30'] = s.zone.map(ranks)
    return s.sort_values(['wr_rank_n30', 'zone'], na_position='last').reset_index(drop=True)


def yearly(d: pd.DataFrame):
    out = []
    for zone, _ in ZONES:
        for year in (2022, 2023, 2024):
            q = d[(d.zone == zone) & (d.year == year) & d.has_entry.astype(bool)].copy()
            out.append({
                'zone': zone, 'year': year, 'entries': len(q),
                'actual_net_wr': float(q.trade_net_win.mean()) if len(q) else np.nan,
                'profit_factor': pf(q.trade_pnl_usd_500) if len(q) else np.nan,
                'avg_net_return': float(pd.to_numeric(q.trade_net_return, errors='coerce').mean()) if len(q) else np.nan,
                'total_pnl_usd_500': float(pd.to_numeric(q.trade_pnl_usd_500, errors='coerce').sum()) if len(q) else 0.0,
            })
    return pd.DataFrame(out)


def fmt_pct(x):
    return 'NA' if pd.isna(x) else f'{100*x:.1f}%'


def fmt_num(x, n=2):
    return 'NA' if pd.isna(x) else f'{x:.{n}f}'


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    # Prereg filename intentionally differs from prefix; check the frozen file explicitly.
    prereg = ROOT / 'BNB_NATIVE_TIMEZONE_M13_B27EY_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EY preregistration missing')

    x5, cov = b27em.data_base.load5(TARGET)
    if cov < .995:
        raise AssertionError(f'coverage gate failed: {cov}')

    d = build(x5)
    d.to_csv(OUT_DETAIL, index=False)
    s = summarize(d)
    s.to_csv(OUT_SUMMARY, index=False)
    y = yearly(d)
    y.to_csv(OUT_YEARLY, index=False)

    leader = s[s.entries >= 30].sort_values('wr_rank_n30').iloc[0] if (s.entries >= 30).any() else None
    strong = s[s.candidate_label == '70_PERCENT_CANDIDATE']
    near = s[s.candidate_label == 'NEAR_CANDIDATE']

    lines = [
        '# BNB Native Time-Zone / Session Window Discovery — B27EY Result', '',
        f'Raw BNB 5m coverage: **{cov:.4%}**.', '',
        'Discovery partition only: **2022-01-01 → 2025-01-01 UTC**. External/reference-validation/August remain unopened for this hypothesis.', '',
        'Each zone uses a frozen **4h reference block → next 4h execution block**. Entry is causal **E5_MICRO_HL_BULL**; economics are TP **H+0.30R**, SL **0.30R**, total cost **0.15%**.', '',
        '## Coarse UTC zone results', '',
        '| WR rank* | Zone | Ref→Exec UTC | K1 | Leaves | Upstream H2 | Entries | H2-after-entry | Actual net WR | Avg net/trade | PF | PnL @ $500 | Max DD | Med RR | Label |',
        '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|'
    ]
    zone_map = {
        'Z00':'00–04 → 04–08', 'Z04':'04–08 → 08–12', 'Z08':'08–12 → 12–16',
        'Z12':'12–16 → 16–20', 'Z16':'16–20 → 20–24', 'Z20':'20–24 → 00–04',
    }
    for _, r in s.iterrows():
        rank = '-' if pd.isna(r.wr_rank_n30) else str(int(r.wr_rank_n30))
        lines.append(
            f"| {rank} | {r.zone} | {zone_map[r.zone]} | {int(r.k1)} | {int(r.leaves)} | "
            f"{fmt_pct(r.upstream_h2_rate)} | {int(r.entries)} | {fmt_pct(r.h2_after_entry_rate)} | "
            f"**{fmt_pct(r.actual_net_wr)}** | {fmt_pct(r.avg_net_return)} | {fmt_num(r.profit_factor)} | "
            f"${r.total_pnl_usd_500:.2f} | ${r.max_dd_usd_500:.2f} | {fmt_num(r.median_rr)} | {r.candidate_label} |"
        )
    lines += ['', '*WR rank only among zones with N>=30, per preregistration.', '', '## Year-by-year stability', '',
              '| Zone | Year | N | Actual net WR | PF | Avg net/trade | PnL @ $500 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for _, r in y.iterrows():
        lines.append(f"| {r.zone} | {int(r.year)} | {int(r.entries)} | {fmt_pct(r.actual_net_wr)} | {fmt_num(r.profit_factor)} | {fmt_pct(r.avg_net_return)} | ${r.total_pnl_usd_500:.2f} |")

    lines += ['', '## Discovery verdict', '']
    if leader is None:
        lines.append('No zone produced N>=30 actual trades. No candidate can be ranked.')
    else:
        lines.append(f"WR-first development leader: **{leader.zone} ({zone_map[leader.zone]})**, N **{int(leader.entries)}**, actual net WR **{fmt_pct(leader.actual_net_wr)}**, PF **{fmt_num(leader.profit_factor)}**, avg net/trade **{fmt_pct(leader.avg_net_return)}**.")
    if len(strong):
        names = ', '.join(strong.zone.tolist())
        lines.append(f"70%-candidate label achieved by: **{names}**. This is discovery only and requires a fresh holdout milestone.")
    elif len(near):
        names = ', '.join(near.zone.tolist())
        lines.append(f"No 70% candidate. Near-candidate label achieved by: **{names}**.")
    else:
        lines.append('**No zone met the preregistered 65% near-candidate threshold with PF>1 and N>=30.**')

    lines += ['', '**Status: B27EY_BNB_NATIVE_TIMEZONE_DEV_COMPLETE**', '',
              'STOP: no sliding-hour retune, no combined zones, no external/reference-validation/August reveal, no SHORT/live integration.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27EY_BNB_NATIVE_TIMEZONE_DEV_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
