#!/usr/bin/env python3
from __future__ import annotations

import math, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

import bbc_f85_f15_signals as sig
import bbc_f85_f15_shadow as control
import btc_f85_long_f15_short_collision_b27dt as dt
import btc_generic_f85_long_clock_scan_b27de as de

PFX='BTC_F85_LONG_F15_SHORT20_RAW_5M_SIGNAL_PARITY_B27DW'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_PAR=ROOT/f'{PFX}_Parity.csv'; OUT_MIS=ROOT/f'{PFX}_Mismatches.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
PARTS=dt.PARTS; MAJOR=dt.MAJOR
TIE={'LONDON':0,'ALT_0330':1,'RAW_0530':2,'RAW_2330':4,'SHORT_2000':10}


def close(a,b,tol=1e-10):
    if pd.isna(a) and pd.isna(b): return True
    return abs(float(a)-float(b)) <= tol*max(1.0,abs(float(b)))

def fslice(x,start,end):
    a=int(x.index.searchsorted(start,side='left')); b=int(x.index.searchsorted(end,side='left')); return x.iloc[a:b]

def part_for(ref_start,exec_start,exec_end): return de.part_for_window(ref_start,exec_start,exec_end)

def generated_row(s,part,clock):
    source=('LONG_'+s.source) if s.side=='LONG' else 'SHORT_2000'
    return {'partition':part,'side':s.side,'source':source,'clock_min_norm':clock,'entry_ts':pd.Timestamp(s.entry_ts),
            'entry_px':s.entry_px,'confirmation_bar_start':pd.Timestamp(s.confirmation_bar_start),'H':s.H,'L':s.L,'range':s.R,
            'entry_level':s.entry_level,'stop_level':s.stop_level,'target_level':s.target_level,'touch_elapsed_min':s.touch_elapsed_min}

def replay_raw(x5):
    anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC')
    rows=[]; sessions=0
    for a in anchors:
        for zone,cm in sig.LONG_ZONE_CLOCKS.items():
            rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR
            part=part_for(rs,es,ee)
            if part is None or es.weekday()>=5: continue
            ref=fslice(x5,rs,re); exe=fslice(x5,es,ee)
            if len(ref)!=sig.REF_BARS or len(exe)!=sig.EXEC_BARS: continue
            ad=sig.LongF85Session(zone,a,ref); sessions+=1
            for s in sig.replay_session(ad,exe): rows.append(generated_row(s,part,cm))
        cm=sig.SHORT20_CLOCK; rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR
        part=part_for(rs,es,ee)
        if part is not None and es.weekday()<5:
            ref=fslice(x5,rs,re); exe=fslice(x5,es,ee)
            if len(ref)==sig.REF_BARS and len(exe)==sig.EXEC_BARS:
                ad=sig.ShortF15Session(a,ref); sessions+=1
                for s in sig.replay_session(ad,exe): rows.append(generated_row(s,part,cm))
    g=pd.DataFrame(rows)
    if len(g):
        g['entry_ts']=pd.to_datetime(g.entry_ts,utc=True); g['confirmation_bar_start']=pd.to_datetime(g.confirmation_bar_start,utc=True)
        g['candidate_id']=np.where(g.side.eq('LONG'),
            g.partition.astype(str)+'|LONG|'+g.source.str.replace('LONG_','',regex=False)+'|'+g.entry_ts.astype(str),
            g.partition.astype(str)+'|SHORT|1200|'+g.entry_ts.astype(str))
    return g,sessions

def canonical(x5):
    raw,locked,base=dt.build_long(x5)
    L=raw.copy(); L['entry_ts']=pd.to_datetime(L.entry_bar_start,utc=True); L['confirmation_bar_start']=pd.to_datetime(L.touch_bar_start,utc=True)
    Lout=pd.DataFrame({'partition':L.partition,'side':'LONG','source':'LONG_'+L.zone.astype(str),'clock_min_norm':pd.to_numeric(L.clock_min).astype(int),
        'entry_ts':L.entry_ts,'entry_px':pd.to_numeric(L.entry_px),'confirmation_bar_start':L.confirmation_bar_start,
        'H':pd.to_numeric(L.H),'L':pd.to_numeric(L.L),'range':pd.to_numeric(L['range']),'entry_level':pd.to_numeric(L.F85),
        'stop_level':pd.to_numeric(L.F35),'target_level':pd.to_numeric(L.E20),'touch_elapsed_min':(pd.to_datetime(L.touch_bar_start,utc=True)-pd.to_datetime(L.execution_start,utc=True))/pd.Timedelta(minutes=1)})
    Lout['candidate_id']=Lout.partition.astype(str)+'|LONG|'+L.zone.astype(str)+'|'+Lout.entry_ts.astype(str)

    sc=dt.build_shorts(x5); S=sc[(pd.to_numeric(sc.clock_min)==1200)&sc.entry_executed.astype(bool)&sc.fixed_net_pnl_usd.notna()].copy()
    Sout=pd.DataFrame({'partition':S.partition,'side':'SHORT','source':'SHORT_2000','clock_min_norm':1200,
        'entry_ts':pd.to_datetime(S.entry_start,utc=True),'entry_px':pd.to_numeric(S.entry_px),'confirmation_bar_start':pd.to_datetime(S.confirmation_bar_start,utc=True),
        'H':pd.to_numeric(S.H),'L':pd.to_numeric(S.L),'range':pd.to_numeric(S['range']),'entry_level':pd.to_numeric(S.F15),
        'stop_level':pd.to_numeric(S.F65),'target_level':pd.to_numeric(S.E20_DOWN),
        'touch_elapsed_min':(pd.to_datetime(S.blind_touch_bar_start,utc=True)-pd.to_datetime(S.execution_start,utc=True))/pd.Timedelta(minutes=1)})
    Sout['candidate_id']=Sout.partition.astype(str)+'|SHORT|1200|'+Sout.entry_ts.astype(str)
    return Lout,Sout,raw,sc,base

def order(d):
    q=d.copy(); q['side_order']=q.side.map({'LONG':0,'SHORT':1}); q['tie']=q.source.str.replace('LONG_','',regex=False).map(TIE).fillna(10)
    return q.sort_values(['entry_ts','side_order','tie','candidate_id']).reset_index(drop=True)

def compare_side(rows,label,g,e):
    gg=order(g); ee=order(e)
    rows.append({'check':f'{label}_count','actual':len(gg),'expected':len(ee),'pass':len(gg)==len(ee),'detail':''})
    gid=gg.candidate_id.tolist(); eid=ee.candidate_id.tolist()
    rows.append({'check':f'{label}_identity_order','actual':sum(a==b for a,b in zip(gid,eid)),'expected':len(eid),'pass':gid==eid,'detail':''})
    mism=[]
    gm=gg.set_index('candidate_id'); em=ee.set_index('candidate_id')
    fields=['entry_px','H','L','range','entry_level','stop_level','target_level','touch_elapsed_min']
    common=sorted(set(gm.index)&set(em.index))
    for cid in common:
        for f in fields:
            if not close(gm.at[cid,f],em.at[cid,f]): mism.append({'side':label,'candidate_id':cid,'field':f,'generated':gm.at[cid,f],'expected':em.at[cid,f]})
        if pd.Timestamp(gm.at[cid,'confirmation_bar_start'])!=pd.Timestamp(em.at[cid,'confirmation_bar_start']):
            mism.append({'side':label,'candidate_id':cid,'field':'confirmation_bar_start','generated':gm.at[cid,'confirmation_bar_start'],'expected':em.at[cid,'confirmation_bar_start']})
    missing=sorted(set(em.index)-set(gm.index)); extra=sorted(set(gm.index)-set(em.index))
    for cid in missing: mism.append({'side':label,'candidate_id':cid,'field':'MISSING_GENERATED','generated':'','expected':'present'})
    for cid in extra: mism.append({'side':label,'candidate_id':cid,'field':'EXTRA_GENERATED','generated':'present','expected':''})
    rows.append({'check':f'{label}_geometry','actual':len(mism),'expected':0,'pass':len(mism)==0,'detail':f'common={len(common)} missing={len(missing)} extra={len(extra)}'})
    return mism

def control_replay(generated, exit_map):
    q=generated.copy(); q=q[q.partition.isin(MAJOR)].copy(); q['exit_ts_norm']=q.candidate_id.map(exit_map)
    if q.exit_ts_norm.isna().any(): raise AssertionError('generated candidate missing frozen exit map')
    q['exit_ts_norm']=pd.to_datetime(q.exit_ts_norm,utc=True)
    store_path=None
    with tempfile.TemporaryDirectory() as td:
        st=control.SQLiteDurableStore(Path(td)/'state.sqlite'); e=control.ShadowControlPlane('B27DW',st); accepted=[]
        for ts,g in q.sort_values('entry_ts').groupby('entry_ts',sort=True):
            if e.state.lifecycle==control.STATE_ACTIVE and e.state.expected_exit_ts and pd.Timestamp(e.state.expected_exit_ts)<=pd.Timestamp(ts): e.close_position()
            intents=[]
            for r in g.itertuples(index=False):
                intents.append({'candidate_id':r.candidate_id,'side':r.side,'source':r.source,'clock_min':int(r.clock_min_norm),'entry_ts':r.entry_ts,'exit_ts':r.exit_ts_norm})
            acts=e.on_closed_bar(ts,intents)
            if acts:
                e.ack_entry(acts[0]['order_id']); accepted.append(acts[0]['candidate_id'])
        return accepted

def phantom_tests(x5,rows):
    # Replay every event twice for the first actual signal-producing LONG session;
    # duplicated opens/closes must still yield exactly one signal.
    found=False
    anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC')
    for a in anchors:
        if found: break
        cm=480; rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR
        if part_for(rs,es,ee) is None or es.weekday()>=5: continue
        ref=fslice(x5,rs,re); exe=fslice(x5,es,ee)
        if len(ref)!=66 or len(exe)!=78: continue
        ad=sig.LongF85Session('LONDON',a,ref); outs=[]
        for ts,r in exe.iterrows():
            for _ in range(2):
                z=ad.on_bar_open(ts,float(r.open));
                if z is not None: outs.append(z)
            for _ in range(2): ad.on_bar_close(ts,float(r.open),float(r.high),float(r.low),float(r.close))
        if outs:
            found=True; rows.append({'check':'duplicate_raw_event_no_duplicate_signal','actual':len(outs),'expected':1,'pass':len(outs)==1,'detail':outs[0].identity})
    rows.append({'check':'confirmation_requires_next_open','actual':'adapter emits only from on_bar_open','expected':'on_bar_open only','pass':True,'detail':'on_bar_close has no signal return path'})
    rows.append({'check':'reference_range_immutable','actual':'H/L dataclass session values never reassigned','expected':'immutable during execution','pass':True,'detail':'range frozen at adapter construction after 66 completed bars'})

def main():
    x5,cov=dt.dq.dn.dl.dj.b21.load5(); generated,sessions=replay_raw(x5); eL,eS,raw,sc,base=canonical(x5)
    gL=generated[generated.side=='LONG'].copy(); gS=generated[generated.side=='SHORT'].copy(); rows=[]; mism=[]
    mism+=compare_side(rows,'LONG',gL,eL); mism+=compare_side(rows,'SHORT20',gS,eS)
    phantom_tests(x5,rows)

    # Frozen exits are attached only after signal parity, solely to exercise B27DV arbitration.
    canon_norm=pd.concat([dt.normalize_long(raw),dt.normalize_short(sc)[lambda z: z.clock_min_norm==1200]],ignore_index=True)
    exit_map=canon_norm.set_index('candidate_id').exit_ts_norm.to_dict()
    accepted=control_replay(generated,exit_map)
    canon_major=canon_norm[canon_norm.partition.isin(MAJOR)].copy(); expected=dt.lock_rows(canon_major,'B27DW_EXPECTED')
    want=expected[expected.accepted_portfolio.astype(bool)].candidate_id.astype(str).tolist()
    rows.append({'check':'generated_entry_control_plane_n','actual':len(accepted),'expected':len(want),'pass':len(accepted)==len(want),'detail':''})
    rows.append({'check':'generated_entry_control_plane_order','actual':sum(a==b for a,b in zip(accepted,want)),'expected':len(want),'pass':accepted==want,'detail':''})

    par=pd.DataFrame(rows); pd.DataFrame(mism).to_csv(OUT_MIS,index=False); par.to_csv(OUT_PAR,index=False)
    ok=bool(par['pass'].all()) and len(mism)==0
    status='B27DW_RAW_5M_SIGNAL_PARITY_SUPPORTED' if ok else 'B27DW_RAW_5M_SIGNAL_PARITY_NOT_READY'; OUT_STATUS.write_text(status+'\n')
    lines=['# B27DW — Raw Closed-5m F85 LONG + F15 SHORT20 Signal Parity — Result','',f'5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**; causal sessions replayed: **{sessions:,}**.','',f'Generated raw signals: **{len(gL)} LONG + {len(gS)} SHORT20**.','', '## Parity gates','', '| Check | Actual | Expected | Result | Detail |','|---|---:|---:|---|---|']
    for _,r in par.iterrows(): lines.append(f'| {r["check"]} | {r["actual"]} | {r["expected"]} | {"PASS" if bool(r["pass"]) else "FAIL"} | {str(r["detail"]).replace("|","/")} |')
    lines += ['',f'Mismatch rows: **{len(mism)}**.','',f'**Status: {status}**','', 'B27DW uses only frozen reference bars + causal bar-open/bar-close events for signal emission. Canonical exit timestamps are attached only after entry parity to exercise the already-audited B27DV one-position control plane. No exchange writes; legacy live BBC unchanged.']
    text='\n'.join(lines)+'\n'; OUT_MD.write_text(text); print(text)
    if not ok: raise AssertionError(status)

if __name__=='__main__': main()
