#!/usr/bin/env python3
from __future__ import annotations
import sys, tempfile
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import bbc_f85_f15_shadow as live
import btc_f85_long_f15_short_collision_b27dt as dt

PFX='BTC_F85_LONG_B27DQ_F15_SHORT20_LIVE_PARITY_B27DV'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CHECKS=ROOT/f'{PFX}_Checks.csv'
OUT_PARITY=ROOT/f'{PFX}_Parity.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'

def add(rows,name,ok,detail):
    rows.append({'check':name,'pass':bool(ok),'detail':str(detail)})
    if not ok: raise AssertionError(f'{name}: {detail}')

def frozen():
    x5,cov=dt.dq.dn.dl.dj.b21.load5()
    raw,locked,base=dt.build_long(x5)
    rawL=dt.normalize_long(raw)
    baseL=dt.normalize_long(locked,accepted_source=True)
    shorts=dt.normalize_short(dt.build_shorts(x5))
    s20=shorts[shorts.clock_min_norm==1200].copy()
    merged=pd.concat([rawL,s20],ignore_index=True)
    expected=dt.lock_rows(merged,'B27DV_EXPECTED')
    return x5,cov,baseL,s20,merged,expected,base

def replay(merged,db):
    st=live.SQLiteDurableStore(db); e=live.ShadowControlPlane('PRIMARY',st)
    accepted=[]; restarts=0
    q=merged.copy(); q['entry_ts']=pd.to_datetime(q.entry_ts,utc=True); q['exit_ts_norm']=pd.to_datetime(q.exit_ts_norm,utc=True)
    for ts,g in q.sort_values('entry_ts').groupby('entry_ts',sort=True):
        if e.state.lifecycle==live.STATE_ACTIVE and e.state.expected_exit_ts and pd.Timestamp(e.state.expected_exit_ts)<=pd.Timestamp(ts):
            e.close_position(); e=live.ShadowControlPlane('PRIMARY',st); restarts+=1
        if e.state.lifecycle==live.STATE_ENTRY_PENDING: raise AssertionError('unacked entry survived to next candidate boundary')
        intents=[{'candidate_id':r.candidate_id,'side':r.side,'source':r.source,'clock_min':int(r.clock_min_norm),
                  'entry_ts':r.entry_ts,'exit_ts':r.exit_ts_norm} for r in g.itertuples(index=False)]
        actions=e.on_closed_bar(ts,intents)
        if actions:
            a=actions[0]
            p=live.ShadowControlPlane('PRIMARY',st)
            if p.state.lifecycle!=live.STATE_ENTRY_PENDING: raise AssertionError('pending entry not restored')
            p.ack_entry(a['order_id']); e=live.ShadowControlPlane('PRIMARY',st)
            if e.state.lifecycle!=live.STATE_ACTIVE: raise AssertionError('ACK did not activate')
            accepted.append(a['candidate_id']); restarts+=2
    return accepted,restarts

def safety(rows):
    t=pd.Timestamp('2026-08-26T00:05:00Z')
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'a.sqlite'); e=live.ShadowControlPlane('dup',st)
        it={'candidate_id':'DUP1','side':'LONG','source':'T','clock_min':-1,'entry_ts':t,'exit_ts':t+pd.Timedelta(minutes=30)}
        a=e.on_closed_bar(t,[it]); d=e.on_closed_bar(t,[it])
        add(rows,'duplicate_closed_bar_idempotent',len(a)==1 and len(d)==0,(len(a),len(d)))
        add(rows,'entry_not_active_before_ack',e.state.lifecycle==live.STATE_ENTRY_PENDING,e.state.lifecycle)
        e=live.ShadowControlPlane('dup',st); add(rows,'restart_restores_entry_pending',e.state.lifecycle==live.STATE_ENTRY_PENDING,e.state.lifecycle)
        e.ack_entry(a[0]['order_id']); e=live.ShadowControlPlane('dup',st); add(rows,'restart_restores_active',e.state.lifecycle==live.STATE_ACTIVE,e.state.lifecycle)
        e.request_floor(100.0,'floor1'); e=live.ShadowControlPlane('dup',st)
        add(rows,'floor_pending_not_active',e.state.pending_floor==100 and e.state.active_floor is None,(e.state.pending_floor,e.state.active_floor))
        e.ack_floor('floor1'); e=live.ShadowControlPlane('dup',st)
        add(rows,'floor_ack_activates_durably',e.state.active_floor==100 and e.state.pending_floor is None,e.state.active_floor)
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'o.sqlite'); e=live.ShadowControlPlane('ooo',st); e.on_closed_bar(t,[]); bad=False
        try: e.on_closed_bar(t-pd.Timedelta(minutes=5),[])
        except RuntimeError: bad=True
        e=live.ShadowControlPlane('ooo',st); add(rows,'out_of_order_fails_closed',bad and e.state.lifecycle==live.STATE_HALT,e.state.halt_reason)
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'l.sqlite'); a=live.ShadowControlPlane('A',st); b=live.ShadowControlPlane('B',st)
        ia={'candidate_id':'LA','side':'LONG','source':'A','clock_min':-1,'entry_ts':t,'exit_ts':t+pd.Timedelta(hours=1)}
        ib={'candidate_id':'LB','side':'SHORT','source':'B','clock_min':1200,'entry_ts':t,'exit_ts':t+pd.Timedelta(hours=1)}
        aa=a.on_closed_bar(t,[ia]); bb=b.on_closed_bar(t,[ib])
        add(rows,'authoritative_btc_lock_one_winner',len(aa)==1 and len(bb)==0 and st.lock_row()==('A','LA'),st.lock_row())
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'r.sqlite'); e=live.ShadowControlPlane('adopt',st)
        r=e.reconcile_exchange({'qty':1,'side':'LONG','position_id':'P1','candidate_id':'EX1'})
        add(rows,'reconcile_adopts_exchange_open',r=='ADOPTED_EXCHANGE_POSITION' and e.state.lifecycle==live.STATE_ACTIVE,r)
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'r.sqlite'); e=live.ShadowControlPlane('stale',st)
        it={'candidate_id':'ST1','side':'LONG','source':'T','clock_min':-1,'entry_ts':t,'exit_ts':t+pd.Timedelta(hours=1)}
        a=e.on_closed_bar(t,[it]); e.ack_entry(a[0]['order_id']); r=e.reconcile_exchange(None)
        add(rows,'reconcile_clears_stale_local',r=='CLEARED_STALE_LOCAL' and e.state.lifecycle==live.STATE_IDLE and st.lock_row() is None,r)
    with tempfile.TemporaryDirectory() as td:
        st=live.SQLiteDurableStore(Path(td)/'r.sqlite'); e=live.ShadowControlPlane('mis',st)
        it={'candidate_id':'MM1','side':'LONG','source':'T','clock_min':-1,'entry_ts':t,'exit_ts':t+pd.Timedelta(hours=1)}
        a=e.on_closed_bar(t,[it]); e.ack_entry(a[0]['order_id']); r=e.reconcile_exchange({'qty':-1,'side':'SHORT','position_id':'PX'})
        add(rows,'reconcile_side_mismatch_halts',r=='HALT_SIDE_MISMATCH' and e.state.lifecycle==live.STATE_HALT,r)

def main():
    rows=[]; x5,cov,baseL,s20,merged,expected,base=frozen()
    add(rows,'b27dq_long_n',int(base['accepted'])==227,base['accepted'])
    add(rows,'b27dq_long_wr',abs(float(base['wr'])-.7224669603524229)<1e-9,base['wr'])
    add(rows,'b27dq_long_pf',abs(float(base['pf'])-2.2537382795519254)<.03,base['pf'])
    add(rows,'b27dq_long_net',abs(float(base['total_net'])-289.75971313529084)<.20,base['total_net'])
    ex=expected[expected.partition.isin(dt.MAJOR)]; acc=ex[ex.accepted_portfolio.astype(bool)]
    lng=acc[acc.side=='LONG']; sht=acc[acc.side=='SHORT']
    add(rows,'b27dt_portfolio_n',len(acc)==283,len(acc)); add(rows,'b27dt_long_n',len(lng)==227,len(lng)); add(rows,'b27dt_short20_n',len(sht)==56,len(sht))
    add(rows,'b27dt_combined_net',abs(float(acc.pnl.sum())-367.48603546601095)<.20,acc.pnl.sum())
    mm=merged[merged.partition.isin(dt.MAJOR)].copy()
    with tempfile.TemporaryDirectory() as td: got,restarts=replay(mm,Path(td)/'p.sqlite')
    want=acc.candidate_id.astype(str).tolist()
    add(rows,'candidate_order_trade_by_trade_parity',got==want,f'actual={len(got)} expected={len(want)} restarts={restarts}')
    add(rows,'candidate_id_set_parity',set(got)==set(want),f'{len(set(got))}/{len(set(want))}')
    safety(rows)
    baret=(ROOT/'baret_live.py').read_text(errors='replace')
    add(rows,'exchange_stop_market_capability_present','STOP_MARKET' in baret and 'place_algo_order' in baret,'baret_live conditional STOP_MARKET')
    checks=pd.DataFrame(rows); checks.to_csv(OUT_CHECKS,index=False)
    parity=pd.DataFrame([
        {'metric':'B27DQ_LONG_N','actual':int(base['accepted']),'expected':227,'pass':int(base['accepted'])==227},
        {'metric':'B27DT_PORTFOLIO_N','actual':len(acc),'expected':283,'pass':len(acc)==283},
        {'metric':'B27DT_LONG_N','actual':len(lng),'expected':227,'pass':len(lng)==227},
        {'metric':'B27DT_SHORT20_N','actual':len(sht),'expected':56,'pass':len(sht)==56},
        {'metric':'CONTROL_PLANE_N','actual':len(got),'expected':283,'pass':len(got)==283},])
    parity.to_csv(OUT_PARITY,index=False)
    ok=bool(checks['pass'].all()) and bool(parity['pass'].all()); status='B27DV_SHADOW_CONTROL_PLANE_SUPPORTED' if ok else 'B27DV_SHADOW_CONTROL_PLANE_NOT_READY'; OUT_STATUS.write_text(status+'\n')
    lines=['# B27DV — B27DQ LONG + F15 SHORT20 Phantom-Free Shadow Control Plane — Result','',f'5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**.','',f'Frozen portfolio: **{len(acc)} = {len(lng)} LONG + {len(sht)} SHORT20**, net=${float(acc.pnl.sum()):+.2f}.','','## Engineering checks','', '| Check | Result | Detail |','|---|---|---|']
    for _,r in checks.iterrows(): lines.append(f'| {r["check"]} | {"PASS" if bool(r["pass"]) else "FAIL"} | {str(r["detail"]).replace("|","/")} |')
    lines += ['','## Readiness interpretation','', '- Frozen B27DQ + SHORT20 arbitration is reproduced trade-by-trade.', '- Duplicate completed bars are idempotent; out-of-order bars halt.', '- Entry and floor changes are ACK-gated and durable across restart.', '- Transactional BTC lock prevents two instances owning the slot.', '- Exchange reconciliation passes adopt, stale-local-clear, and mismatch-halt tests.', '- **Legacy `bbc_live.py` is still unchanged.** B27DV is shadow-control-plane readiness, not production market-data wiring or live authorization.','',f'**Status: {status}**','', 'Next gate: raw Binance closed-5m signal adapters -> this control plane in forward shadow, with exchange writes disabled.']
    text='\n'.join(lines)+'\n'; OUT_MD.write_text(text); print(text)

if __name__=='__main__': main()
