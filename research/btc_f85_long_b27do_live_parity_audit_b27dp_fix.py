#!/usr/bin/env python3
"""B27DP harness-only fix: keep stable candidate id via enumerate(itertuples()).
No trading/audit semantics changed.
"""
import pandas as pd
import btc_f85_long_b27do_live_parity_audit_b27dp as core


def replay_parity_fixed(stream, x5):
    rows=[]; events_by_id={}; total_checkpoints=0
    for cid, r in enumerate(stream.itertuples(index=False)):
        if r.zone not in core.RUNNER_ZONES:
            continue
        direct = core.dn.runner_exit(r, x5)
        rr = core.restart_replay(r, x5, collect_events=True)
        total_checkpoints += rr['checkpoints']
        ok_ts = pd.Timestamp(rr['exit_ts']) == pd.Timestamp(direct['runner_exit_ts'])
        ok_px = core.close_enough(rr['exit_px'], direct['runner_exit_px'])
        ok_reason = rr['reason'] == direct['runner_exit_reason']
        ok_net = core.close_enough(rr['net'], direct['runner_net_pnl_usd'])
        events_by_id[int(cid)] = rr['events']
        rows.append({
            'audit_id':int(cid), 'partition':r.partition, 'zone':r.zone,
            'entry_bar_start':r.entry_bar_start, 'exit_ts_match':ok_ts,
            'exit_px_match':ok_px, 'exit_reason_match':ok_reason, 'net_match':ok_net,
            'pass':bool(ok_ts and ok_px and ok_reason and ok_net), 'restart_checkpoints':rr['checkpoints'],
        })
    return pd.DataFrame(rows), events_by_id, total_checkpoints

core.replay_parity = replay_parity_fixed
core.main()
