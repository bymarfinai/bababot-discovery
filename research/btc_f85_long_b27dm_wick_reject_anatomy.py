#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INFILE = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Detail.csv'
OUT = ROOT / 'BTC_F85_LONG_B27DM_WICK_REJECT_ANATOMY_Result.md'

NOTIONAL = 500.0
FEE = 0.40
MAJOR = {'external','development','reference_validation'}
ZONES = ['ALT_0330','RAW_0530','LONDON','RAW_2330']

d = pd.read_csv(INFILE)
for c in ['entry_px','runner_exit_px','H','L','range','F85','F35','E20','runner_net_pnl_usd']:
    d[c] = pd.to_numeric(d[c], errors='coerce')

q = d[(d['partition'].isin(MAJOR)) & (d['accepted'] == True) & (d['runner_wick_reject'] == True)].copy()
assert len(q) == 92, len(q)
q['bep_px_net'] = q['entry_px'] * (1.0 + FEE/NOTIONAL)
q['exit_ext_R'] = (q['runner_exit_px'] - q['H']) / q['range']
q['drop_from_E20_R'] = (q['E20'] - q['runner_exit_px']) / q['range']
q['exit_vs_entry_pct'] = q['runner_exit_px'] / q['entry_px'] - 1.0
q['exit_vs_e20_pct'] = q['runner_exit_px'] / q['E20'] - 1.0

# Structural buckets are mutually exclusive, from highest to lowest.
def bucket(r):
    x = r.runner_exit_px
    if x >= r.H + 0.10*r['range']:
        return 'E10_to_E20'
    if x >= r.H:
        return 'H_to_E10'
    if x >= r.F85:
        return 'F85_to_H'
    if x >= r.bep_px_net:
        return 'NET_BEP_to_F85'
    if x >= r.entry_px:
        return 'ENTRY_to_NET_BEP'
    return 'BELOW_ENTRY'
q['bucket'] = q.apply(bucket, axis=1)

order = ['E10_to_E20','H_to_E10','F85_to_H','NET_BEP_to_F85','ENTRY_to_NET_BEP','BELOW_ENTRY']
labels = {
'E10_to_E20':'E10–E20 (masih sangat dekat TP)',
'H_to_E10':'H–E10 (masih di atas H)',
'F85_to_H':'F85–H (profit area, di bawah H)',
'NET_BEP_to_F85':'Net-BEP–F85',
'ENTRY_to_NET_BEP':'Entry–Net-BEP (gross +, net ~0/-)',
'BELOW_ENTRY':'Di bawah entry (gross loss)'}

lines = ['# B27DM Wick-Reject Anatomy','',f'Accepted pooled-major wick-reject trades: **{len(q)}**.','']
lines += ['## Where the E20 wick-reject candle closed','', '| Close area | N | Share |','|---|---:|---:|']
for b in order:
    n = int((q.bucket == b).sum())
    lines.append(f'| {labels[b]} | {n} | {n/len(q):.1%} |')

above_h = int((q.runner_exit_px >= q.H).sum())
above_f85 = int((q.runner_exit_px >= q.F85).sum())
above_entry = int((q.runner_exit_px >= q.entry_px).sum())
above_net_bep = int((q.runner_exit_px >= q.bep_px_net).sum())
net_positive = int((q.runner_net_pnl_usd > 0).sum())
net_zeroish = int((q.runner_net_pnl_usd.abs() <= 0.10).sum())

lines += ['', '## Key thresholds','',
 f'- Close still **above H**: **{above_h}/{len(q)} ({above_h/len(q):.1%})**.',
 f'- Close still **at/above F85**: **{above_f85}/{len(q)} ({above_f85/len(q):.1%})**.',
 f'- Close still **at/above entry price**: **{above_entry}/{len(q)} ({above_entry/len(q):.1%})**.',
 f'- Close still **at/above net-BEP price** (fee-adjusted): **{above_net_bep}/{len(q)} ({above_net_bep/len(q):.1%})**.',
 f'- Exit is still **net profitable after $0.40 fee**: **{net_positive}/{len(q)} ({net_positive/len(q):.1%})**.',
 f'- Exit ends **below entry (gross loss)**: **{len(q)-above_entry}/{len(q)} ({(len(q)-above_entry)/len(q):.1%})**.',
 '', '## Distribution statistics','',
 f'- Median close location: **E{100*q.exit_ext_R.median():+.1f}** relative to H (where H=E0, E20=+0.20R).',
 f'- Mean close location: **E{100*q.exit_ext_R.mean():+.1f}**.',
 f'- Median give-back from E20: **{100*q.drop_from_E20_R.median():.1f}% of R**.',
 f'- Mean give-back from E20: **{100*q.drop_from_E20_R.mean():.1f}% of R**.',
 f'- Median exit vs entry: **{100*q.exit_vs_entry_pct.median():+.3f}%**.',
 f'- Median exit vs E20: **{100*q.exit_vs_e20_pct.median():+.3f}%**.',
 f'- Median net PnL of wick rejects: **${q.runner_net_pnl_usd.median():+.2f}**.',
 f'- Mean net PnL of wick rejects: **${q.runner_net_pnl_usd.mean():+.2f}**.',
 '', '## Per-zone wick-reject location','',
 '| Zone | N | Above H | Above entry | Above net-BEP | Net profitable | Median ext vs H | Median net PnL |',
 '|---|---:|---:|---:|---:|---:|---:|---:|']
for z in ZONES:
    a = q[q.zone == z]
    lines.append(f'| {z} | {len(a)} | {(a.runner_exit_px>=a.H).mean():.1%} | {(a.runner_exit_px>=a.entry_px).mean():.1%} | {(a.runner_exit_px>=a.bep_px_net).mean():.1%} | {(a.runner_net_pnl_usd>0).mean():.1%} | E{100*a.exit_ext_R.median():+.1f} | ${a.runner_net_pnl_usd.median():+.2f} |')

OUT.write_text('\n'.join(lines) + '\n')
print(OUT.read_text())
