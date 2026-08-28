from __future__ import annotations

from pathlib import Path
import sys
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m3_entry_b27eo as b27eo

TARGET = 'BNBUSDT'
BAR5 = pd.Timedelta(minutes=5)
CANDIDATES = list(b27eo.CANDIDATES)
EXTS = [0.00, 0.05, 0.10, 0.20, 0.30, 0.50]
STOPS = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
FEE_ROUNDTRIP = 0.0010
SLIPPAGE = 0.0005
TOTAL_COST = FEE_ROUNDTRIP + SLIPPAGE
ILLUSTRATIVE_NOTIONAL = 500.0
EXPECTED = {
    'E0_NEXT_OPEN': (97, 76),
    'E1_FIRST_BULL_CLOSE': (66, 48),
    'E2_F95_RECLAIM': (21, 20),
    'E3_F90_RECLAIM': (36, 33),
    'E4_F85_RECLAIM': (38, 31),
    'E5_MICRO_HL_BULL': (50, 33),
}

PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M7_ENTRY_ECONOMICS_B27ES'
OUT_ENTRY = ROOT / f'{PFX}_Entry_Detail.csv'
OUT_TARGET = ROOT / f'{PFX}_Target_Hits.csv'
OUT_TARGET_SUM = ROOT / f'{PFX}_Target_Summary.csv'
OUT_GRID_TRADES = ROOT / f'{PFX}_Grid_Trades.csv'
OUT_GRID_SUM = ROOT / f'{PFX}_Grid_Summary.csv'
OUT_LEADERS = ROOT / f'{PFX}_Candidate_Leaders.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.2f}%'


def num(x, n=4):
    return '-' if pd.isna(x) else f'{float(x):.{n}f}'


def build_entries(x5: pd.DataFrame):
    sessions = b27em.session_rows(x5)
    dev = sessions[(sessions.partition == 'development') & sessions.leave.fillna(False).astype(bool)].copy()
    if len(dev) != 97:
        raise AssertionError(f'expected 97 development leaves, got {len(dev)}')
    if int((dev.terminal == 'H2_ARRIVAL').sum()) != 76:
        raise AssertionError('expected 76 development H2')

    rows = []
    exec_map = {}
    for _, s in dev.iterrows():
        ny_open = pd.Timestamp(s.ny_open_utc)
        ny_close = pd.Timestamp(s.ny_close_utc)
        exe = b27em.fs(x5, ny_open, ny_close)
        H = float(s.H); L = float(s.L); R = float(s.R)
        leave_ts = pd.Timestamp(s.leave_ts)
        for cand in CANDIDATES:
            z = b27eo.discover_candidate(cand, exe, leave_ts, H, L, R)
            if not bool(z.get('eligible', False)):
                continue
            entry_ts = pd.Timestamp(z['entry_ts'])
            if entry_ts not in exe.index:
                raise AssertionError(f'missing entry bar {s.local_date} {cand}')
            q = exe[exe.index >= entry_ts].copy()
            if q.empty:
                raise AssertionError(f'empty post-entry horizon {s.local_date} {cand}')
            entry_px = float(z['entry_px'])
            max_high = float(q.high.max())
            min_low = float(q.low.min())
            session_close_px = float(q.iloc[-1].close)
            key = (str(s.local_date), cand)
            exec_map[key] = q
            rows.append({
                'local_date': str(s.local_date),
                'candidate': cand,
                'duration_regime': str(s.duration_regime),
                'entry_ts': entry_ts,
                'entry_px': entry_px,
                'H': H, 'L': L, 'R': R,
                'leave_ts': leave_ts,
                'upstream_terminal': str(s.terminal),
                'b27eo_outcome': str(z['outcome']),
                'b27eo_h2': str(z['outcome']) == 'H2_ARRIVAL',
                'entry_depth_R': float(z['entry_depth_R']),
                'minutes_leave_to_entry': float(z['minutes_leave_to_entry']),
                'session_close_px': session_close_px,
                'mfe_R': max(0.0, (max_high - entry_px) / R),
                'mae_R': max(0.0, (entry_px - min_low) / R),
                'mfe_pct': max(0.0, max_high / entry_px - 1.0),
                'mae_pct': max(0.0, 1.0 - min_low / entry_px),
                'max_extension_above_H_R': max(0.0, (max_high - H) / R),
                'session_close_gross_return': session_close_px / entry_px - 1.0,
                'session_close_net_return': session_close_px / entry_px - 1.0 - TOTAL_COST,
            })
    d = pd.DataFrame(rows).sort_values(['candidate', 'entry_ts']).reset_index(drop=True)
    for cand, (n, h2) in EXPECTED.items():
        z = d[d.candidate == cand]
        got_h2 = int(z.b27eo_h2.sum())
        if len(z) != n or got_h2 != h2:
            raise AssertionError(f'{cand} integrity expected {n}/{h2}, got {len(z)}/{got_h2}')
    return d, exec_map


def build_target_hits(entries, exec_map):
    rows = []
    for _, r in entries.iterrows():
        q = exec_map[(r.local_date, r.candidate)]
        for ext in EXTS:
            target = float(r.H + ext * r.R)
            hitq = q[q.high.astype(float) >= target]
            hit = not hitq.empty
            first_start = hitq.index[0] if hit else pd.NaT
            mins = float(((first_start + BAR5) - pd.Timestamp(r.entry_ts)) / pd.Timedelta(minutes=1)) if hit else np.nan
            rows.append({
                'local_date': r.local_date,
                'candidate': r.candidate,
                'ext_R': ext,
                'target_px': target,
                'hit': hit,
                'first_hit_bar_start': first_start,
                'minutes_entry_to_target_complete': mins,
            })
    t = pd.DataFrame(rows)
    sums = []
    for cand in CANDIDATES:
        for ext in EXTS:
            q = t[(t.candidate == cand) & (t.ext_R == ext)]
            h = q[q.hit]
            sums.append({
                'candidate': cand,
                'ext_R': ext,
                'n': len(q),
                'hit_count': int(q.hit.sum()),
                'hit_rate': float(q.hit.mean()) if len(q) else np.nan,
                'median_minutes_to_target': pd.to_numeric(h.minutes_entry_to_target_complete, errors='coerce').median() if len(h) else np.nan,
            })
    return t, pd.DataFrame(sums)


def simulate_one(q, entry_px, H, R, ext_R, stop_R):
    target_px = H + ext_R * R
    stop_px = entry_px - stop_R * R
    risk = entry_px - stop_px
    reward = target_px - entry_px
    gross_rr = reward / risk if risk > 0 else np.nan
    exit_type = 'SESSION_CLOSE'
    exit_ts = q.index[-1]
    exit_px = float(q.iloc[-1].close)
    collision = False
    for ts, bar in q.iterrows():
        hit_sl = float(bar.low) <= stop_px
        hit_tp = float(bar.high) >= target_px
        if hit_sl:
            collision = bool(hit_tp)
            exit_type = 'SL_BOTH' if collision else 'SL'
            exit_ts = ts
            exit_px = stop_px
            break
        if hit_tp:
            exit_type = 'TP'
            exit_ts = ts
            exit_px = target_px
            break
    gross_return = exit_px / entry_px - 1.0
    net_return = gross_return - TOTAL_COST
    return {
        'ext_R': ext_R, 'stop_R': stop_R,
        'target_px': target_px, 'stop_px': stop_px,
        'gross_rr': gross_rr,
        'exit_type': exit_type,
        'exit_ts': exit_ts,
        'exit_px': exit_px,
        'same_bar_collision': collision,
        'gross_return': gross_return,
        'net_return': net_return,
        'gross_win': gross_return > 0,
        'net_win': net_return > 0,
        'pnl_usd_500': net_return * ILLUSTRATIVE_NOTIONAL,
    }


def build_grid(entries, exec_map):
    rows = []
    for _, r in entries.iterrows():
        q = exec_map[(r.local_date, r.candidate)]
        for ext in EXTS:
            for stop in STOPS:
                z = simulate_one(q, float(r.entry_px), float(r.H), float(r.R), ext, stop)
                z.update({
                    'local_date': r.local_date,
                    'candidate': r.candidate,
                    'entry_ts': r.entry_ts,
                    'entry_px': r.entry_px,
                    'R': r.R,
                })
                rows.append(z)
    g = pd.DataFrame(rows).sort_values(['candidate', 'ext_R', 'stop_R', 'entry_ts']).reset_index(drop=True)
    return g


def max_drawdown(pnls):
    equity = 0.0; peak = 0.0; max_dd = 0.0
    for v in pnls:
        equity += float(v)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def summarize_grid(g):
    rows = []
    for cand in CANDIDATES:
        for ext in EXTS:
            for stop in STOPS:
                q = g[(g.candidate == cand) & (g.ext_R == ext) & (g.stop_R == stop)].sort_values('entry_ts')
                pnl = pd.to_numeric(q.pnl_usd_500, errors='coerce')
                pos = pnl[pnl > 0].sum()
                neg = -pnl[pnl < 0].sum()
                pf = float(pos / neg) if neg > 0 else (math.inf if pos > 0 else np.nan)
                rows.append({
                    'candidate': cand,
                    'ext_R': ext,
                    'stop_R': stop,
                    'trades': len(q),
                    'tp_exits': int((q.exit_type == 'TP').sum()),
                    'sl_exits': int(q.exit_type.isin(['SL', 'SL_BOTH']).sum()),
                    'close_exits': int((q.exit_type == 'SESSION_CLOSE').sum()),
                    'same_bar_collisions': int(q.same_bar_collision.sum()),
                    'gross_win_rate': float(q.gross_win.mean()) if len(q) else np.nan,
                    'net_win_rate': float(q.net_win.mean()) if len(q) else np.nan,
                    'avg_gross_return': float(q.gross_return.mean()) if len(q) else np.nan,
                    'avg_net_return': float(q.net_return.mean()) if len(q) else np.nan,
                    'median_net_return': float(q.net_return.median()) if len(q) else np.nan,
                    'total_pnl_usd_500': float(pnl.sum()),
                    'avg_pnl_usd_500': float(pnl.mean()) if len(q) else np.nan,
                    'profit_factor': pf,
                    'max_drawdown_usd_500': max_drawdown(pnl.tolist()),
                    'median_gross_rr': float(q.gross_rr.median()) if len(q) else np.nan,
                    'rr_ge_1_share': float((q.gross_rr >= 1.0).mean()) if len(q) else np.nan,
                })
    return pd.DataFrame(rows)


def candidate_leaders(entries, grid_sum):
    rows = []
    for cand in CANDIDATES:
        e = entries[entries.candidate == cand]
        q = grid_sum[grid_sum.candidate == cand].copy()
        q = q.sort_values(['avg_net_return', 'profit_factor', 'net_win_rate'], ascending=[False, False, False])
        best = q.iloc[0]
        rrq = q[q.median_gross_rr >= 1.0].copy()
        best_rr = rrq.iloc[0] if len(rrq) else None
        positive = int((q.avg_net_return > 0).sum())
        positive_rr = int(((q.avg_net_return > 0) & (q.median_gross_rr >= 1.0)).sum())
        rows.append({
            'candidate': cand,
            'entries': len(e),
            'b27eo_h2_rate': float(e.b27eo_h2.mean()),
            'median_entry_depth_R': float(e.entry_depth_R.median()),
            'median_mfe_R': float(e.mfe_R.median()),
            'median_mae_R': float(e.mae_R.median()),
            'median_max_extension_above_H_R': float(e.max_extension_above_H_R.median()),
            'positive_cells': positive,
            'positive_cells_share': positive / 36.0,
            'positive_rr1_cells': positive_rr,
            'positive_rr1_cells_share': positive_rr / 36.0,
            'best_ext_R': float(best.ext_R),
            'best_stop_R': float(best.stop_R),
            'best_avg_net_return': float(best.avg_net_return),
            'best_net_win_rate': float(best.net_win_rate),
            'best_total_pnl_usd_500': float(best.total_pnl_usd_500),
            'best_profit_factor': float(best.profit_factor),
            'best_median_gross_rr': float(best.median_gross_rr),
            'best_rr1_ext_R': float(best_rr.ext_R) if best_rr is not None else np.nan,
            'best_rr1_stop_R': float(best_rr.stop_R) if best_rr is not None else np.nan,
            'best_rr1_avg_net_return': float(best_rr.avg_net_return) if best_rr is not None else np.nan,
            'best_rr1_net_win_rate': float(best_rr.net_win_rate) if best_rr is not None else np.nan,
            'best_rr1_total_pnl_usd_500': float(best_rr.total_pnl_usd_500) if best_rr is not None else np.nan,
            'best_rr1_profit_factor': float(best_rr.profit_factor) if best_rr is not None else np.nan,
            'best_rr1_median_gross_rr': float(best_rr.median_gross_rr) if best_rr is not None else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27ES preregistration missing')
    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < 0.995:
        raise AssertionError(f'coverage gate failed {coverage}')

    entries, exec_map = build_entries(x5)
    entries.to_csv(OUT_ENTRY, index=False)
    target_hits, target_sum = build_target_hits(entries, exec_map)
    target_hits.to_csv(OUT_TARGET, index=False)
    target_sum.to_csv(OUT_TARGET_SUM, index=False)
    grid = build_grid(entries, exec_map)
    grid.to_csv(OUT_GRID_TRADES, index=False)
    grid_sum = summarize_grid(grid)
    grid_sum.to_csv(OUT_GRID_SUM, index=False)
    leaders = candidate_leaders(entries, grid_sum)
    leaders.to_csv(OUT_LEADERS, index=False)

    lines = [
        '# BNB Session-Native London→New York LONG M7 Entry Economics Anatomy — B27ES Result', '',
        f'Raw BNB 5m coverage: **{coverage:.4%}**.', '',
        'Economics discovery uses **development only (2022-01-01 → 2025-01-01)** and all frozen B27EO eligible entries. External, reference-validation and August are not used for economics selection.', '',
        'Cost model: **0.10% round-trip fee + 0.05% slippage = 0.15% total cost per trade**. Illustrative PnL uses **$500 notional** ($10 × 50x) with no funding/liquidation model.', '',
        'Intrabar rule: entry at 5m open; TP/SL active on the entry bar; if both are touched in one bar, **SL wins**. Unresolved trades exit at NY session close.', '',
        '## Entry / excursion anatomy', '',
        '| Candidate | N | B27EO H2 | Med entry depth | Med MFE | Med MAE | Med max ext above H | + grid cells | + cells RR>=1 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for _, r in leaders.iterrows():
        lines.append(f"| {r.candidate} | {int(r.entries)} | {pct(r.b27eo_h2_rate)} | {r.median_entry_depth_R:.3f}R | {r.median_mfe_R:.3f}R | {r.median_mae_R:.3f}R | {r.median_max_extension_above_H_R:.3f}R | {int(r.positive_cells)}/36 | {int(r.positive_rr1_cells)}/36 |")

    lines += ['', '## Target reach from actual entry', '',
              '| Candidate | H | H+0.05R | H+0.10R | H+0.20R | H+0.30R | H+0.50R |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for cand in CANDIDATES:
        vals = []
        for ext in EXTS:
            z = target_sum[(target_sum.candidate == cand) & (target_sum.ext_R == ext)].iloc[0]
            vals.append(pct(z.hit_rate))
        lines.append('| ' + cand + ' | ' + ' | '.join(vals) + ' |')

    lines += ['', '## Best development cell per candidate — unrestricted', '',
              '| Candidate | TP extension | Stop | Net WR | Avg net/trade | Total PnL @ $500 | PF | Median RR |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for _, r in leaders.iterrows():
        pf = 'inf' if math.isinf(r.best_profit_factor) else f'{r.best_profit_factor:.2f}'
        lines.append(f"| {r.candidate} | H+{r.best_ext_R:.2f}R | {r.best_stop_R:.2f}R | {pct(r.best_net_win_rate)} | {pct(r.best_avg_net_return)} | ${r.best_total_pnl_usd_500:.2f} | {pf} | {r.best_median_gross_rr:.2f} |")

    lines += ['', '## Best development cell per candidate with median gross RR >= 1.0', '',
              '| Candidate | TP extension | Stop | Net WR | Avg net/trade | Total PnL @ $500 | PF | Median RR |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for _, r in leaders.iterrows():
        if pd.isna(r.best_rr1_ext_R):
            lines.append(f'| {r.candidate} | - | - | - | - | - | - | - |')
        else:
            pf = 'inf' if math.isinf(r.best_rr1_profit_factor) else f'{r.best_rr1_profit_factor:.2f}'
            lines.append(f"| {r.candidate} | H+{r.best_rr1_ext_R:.2f}R | {r.best_rr1_stop_R:.2f}R | {pct(r.best_rr1_net_win_rate)} | {pct(r.best_rr1_avg_net_return)} | ${r.best_rr1_total_pnl_usd_500:.2f} | {pf} | {r.best_rr1_median_gross_rr:.2f} |")

    # Robustness ordering is descriptive only.
    rob = leaders.sort_values(['positive_rr1_cells', 'best_rr1_avg_net_return', 'entries'], ascending=[False, False, False]).reset_index(drop=True)
    top = rob.iloc[0]
    lines += ['', '## Development-only descriptive read', '',
              f'By preregistered robustness ordering, **{top.candidate}** has the largest count of positive-expectancy grid cells with median gross RR >= 1.0: **{int(top.positive_rr1_cells)}/36**.', '',
              'This is **not a promoted setup**. Best-cell numbers are in-sample development economics and require a later frozen holdout test before being called validated trading WR/expectancy.', '',
              '**Status: B27ES_BNB_ALL_ENTRY_ECONOMICS_DEV_COMPLETE**', '',
              'STOP: no holdout economics reveal, no parameter retuning, no August, no H3/breakout-retest, no SHORT/live integration.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27ES_BNB_ALL_ENTRY_ECONOMICS_DEV_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
