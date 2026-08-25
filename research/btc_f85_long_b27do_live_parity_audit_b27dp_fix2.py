#!/usr/bin/env python3
"""B27DP harness-only fixes: reserved-word rendering + stable candidate id.
No trading or audit-gate semantics changed.
"""
from pathlib import Path
import pandas as pd

SRC = Path(__file__).with_name('btc_f85_long_b27do_live_parity_audit_b27dp.py')
text = SRC.read_text()
old = '''    for r in static.itertuples(index=False):\n        lines.append(f'| {r.check_id} | {r.capability} | {"PASS" if r.pass else "FAIL"} |')'''
new = '''    for _, r in static.iterrows():\n        lines.append(f'| {r["check_id"]} | {r["capability"]} | {"PASS" if bool(r["pass"]) else "FAIL"} |')'''
if old not in text:
    raise RuntimeError('expected B27DP rendering block not found')
text = text.replace(old, new)
ns = {'__name__':'b27dp_dynamic_core', '__file__':str(SRC)}
exec(compile(text, str(SRC), 'exec'), ns)


def replay_parity_fixed(stream, x5):
    rows=[]; events_by_id={}; total_checkpoints=0
    for cid, r in enumerate(stream.itertuples(index=False)):
        if r.zone not in ns['RUNNER_ZONES']:
            continue
        direct = ns['dn'].runner_exit(r, x5)
        rr = ns['restart_replay'](r, x5, collect_events=True)
        total_checkpoints += rr['checkpoints']
        ok_ts = pd.Timestamp(rr['exit_ts']) == pd.Timestamp(direct['runner_exit_ts'])
        ok_px = ns['close_enough'](rr['exit_px'], direct['runner_exit_px'])
        ok_reason = rr['reason'] == direct['runner_exit_reason']
        ok_net = ns['close_enough'](rr['net'], direct['runner_net_pnl_usd'])
        events_by_id[int(cid)] = rr['events']
        rows.append({
            'audit_id':int(cid), 'partition':r.partition, 'zone':r.zone,
            'entry_bar_start':r.entry_bar_start, 'exit_ts_match':ok_ts,
            'exit_px_match':ok_px, 'exit_reason_match':ok_reason, 'net_match':ok_net,
            'pass':bool(ok_ts and ok_px and ok_reason and ok_net),
            'restart_checkpoints':rr['checkpoints'],
        })
    return pd.DataFrame(rows), events_by_id, total_checkpoints

ns['replay_parity'] = replay_parity_fixed
ns['main']()
