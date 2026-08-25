#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_f85_long_e20_e10_breathing_runner_b27dn as dn

ROOT = Path(__file__).resolve().parent.parent
SAVED_SUM = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Summary.csv'
OUT_MD = ROOT / 'BTC_F85_LONG_B27DO_LIVE_PARITY_AUDIT_B27DP_Result.md'
OUT_PARITY = ROOT / 'BTC_F85_LONG_B27DO_LIVE_PARITY_AUDIT_B27DP_Parity.csv'
OUT_EVENTS = ROOT / 'BTC_F85_LONG_B27DO_LIVE_PARITY_AUDIT_B27DP_BoundaryEvents.csv'
OUT_STATIC = ROOT / 'BTC_F85_LONG_B27DO_LIVE_PARITY_AUDIT_B27DP_LiveReadiness.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_B27DO_LIVE_PARITY_AUDIT_B27DP_Status.txt'

VARIANT = 'HYBRID_0330_FIXED_OTHERS_E10'
RUNNER_ZONES = ('RAW_0530', 'LONDON', 'RAW_2330')
BAR5 = pd.Timedelta(minutes=5)


def close_enough(a, b, tol=1e-9):
    if pd.isna(b):
        return pd.isna(a)
    if math.isinf(float(b)):
        return math.isinf(float(a)) and ((float(a) > 0) == (float(b) > 0))
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def build_hybrid(stream: pd.DataFrame, breathing: pd.DataFrame) -> pd.DataFrame:
    s = stream.copy().reset_index(drop=True)
    b = breathing.copy().reset_index(drop=True)
    assert len(s) == len(b)
    s['_audit_id'] = np.arange(len(s), dtype=int)
    use_runner = s.zone.isin(RUNNER_ZONES).to_numpy()
    s['management_mode'] = np.where(use_runner, 'E10_BREATHING', 'FIXED_E20')

    exit_ts = []
    exit_px = []
    net = []
    for i, use in enumerate(use_runner):
        if use:
            exit_ts.append(pd.Timestamp(b.at[i, 'exit_ts']))
            exit_px.append(float(b.at[i, 'exit_px']))
            net.append(float(b.at[i, 'net_pnl_usd']))
        else:
            exit_ts.append(pd.Timestamp(s.at[i, 'exit_ts']))
            exit_px.append(float(s.at[i, 'exit_px']))
            net.append(float(s.at[i, 'net_pnl_usd']))
    s['exit_ts'] = pd.to_datetime(pd.Series(exit_ts), utc=True)
    s['exit_px'] = np.asarray(exit_px, dtype=float)
    s['net_pnl_usd'] = np.asarray(net, dtype=float)
    return s


def metrics_with_streak(d: pd.DataFrame):
    a = d[d.accepted].copy()
    m = dn.dl.dg.metrics(a)
    return {
        'candidates': len(d),
        'accepted': len(a),
        'blocked': int((~d.accepted).sum()),
        **m,
        'max_loss_streak': dn.dl.streak_losses(a),
    }


def portfolio_parity(stream, hybrid):
    saved = pd.read_csv(SAVED_SUM)
    rows = []
    locked = {}
    for part in dn.dl.PARTS:
        h = dn.dl.dg.lock(hybrid[hybrid.partition == part].copy(), 'B27DP_HYBRID_PARITY')
        locked[part] = h
        actual = metrics_with_streak(h)
        q = saved[(saved.variant == VARIANT) & (saved.partition == part)]
        assert len(q) == 1
        exp = q.iloc[0]
        checks = {
            'candidates': (actual['candidates'], int(exp.candidates)),
            'accepted': (actual['accepted'], int(exp.accepted)),
            'blocked': (actual['blocked'], int(exp.blocked)),
            'wr': (actual['wr'], float(exp.wr)),
            'pf': (actual['pf'], float(exp.pf)),
            'expectancy': (actual['expectancy'], float(exp.expectancy)),
            'total_net': (actual['total_net'], float(exp.total_net)),
            'max_loss_streak': (actual['max_loss_streak'], int(exp.max_loss_streak)),
        }
        for metric, (a, e) in checks.items():
            ok = int(a) == int(e) if metric in ('candidates','accepted','blocked','max_loss_streak') else close_enough(a, e)
            rows.append({'partition': part, 'check': metric, 'actual': a, 'expected': e, 'pass': bool(ok)})

    major = pd.concat([locked[p] for p in dn.dl.MAJOR], ignore_index=True)
    actual = metrics_with_streak(major)
    exp = saved[(saved.variant == VARIANT) & (saved.partition == 'POOLED_MAJOR')].iloc[0]
    checks = {
        'candidates': (actual['candidates'], int(exp.candidates)),
        'accepted': (actual['accepted'], int(exp.accepted)),
        'blocked': (actual['blocked'], int(exp.blocked)),
        'wr': (actual['wr'], float(exp.wr)),
        'pf': (actual['pf'], float(exp.pf)),
        'expectancy': (actual['expectancy'], float(exp.expectancy)),
        'total_net': (actual['total_net'], float(exp.total_net)),
        'max_loss_streak': (actual['max_loss_streak'], int(exp.max_loss_streak)),
    }
    for metric, (a, e) in checks.items():
        ok = int(a) == int(e) if metric in ('candidates','accepted','blocked','max_loss_streak') else close_enough(a, e)
        rows.append({'partition': 'POOLED_MAJOR', 'check': metric, 'actual': a, 'expected': e, 'pass': bool(ok)})
    return pd.DataFrame(rows), locked


def floor_after_close(close, H, R, current_floor):
    return dn.ratchet_floor_from_close(float(close), float(H), float(R), float(current_floor))


def restart_replay(r, x5, collect_events=True):
    entry_start = pd.Timestamp(r.entry_bar_start)
    exec_end = pd.Timestamp(r.execution_end)
    entry_px = float(r.entry_px)
    H = float(r.H); R = float(r.range); f35 = float(r.F35); e20 = float(r.E20)
    e10 = H + 0.10 * R
    q = dn.dl.fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError(f'empty audit path {r.zone} {entry_start}')

    st = {'armed': False, 'floor': None, 'floor_ext': None, 'floor_raises': 0}
    events = []
    checkpoints = 0
    exit_ts = None; exit_px = None; reason = None

    for ts, bar in q.iterrows():
        op=float(bar.open); hi=float(bar.high); lo=float(bar.low); cl=float(bar.close)
        if not st['armed']:
            if hi >= e20:
                old_floor = None
                st['armed'] = True
                st['floor'] = e10
                st['floor_ext'] = 0.10
                new_floor, new_ext = floor_after_close(cl, H, R, st['floor'])
                if new_floor > st['floor'] + 1e-12:
                    st['floor_raises'] += 1
                    st['floor'] = float(new_floor); st['floor_ext'] = float(new_ext)
                if collect_events:
                    events.append({
                        'event_type':'ARM', 'decision_bar_start':ts, 'effective_bar_start':ts+BAR5,
                        'old_floor':old_floor, 'new_floor':float(st['floor']), 'zone':r.zone,
                        'partition':r.partition, 'entry_bar_start':entry_start, 'execution_end':exec_end,
                    })
                # Restart checkpoint after the completed arm bar.
                st = json.loads(json.dumps(st)); checkpoints += 1
                continue
            if cl < f35:
                exit_ts = ts + BAR5; exit_px = cl; reason = 'CLOSE_INVALIDATION_F35'
                break
            st = json.loads(json.dumps(st)); checkpoints += 1
            continue

        floor = float(st['floor'])
        if op <= floor:
            exit_ts = ts; exit_px = op; reason = 'BREATHING_FLOOR_GAP_OPEN'
            break
        if lo <= floor:
            exit_ts = ts + BAR5; exit_px = floor; reason = 'BREATHING_FLOOR_TOUCH'
            break

        old_floor = floor
        new_floor, new_ext = floor_after_close(cl, H, R, floor)
        if new_floor > floor + 1e-12:
            st['floor_raises'] += 1
            st['floor'] = float(new_floor); st['floor_ext'] = float(new_ext)
            if collect_events:
                events.append({
                    'event_type':'RATCHET', 'decision_bar_start':ts, 'effective_bar_start':ts+BAR5,
                    'old_floor':float(old_floor), 'new_floor':float(new_floor), 'zone':r.zone,
                    'partition':r.partition, 'entry_bar_start':entry_start, 'execution_end':exec_end,
                })
        st = json.loads(json.dumps(st)); checkpoints += 1

    if reason is None:
        pos = int(x5.index.searchsorted(exec_end, side='left'))
        if pos >= len(x5) or x5.index[pos] != exec_end:
            raise AssertionError(f'missing time-exit bar {exec_end}')
        exit_ts = exec_end; exit_px = float(x5.iloc[pos].open)
        reason = 'BREATHING_RUNNER_TIME_EXIT' if st['armed'] else 'TIME_EXIT_EXEC_END'

    net = float(exit_px / entry_px - 1.0) * dn.dl.NOTIONAL - dn.dl.FEE
    return {
        'exit_ts':pd.Timestamp(exit_ts), 'exit_px':float(exit_px), 'reason':reason, 'net':net,
        'armed':bool(st['armed']), 'checkpoints':checkpoints, 'events':events,
    }


def replay_parity(stream, x5):
    rows=[]; events_by_id={}; total_checkpoints=0
    for r in stream.itertuples(index=False):
        if r.zone not in RUNNER_ZONES:
            continue
        direct = dn.runner_exit(r, x5)
        rr = restart_replay(r, x5, collect_events=True)
        total_checkpoints += rr['checkpoints']
        ok_ts = pd.Timestamp(rr['exit_ts']) == pd.Timestamp(direct['runner_exit_ts'])
        ok_px = close_enough(rr['exit_px'], direct['runner_exit_px'])
        ok_reason = rr['reason'] == direct['runner_exit_reason']
        ok_net = close_enough(rr['net'], direct['runner_net_pnl_usd'])
        cid = int(getattr(r, '_audit_id')) if hasattr(r, '_audit_id') else None
        if cid is not None:
            events_by_id[cid] = rr['events']
        rows.append({
            'audit_id':cid, 'partition':r.partition, 'zone':r.zone,
            'entry_bar_start':r.entry_bar_start, 'exit_ts_match':ok_ts,
            'exit_px_match':ok_px, 'exit_reason_match':ok_reason, 'net_match':ok_net,
            'pass':bool(ok_ts and ok_px and ok_reason and ok_net), 'restart_checkpoints':rr['checkpoints'],
        })
    return pd.DataFrame(rows), events_by_id, total_checkpoints


def classify_boundary_events(events_by_id, locked, x5):
    accepted_ids=set()
    for p in dn.dl.MAJOR:
        d=locked[p]
        q=d[d.accepted & d.zone.isin(RUNNER_ZONES)]
        accepted_ids.update(int(x) for x in q['_audit_id'].tolist())

    rows=[]
    for cid in sorted(accepted_ids):
        for ev in events_by_id.get(cid, []):
            eff=pd.Timestamp(ev['effective_bar_start'])
            exec_end=pd.Timestamp(ev['execution_end'])
            # Floor is not evaluated after the execution window; time exit owns that boundary.
            if eff >= exec_end:
                cls='TIME_EXIT_BOUNDARY'
                op=lo=np.nan
                old_protect=False
            else:
                pos=int(x5.index.searchsorted(eff, side='left'))
                if pos >= len(x5) or x5.index[pos] != eff:
                    cls='MISSING_BAR'; op=lo=np.nan; old_protect=False
                else:
                    bar=x5.iloc[pos]; op=float(bar.open); lo=float(bar.low)
                    new=float(ev['new_floor'])
                    old=ev['old_floor']
                    oldf=None if old is None or pd.isna(old) else float(old)
                    old_protect = oldf is not None and op <= oldf
                    if op <= new:
                        if old_protect:
                            cls='BOUNDARY_GAP_OLD_FLOOR_ALREADY_PROTECTS'
                        else:
                            cls='BOUNDARY_GAP_NEW_FLOOR_REQUIRED'
                    elif lo <= new:
                        cls='SAME_BAR_CROSS_LATENCY_AMBIGUOUS'
                    else:
                        cls='NO_IMMEDIATE_CROSS'
            row=dict(ev)
            row.update({'active_open':op,'active_low':lo,'classification':cls,'old_floor_protects_open':old_protect})
            rows.append(row)
    return pd.DataFrame(rows)


def static_live_readiness():
    live=(ROOT/'bbc_live.py').read_text(errors='replace')
    endpoint=(ROOT/'bbc_live_endpoint.py').read_text(errors='replace')
    baret=(ROOT/'baret_live.py').read_text(errors='replace')
    combined=live+'\n'+endpoint

    checks=[]
    def add(cid, name, passed, evidence):
        checks.append({'check_id':cid,'capability':name,'pass':bool(passed),'evidence':evidence})

    integrated = any(tok in combined for tok in ('B27DO','E10_BREATHING','F85_LONG_HYBRID'))
    closed5 = ('"5m": 5' in live or "'5m': 5" in live) and integrated
    durable_fields = all(tok in combined for tok in ('runner_armed','runner_floor','execution_end')) and any(tok in combined.lower() for tok in ('sqlite','redis','durable','d1'))
    restore_b27do = integrated and durable_fields and ('get_open_algo_orders' in combined or 'get_position' in combined)
    distributed_lock = integrated and any(tok in combined.lower() for tok in ('redis','distributed_lock','btc_global_lock','advisory_lock'))
    stop_cap = ('STOP_MARKET' in baret and 'place_algo_order' in baret)
    dynamic_b27do = integrated and ('cancel_algo' in combined or '_cancel_sl_tp' in combined) and ('runner_floor' in combined or 'E10' in combined)

    add('C1','B27DO/F85 4-zone strategy integrated in live',integrated,'Search of bbc_live.py + bbc_live_endpoint.py for B27DO/E10/F85 hybrid tokens.')
    add('C2','Closed 5m B27DO event processing',closed5,'Current BBC timeframe map supports 15m/1h/4h; B27DO-specific 5m path must exist.')
    add('C3','Durable B27DO armed/floor state',durable_fields,'Required runner_armed/floor/execution_end durable state not found in current live path.')
    add('C4','Startup restores B27DO runner/floor state',restore_b27do,'Generic exchange orphan/reconciliation exists, but B27DO runner-floor restoration requires C1+C3.')
    add('C5','Single authoritative BTC lock across instances',distributed_lock,'No B27DO distributed/global BTC lock primitive detected in current live path.')
    add('C6','Exchange-native STOP_MARKET capability',stop_cap,'baret_live.ExchangeClient implements conditional algoOrder STOP_MARKET.')
    add('C7','Dynamic B27DO floor replacement + acknowledgement',dynamic_b27do,'No B27DO dynamic runner-floor order replacement path detected.')
    return pd.DataFrame(checks)


def main():
    x5, coverage=dn.dl.dj.b21.load5()
    stream=dn.dl.load_stream(x5).reset_index(drop=True)
    stream['_audit_id']=np.arange(len(stream),dtype=int)
    breathing=dn.attach_runner(stream, x5)
    hybrid=build_hybrid(stream, breathing)

    parity, locked=portfolio_parity(stream, hybrid)
    replay, events_by_id, checkpoints=replay_parity(stream, x5)
    event_df=classify_boundary_events(events_by_id, locked, x5)
    static=static_live_readiness()

    portfolio_ok=bool(parity['pass'].all())
    replay_ok=bool(replay['pass'].all()) and len(replay)>0
    static_ok=bool(static['pass'].all())
    critical_gap=int((event_df.classification=='BOUNDARY_GAP_NEW_FLOOR_REQUIRED').sum()) if len(event_df) else 0
    ambiguous=int((event_df.classification=='SAME_BAR_CROSS_LATENCY_AMBIGUOUS').sum()) if len(event_df) else 0
    missing=int((event_df.classification=='MISSING_BAR').sum()) if len(event_df) else 0
    strict_execution_ok=(critical_gap==0 and ambiguous==0 and missing==0)
    ready=bool(portfolio_ok and replay_ok and static_ok and strict_execution_ok)
    status='B27DP_LIVE_PARITY_READY' if ready else 'B27DP_LIVE_PARITY_NOT_READY'

    parity_out=pd.concat([
        parity,
        pd.DataFrame([{
            'partition':'RUNNER_STATE_MACHINE','check':'restart_replay_all_runner_candidates',
            'actual':int(replay['pass'].sum()),'expected':len(replay),'pass':replay_ok,
        }])
    ],ignore_index=True)
    parity_out.to_csv(OUT_PARITY,index=False)
    event_df.to_csv(OUT_EVENTS,index=False)
    static.to_csv(OUT_STATIC,index=False)
    OUT_STATUS.write_text(status+'\n')

    counts=event_df.classification.value_counts().to_dict() if len(event_df) else {}
    etypes=event_df.event_type.value_counts().to_dict() if len(event_df) else {}
    runner_accepted=sum(int((locked[p].accepted & locked[p].zone.isin(RUNNER_ZONES)).sum()) for p in dn.dl.MAJOR)
    runner_replay_pass=int(replay['pass'].sum())

    lines=[
        '# B27DP — B27DO Live-Parity Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        'Scope: engineering/live-readiness audit only. **No live BBC code or trading configuration was changed.**','',
        '## 1. Deterministic research/state-machine parity','',
        f'- Saved B27DO portfolio parity: **{"PASS" if portfolio_ok else "FAIL"}** ({int(parity["pass"].sum())}/{len(parity)} metric checks).',
        f'- Runner-zone restart replay parity: **{"PASS" if replay_ok else "FAIL"}** ({runner_replay_pass}/{len(replay)} candidates exact on exit timestamp/price/reason/net).',
        f'- Simulated durable restart checkpoints exercised: **{checkpoints:,}**.',
        f'- Accepted pooled-major trades using runner zones in B27DO: **{runner_accepted}**.','',
        'Interpretation: the B27DO algorithm itself can be represented as a causal persisted state machine if its state is actually stored and restored.','',
        '## 2. Floor-update boundary risk','',
        f'- Floor update events on accepted pooled-major runner trades: **{len(event_df)}** (ARM **{etypes.get("ARM",0)}**, RATCHET **{etypes.get("RATCHET",0)}**).',
        f'- `BOUNDARY_GAP_NEW_FLOOR_REQUIRED`: **{critical_gap}**.',
        f'- `SAME_BAR_CROSS_LATENCY_AMBIGUOUS`: **{ambiguous}**.',
        f'- `BOUNDARY_GAP_OLD_FLOOR_ALREADY_PROTECTS`: **{counts.get("BOUNDARY_GAP_OLD_FLOOR_ALREADY_PROTECTS",0)}**.',
        f'- `NO_IMMEDIATE_CROSS`: **{counts.get("NO_IMMEDIATE_CROSS",0)}**.',
        f'- `TIME_EXIT_BOUNDARY`: **{counts.get("TIME_EXIT_BOUNDARY",0)}**.','',
        'A boundary-gap-new-floor event is a strict parity problem: the new floor is learned only after bar N closes, so a live order cannot already have been working at the exact N+1 open. Same-bar-cross cases remain timing-ambiguous under 5m OHLC because the low may occur before or after order acknowledgement.','',
        '## 3. Current live BBC readiness matrix','',
        '| Check | Capability | Result |', '|---|---|---|',
    ]
    for r in static.itertuples(index=False):
        lines.append(f'| {r.check_id} | {r.capability} | {"PASS" if r.pass else "FAIL"} |')
    lines += ['',
        'Current live source does have generic exchange-position reconciliation/orphan handling and Binance conditional `STOP_MARKET` capability, but those are not the same as persisting/restoring B27DO armed/floor state. The existing BBC loop is still the EMA/MTF engine and polls open positions between candles at 15-second intervals.','',
        '## Frozen decision gate','',
        f'- Portfolio parity: **{"PASS" if portfolio_ok else "FAIL"}**',
        f'- Restart/state parity: **{"PASS" if replay_ok else "FAIL"}**',
        f'- Current-live C1-C7 all pass: **{"PASS" if static_ok else "FAIL"}**',
        f'- Strict boundary execution assumptions resolved: **{"PASS" if strict_execution_ok else "FAIL"}**', '',
        f'**Status: {status}**','',
        'This result does **not** invalidate B27DO research performance. It means the current live system cannot yet be claimed to reproduce B27DO without ghost/execution divergence.','',
        'Live BBC unchanged.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
