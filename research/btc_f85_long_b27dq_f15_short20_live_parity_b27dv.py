#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bbc_f85_f15_shadow as live
import btc_f85_long_f15_short_collision_b27dt as dt

OUT_MD = ROOT / 'BTC_F85_LONG_B27DQ_F15_SHORT20_LIVE_PARITY_B27DV_Result.md'
OUT_CHECKS = ROOT / 'BTC_F85_LONG_B27DQ_F15_SHORT20_LIVE_PARITY_B27DV_Checks.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_B27DQ_F15_SHORT20_LIVE_PARITY_B27DV_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_B27DQ_F15_SHORT20_LIVE_PARITY_B27DV_Status.txt'


def check(rows, name, passed, detail):
    rows.append({'check': name, 'pass': bool(passed), 'detail': str(detail)})
    if not passed:
        raise AssertionError(f'{name}: {detail}')


def build_frozen_candidates():
    x5, coverage = dt.dq.dn.dl.dj.b21.load5()
    raw, locked, base = dt.build_long(x5)
    rawL = dt.normalize_long(raw)
    baseL = dt.normalize_long(locked, accepted_source=True)
    short_cases = dt.build_shorts(x5)
    shorts = dt.normalize_short(short_cases)
    short20 = shorts[shorts.clock_min_norm == 1200].copy()
    merged = pd.concat([rawL, short20], ignore_index=True)
    expected = dt.lock_rows(merged, 'B27DV_EXPECTED_FIRST_SIGNAL')
    return x5, coverage, rawL, baseL, short20, merged, expected, base


def replay_control_plane(merged, expected, db_path):
    store = live.SQLiteDurableStore(db_path)
    eng = live.ShadowControlPlane('B27DV_PRIMARY', store)
    accepted = []
    restarts = 0

    q = merged.copy()
    q['entry_ts'] = pd.to_datetime(q.entry_ts, utc=True)
    q['exit_ts_norm'] = pd.to_datetime(q.exit_ts_norm, utc=True)
    # Replay candidate-bearing completed-bar boundaries. Exit releases are applied
    # before a same-timestamp new entry because position intervals are [entry,exit).
    for ts, g in q.sort_values(['entry_ts']).groupby('entry_ts', sort=True):
        if eng.state.lifecycle == live.STATE_ACTIVE and eng.state.expected_exit_ts is not None:
            if pd.Timestamp(eng.state.expected_exit_ts) <= pd.Timestamp(ts):
                eng.close_position()
                eng = live.ShadowControlPlane('B27DV_PRIMARY', store)
                restarts += 1
        if eng.state.lifecycle == live.STATE_ENTRY_PENDING:
            raise AssertionError('unexpected unacked entry before next candidate boundary')

        intents = []
        for r in g.itertuples(index=False):
            intents.append({
                'candidate_id': r.candidate_id, 'side': r.side, 'source': r.source,
                'clock_min': int(r.clock_min_norm), 'entry_ts': r.entry_ts,
                'exit_ts': r.exit_ts_norm,
            })
        actions = eng.on_closed_bar(ts, intents)
        if actions:
            a = actions[0]
            # Restart while ENTRY_PENDING_ACK, then ACK. Submit != active.
            pending = live.ShadowControlPlane('B27DV_PRIMARY', store)
            if pending.state.lifecycle != live.STATE_ENTRY_PENDING:
                raise AssertionError('pending entry was not durably restored')
            pending.ack_entry(a['order_id'])
            eng = live.ShadowControlPlane('B27DV_PRIMARY', store)
            if eng.state.lifecycle != live.STATE_ACTIVE:
                raise AssertionError('entry ACK did not durably activate position')
            accepted.append(a['candidate_id'])
            restarts += 2

    return accepted, restarts


def lifecycle_safety_tests(rows):
    base = pd.Timestamp('2026-08-26T00:05:00Z')
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'state.sqlite'
        st = live.SQLiteDurableStore(db)
        e = live.ShadowControlPlane('dup', st)
        it = {'candidate_id':'DUP1','side':'LONG','source':'TEST','clock_min':-1,
              'entry_ts':base,'exit_ts':base+pd.Timedelta(minutes=30)}
        a1 = e.on_closed_bar(base, [it])
        a2 = e.on_closed_bar(base, [it])
        check(rows, 'duplicate_closed_bar_idempotent', len(a1)==1 and len(a2)==0, f'first={len(a1)} duplicate={len(a2)}')
        check(rows, 'entry_not_active_before_ack', e.state.lifecycle==live.STATE_ENTRY_PENDING, e.state.lifecycle)

        # Durable pending restore then ACK.
        e2 = live.ShadowControlPlane('dup', st)
        check(rows, 'restart_restores_entry_pending', e2.state.lifecycle==live.STATE_ENTRY_PENDING and e2.state.entry_order_id==a1[0]['order_id'], e2.state.lifecycle)
        e2.ack_entry(a1[0]['order_id'])
        e3 = live.ShadowControlPlane('dup', st)
        check(rows, 'restart_restores_active', e3.state.lifecycle==live.STATE_ACTIVE, e3.state.lifecycle)

        # Floor stays inactive until ACK and survives restart.
        e3.request_floor(100.0, 'floor-1')
        e4 = live.ShadowControlPlane('dup', st)
        check(rows, 'floor_pending_not_active', e4.state.pending_floor==100.0 and e4.state.active_floor is None, f'pending={e4.state.pending_floor} active={e4.state.active_floor}')
        e4.ack_floor('floor-1')
        e5 = live.ShadowControlPlane('dup', st)
        check(rows, 'floor_ack_activates_durably', e5.state.active_floor==100.0 and e5.state.pending_floor is None, e5.state.active_floor)

    with tempfile.TemporaryDirectory() as td:
        st = live.SQLiteDurableStore(Path(td)/'ooo.sqlite')
        e = live.ShadowControlPlane('ooo', st)
        e.on_closed_bar(base, [])
        rejected = False
        try:
            e.on_closed_bar(base-pd.Timedelta(minutes=5), [])
        except RuntimeError:
            rejected = True
        er = live.ShadowControlPlane('ooo', st)
        check(rows, 'out_of_order_fails_closed', rejected and er.state.lifecycle==live.STATE_HALT, er.state.halt_reason)

    # Two engine instances share one transactional BTC slot.
    with tempfile.TemporaryDirectory() as td:
        st = live.SQLiteDurableStore(Path(td)/'lock.sqlite')
        a = live.ShadowControlPlane('worker-A', st)
        b = live.ShadowControlPlane('worker-B', st)
        ia = {'candidate_id':'LOCK-A','side':'LONG','source':'A','clock_min':-1,'entry_ts':base,'exit_ts':base+pd.Timedelta(hours=1)}
        ib = {'candidate_id':'LOCK-B','side':'SHORT','source':'B','clock_min':1200,'entry_ts':base,'exit_ts':base+pd.Timedelta(hours=1)}
        aa = a.on_closed_bar(base,[ia]); bb = b.on_closed_bar(base,[ib])
        check(rows, 'authoritative_btc_lock_one_winner', len(aa)==1 and len(bb)==0 and st.lock_row()==('worker-A','LOCK-A'), st.lock_row())

    # Exchange reconciliation cases.
    with tempfile.TemporaryDirectory() as td:
        st = live.SQLiteDurableStore(Path(td)/'rec1.sqlite')
        e = live.ShadowControlPlane('adopt', st)
        r = e.reconcile_exchange({'qty':1,'side':'LONG','position_id':'P1','candidate_id':'EX1'})
        check(rows, 'reconcile_adopts_exchange_open', r=='ADOPTED_EXCHANGE_POSITION' and e.state.lifecycle==live.STATE_ACTIVE, r)

    with tempfile.TemporaryDirectory() as td:
        st = live.SQLiteDurableStore(Path(td)/'rec2.sqlite')
        e = live.ShadowControlPlane('stale', st)
        it = {'candidate_id':'ST1','side':'LONG','source':'T','clock_min':-1,'entry_ts':base,'exit_ts':base+pd.Timedelta(hours=1)}
        a=e.on_closed_bar(base,[it]); e.ack_entry(a[0]['order_id'])
        r=e.reconcile_exchange(None)
        check(rows, 'reconcile_clears_stale_local', r=='CLEARED_STALE_LOCAL' and e.state.lifecycle==live.STATE_IDLE and st.lock_row() is None, r)

    with tempfile.TemporaryDirectory() as td:
        st = live.SQLiteDurableStore(Path(td)/'rec3.sqlite')
        e = live.ShadowControlPlane('mis', st)
        it = {'candidate_id':'MM1','side':'LONG','source':'T','clock_min':-1,'entry_ts':base,'exit_ts':base+pd.Timedelta(hours=1)}
        a=e.on_closed_bar(base,[it]); e.ack_entry(a[0]['order_id'])
        r=e.reconcile_exchange({'qty':-1,'side':'SHORT','position_id':'PX'})
        check(rows, 'reconcile_side_mismatch_halts', r=='HALT_SIDE_MISMATCH' and e.state.lifecycle==live.STATE_HALT, r)


def main():
    rows=[]
    x5, coverage, rawL, baseL, short20, merged, expected, base = build_frozen_candidates()

    # Frozen prerequisite controls.
    check(rows, 'b27dq_long_n', int(base['accepted'])==227, base['accepted'])
    check(rows, 'b27dq_long_wr', abs(float(base['wr'])-.7224669603524229)<1e-9, base['wr'])
    check(rows, 'b27dq_long_pf', abs(float(base['pf'])-2.2537382795519254)<.03, base['pf'])
    check(rows, 'b27dq_long_net', abs(float(base['total_net'])-289.75971313529084)<.20, base['total_net'])

    exp_major=expected[expected.partition.isin(dt.MAJOR)].copy()
    exp_acc=exp_major[exp_major.accepted_portfolio.astype(bool)].copy()
    exp_long=exp_acc[exp_acc.side=='LONG']; exp_short=exp_acc[exp_acc.side=='SHORT']
    check(rows, 'b27dt_portfolio_n', len(exp_acc)==283, len(exp_acc))
    check(rows, 'b27dt_long_n', len(exp_long)==227, len(exp_long))
    check(rows, 'b27dt_short20_n', len(exp_short)==56, len(exp_short))
    check(rows, 'b27dt_combined_net', abs(float(exp_acc.pnl.sum())-367.48603546601095)<.20, exp_acc.pnl.sum())

    # Run control plane over pooled-major candidate stream only, because B27DT's
    # 283 gate is a pooled-major control.
    major_merged=merged[merged.partition.isin(dt.MAJOR)].copy()
    with tempfile.TemporaryDirectory() as td:
        accepted,restarts=replay_control_plane(major_merged, exp_major, Path(td)/'primary.sqlite')
    expected_ids=exp_acc.candidate_id.astype(str).tolist()
    check(rows, 'candidate_order_trade_by_trade_parity', accepted==expected_ids, f'actual={len(accepted)} expected={len(expected_ids)} restarts={restarts}')
    check(rows, 'candidate_id_set_parity', set(accepted)==set(expected_ids), f'actual={len(set(accepted))} expected={len(set(expected_ids))}')

    lifecycle_safety_tests(rows)

    # Existing exchange-native STOP_MARKET capability is a dependency, not used
    # by shadow mode.
    baret=(ROOT/'baret_live.py').read_text(errors='replace')
    check(rows, 'exchange_stop_market_capability_present', 'STOP_MARKET' in baret and 'place_algo_order' in baret, 'baret_live conditional STOP_MARKET')

    checks=pd.DataFrame(rows)
    checks.to_csv(OUT_CHECKS,index=False)
    parity=pd.DataFrame([
        {'metric':'B27DQ_LONG_N','actual':int(base['accepted']),'expected':227,'pass':int(base['accepted'])==227},
        {'metric':'B27DT_LONG_SHORT20_N','actual':len(exp_acc),'expected':283,'pass':len(exp_acc)==283},
        {'metric':'B27DT_LONG_N','actual':len(exp_long),'expected':227,'pass':len(exp_long)==227},
        {'metric':'B27DT_SHORT20_N','actual':len(exp_short),'expected':56,'pass':len(exp_short)==56},
        {'metric':'CONTROL_PLANE_ACCEPTED_N','actual':len(accepted),'expected':283,'pass':len(accepted)==283},
    ])
    parity.to_csv(OUT_PARITY,index=False)

    all_pass=bool(checks['pass'].all()) and bool(parity['pass'].all())
    status='B27DV_SHADOW_CONTROL_PLANE_SUPPORTED' if all_pass else 'B27DV_SHADOW_CONTROL_PLANE_NOT_READY'
    OUT_STATUS.write_text(status+'\n')

    lines=[
        '# B27DV — B27DQ LONG + F15 SHORT20 Phantom-Free Shadow Control Plane — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        f'Frozen portfolio control: **{len(exp_acc)} accepted = {len(exp_long)} LONG + {len(exp_short)} SHORT20**, net=${float(exp_acc.pnl.sum()):+.2f}.','',
        '## Engineering checks','',
        '| Check | Result | Detail |','|---|---|---|'
    ]
    for r in checks.itertuples(index=False):
        lines.append(f'| {r.check} | {"PASS" if r.pass_ if hasattr(r,"pass_") else ("PASS" if getattr(r,"pass") else "FAIL")} | {str(r.detail).replace("|","/")} |')
    lines += ['',
        '## Readiness interpretation','',
        '- Frozen B27DQ + SHORT20 chronological candidate arbitration is reproduced trade-by-trade by the new durable control plane.',
        '- Completed-bar duplication is idempotent and out-of-order bars fail closed.',
        '- Entry and protective-floor state are acknowledgement-gated and survive restart.',
        '- A transactional one-BTC lock prevents two shadow instances from owning BTC simultaneously.',
        '- Startup exchange reconciliation covers exchange-adopt, stale-local-clear, and side-mismatch halt.',
        '- **Legacy `bbc_live.py` remains unchanged and is not yet switched to this strategy.** This is deliberate: B27DV proves the control plane before production market-data wiring.','',
        f'**Status: {status}**','',
        'Next engineering gate after a PASS: wire raw closed Binance 5m events + frozen LONG/SHORT signal adapters into this control plane in shadow mode, then compare forward signals before enabling any exchange entry writes.'
    ]
    text='\n'.join(lines)+'\n'
    OUT_MD.write_text(text)
    print(text)

if __name__=='__main__':
    main()
