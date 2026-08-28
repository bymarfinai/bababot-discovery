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
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET = 'BNBUSDT'
BAR5 = pd.Timedelta(minutes=5)
CAND = 'E5_MICRO_HL_BULL'
EXT_R = 0.30
STOP_R = 0.30
COST = b27es.TOTAL_COST
NOTIONAL = b27es.ILLUSTRATIVE_NOTIONAL
PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M12_CONDITIONAL_REPAIR_B27EX'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

ACTIONS = [
    'BASELINE',
    'T05_EXIT_REENTER_FRESH_MICROHL',
    'T10_EXIT_REENTER_FRESH_MICROHL',
    'T15_EXIT_REENTER_FRESH_MICROHL',
    'T20_EXIT_REENTER_FRESH_MICROHL',
]
TRIGGER_R = {
    'T05_EXIT_REENTER_FRESH_MICROHL': 0.05,
    'T10_EXIT_REENTER_FRESH_MICROHL': 0.10,
    'T15_EXIT_REENTER_FRESH_MICROHL': 0.15,
    'T20_EXIT_REENTER_FRESH_MICROHL': 0.20,
}


def basic_sim(q, entry_px, H, R):
    z = b27es.simulate_one(q, float(entry_px), float(H), float(R), EXT_R, STOP_R)
    z.update({'executed': True, 'trade_legs': 1})
    return z


def failed_before_h(q, base, H):
    if bool(base['net_win']):
        return False
    et = pd.Timestamp(base['exit_ts'])
    pre = q[q.index < et] if str(base['exit_type']) in ('SL', 'SL_BOTH') else q[q.index <= et]
    return not bool((not pre.empty) and float(pre.high.max()) >= float(H))


def fresh_microhl_reentry(exe, start_ts, H, R):
    scan = exe[exe.index >= pd.Timestamp(start_ts)]
    if scan.empty:
        return None
    prev_ts = scan.index[0] - BAR5
    prev = exe.loc[prev_ts] if prev_ts in exe.index else None
    for ts, row in scan.iterrows():
        if prev is not None:
            o, l, c = float(row.open), float(row.low), float(row.close)
            if (l > float(prev.low)) and (c > float(prev.close)) and (c > o):
                fill_ts = ts + BAR5
                if fill_ts not in exe.index:
                    return None
                px = float(exe.loc[fill_ts].open)
                post = exe[exe.index >= fill_ts]
                if post.empty:
                    return None
                z = basic_sim(post, px, H, R)
                z.update({'repair_entry_ts': fill_ts, 'repair_entry_px': px, 'repair_signal_ts': ts})
                return z
        prev = row
    return None


def conditional_repair(exe, q, entry_px, H, R, trigger_r, baseline):
    orig_stop = float(entry_px) - STOP_R * float(R)
    trig_px = float(entry_px) - float(trigger_r) * float(R)
    base_exit_ts = pd.Timestamp(baseline['exit_ts'])
    base_exit_type = str(baseline['exit_type'])

    # Only inspect bars that occur before the frozen baseline barrier exit.
    horizon = q[q.index <= base_exit_ts] if base_exit_type == 'SESSION_CLOSE' else q[q.index < base_exit_ts]
    h_reached = False
    trigger_ts = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan

    for ts, bar in horizon.iterrows():
        high = float(bar.high)
        low = float(bar.low)
        # Once H has been reached, repair is permanently disabled for this opportunity.
        if high >= float(H):
            h_reached = True
            break
        # If the original stop is touched, baseline owns the bar; no causal repair is possible.
        if low <= orig_stop:
            break
        # Valid completed-bar adverse trigger. high < H is already guaranteed above.
        if low <= trig_px:
            nxt = ts + BAR5
            if nxt not in exe.index:
                break
            trigger_ts = ts
            exit_ts = nxt
            exit_px = float(exe.loc[nxt].open)
            break

    if pd.isna(trigger_ts) or h_reached:
        z = dict(baseline)
        z.update({
            'triggered': False, 'repair_reentered': False,
            'trigger_ts': pd.NaT, 'trigger_r': trigger_r,
            'first_leg_exit_ts': pd.NaT, 'first_leg_exit_px': np.nan,
            'trade_legs': 1, 'executed': True,
            'pnl_usd_500': float(baseline['net_return']) * NOTIONAL,
        })
        return z

    first_gross = float(exit_px) / float(entry_px) - 1.0
    first_net = first_gross - COST
    repair = fresh_microhl_reentry(exe, exit_ts, H, R)

    if repair is None:
        total_net = first_net
        return {
            'triggered': True, 'repair_reentered': False,
            'trigger_ts': trigger_ts, 'trigger_r': trigger_r,
            'first_leg_exit_ts': exit_ts, 'first_leg_exit_px': exit_px,
            'exit_type': 'TRIGGER_EXIT_NO_REENTRY', 'exit_ts': exit_ts, 'exit_px': exit_px,
            'net_return': total_net, 'pnl_usd_500': total_net * NOTIONAL,
            'net_win': total_net > 0, 'trade_legs': 1, 'executed': True,
            'repair_entry_ts': pd.NaT, 'repair_entry_px': np.nan,
        }

    total_net = first_net + float(repair['net_return'])
    return {
        'triggered': True, 'repair_reentered': True,
        'trigger_ts': trigger_ts, 'trigger_r': trigger_r,
        'first_leg_exit_ts': exit_ts, 'first_leg_exit_px': exit_px,
        'exit_type': f"REPAIR_{repair['exit_type']}", 'exit_ts': repair['exit_ts'], 'exit_px': repair['exit_px'],
        'net_return': total_net, 'pnl_usd_500': total_net * NOTIONAL,
        'net_win': total_net > 0, 'trade_legs': 2, 'executed': True,
        'repair_entry_ts': repair['repair_entry_ts'], 'repair_entry_px': repair['repair_entry_px'],
        'repair_signal_ts': repair['repair_signal_ts'],
    }


def build(x5):
    entries, exec_map = b27es.build_entries(x5)
    e = entries[entries.candidate == CAND].copy().sort_values('entry_ts')
    if len(e) != 50:
        raise AssertionError(f'expected 50 E5 entries, got {len(e)}')

    sessions = b27em.session_rows(x5)
    dev = sessions[(sessions.partition == 'development') & sessions.leave.fillna(False).astype(bool)].copy()
    smap = {str(r.local_date): r for _, r in dev.iterrows()}

    rows = []
    fb_count = 0
    for _, r in e.iterrows():
        date = str(r.local_date)
        s = smap[date]
        exe = b27em.fs(x5, pd.Timestamp(s.ny_open_utc), pd.Timestamp(s.ny_close_utc))
        q = exec_map[(date, CAND)]
        entry_px = float(r.entry_px); H = float(r.H); R = float(r.R)
        base = basic_sim(q, entry_px, H, R)
        base_win = bool(base['net_win'])
        fb = failed_before_h(q, base, H)
        fb_count += int(fb)

        for action in ACTIONS:
            if action == 'BASELINE':
                z = dict(base)
                z.update({
                    'triggered': False, 'repair_reentered': False, 'trigger_ts': pd.NaT,
                    'trigger_r': np.nan, 'first_leg_exit_ts': pd.NaT, 'first_leg_exit_px': np.nan,
                    'pnl_usd_500': float(base['net_return']) * NOTIONAL, 'trade_legs': 1,
                })
            else:
                z = conditional_repair(exe, q, entry_px, H, R, TRIGGER_R[action], base)

            new_win = bool(z['net_win'])
            if base_win and new_win:
                trans = 'W_TO_W'
            elif base_win:
                trans = 'W_TO_L'
            elif new_win:
                trans = 'L_TO_W'
            else:
                trans = 'L_TO_L'

            rec = {
                'local_date': date, 'action': action,
                'baseline_win': base_win, 'baseline_failed_before_H': fb,
                'baseline_exit_type': str(base['exit_type']),
                'baseline_net_return': float(base['net_return']),
                'transition': trans, 'entry_ts': pd.Timestamp(r.entry_ts),
                'entry_px': entry_px, 'H': H, 'R': R,
            }
            rec.update(z)
            rows.append(rec)

    if fb_count != 19:
        raise AssertionError(f'expected 19 failed-before-H losses, got {fb_count}')
    d = pd.DataFrame(rows).sort_values(['action', 'local_date']).reset_index(drop=True)
    b = d[d.action == 'BASELINE']
    if len(b) != 50 or int(b.net_win.sum()) != 25 or int((~b.net_win).sum()) != 25:
        raise AssertionError('baseline 25/25 integrity failed')
    return d


def pf(vals):
    x = pd.to_numeric(vals, errors='coerce').fillna(0.0)
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    return pos / neg if neg > 0 else (math.inf if pos > 0 else np.nan)


def summarize(d):
    out = []
    for action in ACTIONS:
        q = d[d.action == action].copy()
        fb = q[q.baseline_failed_before_H.astype(bool)]
        bw = q[q.baseline_win.astype(bool)]
        bl = q[~q.baseline_win.astype(bool)]
        out.append({
            'action': action,
            'L_to_W': int((q.transition == 'L_TO_W').sum()),
            'FBH_L_to_W': int((fb.transition == 'L_TO_W').sum()),
            'W_to_W': int((q.transition == 'W_TO_W').sum()),
            'W_to_L': int((q.transition == 'W_TO_L').sum()),
            'net_wins': int(q.net_win.sum()),
            'wr_50': float(q.net_win.mean()),
            'triggered_total': int(q.triggered.fillna(False).sum()),
            'triggered_baseline_winners': int(bw.triggered.fillna(False).sum()),
            'triggered_baseline_losers': int(bl.triggered.fillna(False).sum()),
            'repair_reentries': int(q.repair_reentered.fillna(False).sum()),
            'trade_legs': int(pd.to_numeric(q.trade_legs, errors='coerce').fillna(0).sum()),
            'avg_net_return': float(pd.to_numeric(q.net_return, errors='coerce').mean()),
            'total_pnl_usd_500': float(pd.to_numeric(q.pnl_usd_500, errors='coerce').sum()),
            'profit_factor': pf(q.pnl_usd_500),
        })
    s = pd.DataFrame(out)
    rank = s[s.action != 'BASELINE'].sort_values(
        ['L_to_W', 'FBH_L_to_W', 'W_to_W', 'net_wins', 'avg_net_return'],
        ascending=[False, False, False, False, False]
    ).reset_index(drop=True)
    rank['rank'] = np.arange(1, len(rank) + 1)
    base = s[s.action == 'BASELINE'].copy(); base['rank'] = 0
    return pd.concat([base, rank], ignore_index=True)


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EX preregistration missing')
    x5, cov = b27em.data_base.load5(TARGET)
    if cov < .995:
        raise AssertionError(f'coverage gate failed {cov}')

    d = build(x5); d.to_csv(OUT_DETAIL, index=False)
    s = summarize(d); s.to_csv(OUT_SUM, index=False)
    lead = s[s.action != 'BASELINE'].sort_values('rank').iloc[0]

    lines = [
        '# BNB Session-Native LONG M12 Conditional Repair Trigger Discovery — B27EX Result', '',
        f'Raw BNB 5m coverage: **{cov:.4%}**.', '',
        'Development only. Frozen baseline: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15% per completed leg**.', '',
        'Baseline integrity: **50 opportunities = 25 net wins + 25 net losses**; **19/25 losses failed before H**.', '',
        'Repair preserves the original entry and activates only after a completed adverse bar before H; it exits at next 5m open and allows one fresh-Micro-HL re-entry.', '',
        '| Rank | Conditional repair | L→W | FBH L→W | W→W | W→L | Net wins/50 | WR | Triggered W/L | Reentries | Legs | Avg net/opp | PnL @ $500 | PF |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for _, r in s.sort_values('rank').iterrows():
        lines.append(
            f"| {int(r['rank'])} | {r.action} | {int(r.L_to_W)} | {int(r.FBH_L_to_W)} | {int(r.W_to_W)} | {int(r.W_to_L)} | "
            f"{int(r.net_wins)}/50 | {100*r.wr_50:.1f}% | {int(r.triggered_baseline_winners)}/{int(r.triggered_baseline_losers)} | "
            f"{int(r.repair_reentries)} | {int(r.trade_legs)} | {100*r.avg_net_return:.3f}% | ${r.total_pnl_usd_500:.2f} | {r.profit_factor:.2f} |"
        )

    lines += [
        '', '## Development discovery leader', '',
        f"By preregistered conversion ranking: **{lead.action}** converts **{int(lead.L_to_W)}/25** original losses, including **{int(lead.FBH_L_to_W)}/19** failed-before-H losses, while retaining **{int(lead.W_to_W)}/25** original winners.",
        f"Resulting net-positive opportunities: **{int(lead.net_wins)}/50 ({100*lead.wr_50:.1f}%)**.", '',
        'This is development discovery only. No trigger is validated or promoted here.', '',
        '**Status: B27EX_BNB_CONDITIONAL_REPAIR_TRIGGER_DEV_COMPLETE**', '',
        'STOP: no partial-management combination, no threshold retuning, no external/reference-validation/August reveal, no SHORT/live integration.'
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27EX_BNB_CONDITIONAL_REPAIR_TRIGGER_DEV_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
