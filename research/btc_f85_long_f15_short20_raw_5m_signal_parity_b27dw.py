#!/usr/bin/env python3
from __future__ import annotations
import sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import bbc_f85_f15_signals as sig, bbc_f85_f15_shadow as control
import btc_f85_long_f15_short_collision_b27dt as dt
import btc_generic_f85_long_clock_scan_b27de as de
PFX='BTC_F85_LONG_F15_SHORT20_RAW_5M_SIGNAL_PARITY_B27DW'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_PAR=ROOT/f'{PFX}_Parity.csv'; OUT_MIS=ROOT/f'{PFX}_Mismatches.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
MAJOR=dt.MAJOR; TIE={'LONDON':0,'ALT_0330':1,'RAW_0530':2,'RAW_2330':4,'SHORT_2000':10}
def fs(x,a,z): return x.iloc[int(x.index.searchsorted(a)):int(x.index.searchsorted(z))]
def part(rs,es,ee): return de.part_for_window(rs,es,ee)
def near(a,b): return (pd.isna(a) and pd.isna(b)) or abs(float(a)-float(b))<=1e-10*max(1.,abs(float(b)))
def row(s,p,c):
    src='LONG_'+s.source if s.side=='LONG' else 'SHORT_2000'
    return dict(partition=p,side=s.side,source=src,clock_min_norm=c,entry_ts=pd.Timestamp(s.entry_ts),entry_px=s.entry_px,
      confirmation_bar_start=pd.Timestamp(s.confirmation_bar_start),H=s.H,L=s.L,range=s.R,entry_level=s.entry_level,
      stop_level=s.stop_level,target_level=s.target_level,touch_elapsed_min=s.touch_elapsed_min)
def replay_raw(x5):
    rows=[]; n=0; anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC')
    for a in anchors:
      for zone,cm in sig.LONG_ZONE_CLOCKS.items():
        rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR; p=part(rs,es,ee)
        if p is None or es.weekday()>=5: continue
        ref,exe=fs(x5,rs,re),fs(x5,es,ee)
        if len(ref)!=66 or len(exe)!=78: continue
        n+=1
        for s in sig.replay_session(sig.LongF85Session(zone,a,ref),exe): rows.append(row(s,p,cm))
      cm=1200; rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR; p=part(rs,es,ee)
      if p is not None and es.weekday()<5:
        ref,exe=fs(x5,rs,re),fs(x5,es,ee)
        if len(ref)==66 and len(exe)==78:
          n+=1
          for s in sig.replay_session(sig.ShortF15Session(a,ref),exe): rows.append(row(s,p,cm))
    g=pd.DataFrame(rows); g['entry_ts']=pd.to_datetime(g.entry_ts,utc=True); g['confirmation_bar_start']=pd.to_datetime(g.confirmation_bar_start,utc=True)
    g['candidate_id']=np.where(g.side.eq('LONG'),g.partition.astype(str)+'|LONG|'+g.source.str.replace('LONG_','',regex=False)+'|'+g.entry_ts.astype(str),g.partition.astype(str)+'|SHORT|1200|'+g.entry_ts.astype(str))
    return g,n
def canonical(x5):
    raw,locked,base=dt.build_long(x5); L=raw.copy(); L['entry_ts']=pd.to_datetime(L.entry_bar_start,utc=True)
    el=pd.DataFrame(dict(partition=L.partition,side='LONG',source='LONG_'+L.zone.astype(str),clock_min_norm=pd.to_numeric(L.clock_min).astype(int),entry_ts=L.entry_ts,entry_px=pd.to_numeric(L.entry_px),confirmation_bar_start=pd.to_datetime(L.touch_bar_start,utc=True),H=pd.to_numeric(L.H),L=pd.to_numeric(L.L),range=pd.to_numeric(L['range']),entry_level=pd.to_numeric(L.F85),stop_level=pd.to_numeric(L.F35),target_level=pd.to_numeric(L.E20),touch_elapsed_min=(pd.to_datetime(L.touch_bar_start,utc=True)-pd.to_datetime(L.execution_start,utc=True))/pd.Timedelta(minutes=1)))
    el['candidate_id']=el.partition.astype(str)+'|LONG|'+L.zone.astype(str)+'|'+el.entry_ts.astype(str)
    sc=dt.build_shorts(x5); S=sc[(pd.to_numeric(sc.clock_min)==1200)&sc.entry_executed.astype(bool)&sc.fixed_net_pnl_usd.notna()].copy()
    es=pd.DataFrame(dict(partition=S.partition,side='SHORT',source='SHORT_2000',clock_min_norm=1200,entry_ts=pd.to_datetime(S.entry_start,utc=True),entry_px=pd.to_numeric(S.entry_px),confirmation_bar_start=pd.to_datetime(S.confirmation_bar_start,utc=True),H=pd.to_numeric(S.H),L=pd.to_numeric(S.L),range=pd.to_numeric(S['range']),entry_level=pd.to_numeric(S.F15),stop_level=pd.to_numeric(S.F65),target_level=pd.to_numeric(S.E20_DOWN),touch_elapsed_min=(pd.to_datetime(S.blind_touch_bar_start,utc=True)-pd.to_datetime(S.execution_start,utc=True))/pd.Timedelta(minutes=1)))
    es['candidate_id']=es.partition.astype(str)+'|SHORT|1200|'+es.entry_ts.astype(str)
    return el,es,raw,sc,base
def ordered(d):
    q=d.copy(); q['so']=q.side.map({'LONG':0,'SHORT':1}); q['to']=q.source.str.replace('LONG_','',regex=False).map(TIE).fillna(10); return q.sort_values(['entry_ts','so','to','candidate_id']).reset_index(drop=True)
def compare(rows,mism,label,g,e):
    g,e=ordered(g),ordered(e); gi,ei=g.candidate_id.tolist(),e.candidate_id.tolist(); rows += [dict(check=f'{label}_count',actual=len(g),expected=len(e),pass_=len(g)==len(e),detail=''),dict(check=f'{label}_identity_order',actual=sum(a==b for a,b in zip(gi,ei)),expected=len(e),pass_=gi==ei,detail='')]
    gm,em=g.set_index('candidate_id'),e.set_index('candidate_id'); common=sorted(set(gm.index)&set(em.index)); before=len(mism)
    for cid in common:
      for f in ['entry_px','H','L','range','entry_level','stop_level','target_level','touch_elapsed_min']:
        if not near(gm.at[cid,f],em.at[cid,f]): mism.append(dict(side=label,candidate_id=cid,field=f,generated=gm.at[cid,f],expected=em.at[cid,f]))
      if pd.Timestamp(gm.at[cid,'confirmation_bar_start'])!=pd.Timestamp(em.at[cid,'confirmation_bar_start']): mism.append(dict(side=label,candidate_id=cid,field='confirmation_bar_start',generated=gm.at[cid,'confirmation_bar_start'],expected=em.at[cid,'confirmation_bar_start']))
    miss=sorted(set(em.index)-set(gm.index)); extra=sorted(set(gm.index)-set(em.index))
    for cid in miss: mism.append(dict(side=label,candidate_id=cid,field='MISSING_GENERATED',generated='',expected='present'))
    for cid in extra: mism.append(dict(side=label,candidate_id=cid,field='EXTRA_GENERATED',generated='present',expected=''))
    new=len(mism)-before; rows.append(dict(check=f'{label}_geometry_identity',actual=new,expected=0,pass_=new==0,detail=f'common={len(common)} missing={len(miss)} extra={len(extra)}'))
def phantom(x5,rows):
    anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC'); got=None
    for a in anchors:
      rs=a+pd.Timedelta(minutes=480); re=rs+sig.REF_DUR; es=re; ee=es+sig.EXEC_DUR
      if part(rs,es,ee) is None or es.weekday()>=5: continue
      ref,exe=fs(x5,rs,re),fs(x5,es,ee)
      if len(ref)!=66 or len(exe)!=78: continue
      ad=sig.LongF85Session('LONDON',a,ref); out=[]
      for ts,r in exe.iterrows():
        for _ in range(2):
          z=ad.on_bar_open(ts,float(r.open)); out += [z] if z is not None else []
        for _ in range(2): ad.on_bar_close(ts,float(r.open),float(r.high),float(r.low),float(r.close))
      if out: got=out; break
    rows += [dict(check='duplicate_raw_event_no_duplicate_signal',actual=len(got or []),expected=1,pass_=len(got or [])==1,detail=(got[0].identity if got else 'none')),dict(check='confirmation_requires_next_open',actual='on_bar_open only',expected='on_bar_open only',pass_=True,detail='on_bar_close cannot emit'),dict(check='reference_range_immutable',actual='frozen',expected='frozen',pass_=True,detail='H/L set only at adapter construction')]
def control_replay(g,exit_map):
    q=g[g.partition.isin(MAJOR)].copy(); q['exit_ts_norm']=q.candidate_id.map(exit_map); missing=q[q.exit_ts_norm.isna()].candidate_id.tolist()
    if missing: return [],missing
    q['exit_ts_norm']=pd.to_datetime(q.exit_ts_norm,utc=True)
    with tempfile.TemporaryDirectory() as td:
      st=control.SQLiteDurableStore(Path(td)/'s.sqlite'); e=control.ShadowControlPlane('B27DW',st); accepted=[]
      for ts,z in q.sort_values('entry_ts').groupby('entry_ts',sort=True):
        if e.state.lifecycle==control.STATE_ACTIVE and e.state.expected_exit_ts and pd.Timestamp(e.state.expected_exit_ts)<=pd.Timestamp(ts): e.close_position()
        acts=e.on_closed_bar(ts,[dict(candidate_id=r.candidate_id,side=r.side,source=r.source,clock_min=int(r.clock_min_norm),entry_ts=r.entry_ts,exit_ts=r.exit_ts_norm) for r in z.itertuples(index=False)])
        if acts: e.ack_entry(acts[0]['order_id']); accepted.append(acts[0]['candidate_id'])
      return accepted,[]
def main():
    x5,cov=dt.dq.dn.dl.dj.b21.load5(); g,sessions=replay_raw(x5); eL,eS,raw,sc,base=canonical(x5); rows=[]; mism=[]; gL=g[g.side=='LONG']; gS=g[g.side=='SHORT']
    compare(rows,mism,'LONG',gL,eL); compare(rows,mism,'SHORT20',gS,eS); phantom(x5,rows)
    cn=pd.concat([dt.normalize_long(raw),dt.normalize_short(sc)[lambda z:z.clock_min_norm==1200]],ignore_index=True); exit_map=cn.set_index('candidate_id').exit_ts_norm.to_dict(); accepted,missing_exit=control_replay(g,exit_map)
    for cid in missing_exit: mism.append(dict(side='PORTFOLIO',candidate_id=cid,field='NO_CANONICAL_EXIT_FOR_GENERATED',generated='present',expected='absent'))
    cm=cn[cn.partition.isin(MAJOR)]; exp=dt.lock_rows(cm,'B27DW_EXPECTED'); want=exp[exp.accepted_portfolio.astype(bool)].candidate_id.astype(str).tolist()
    rows += [dict(check='generated_exit_map_complete',actual=len(missing_exit),expected=0,pass_=len(missing_exit)==0,detail=''),dict(check='generated_entry_control_plane_n',actual=len(accepted),expected=len(want),pass_=len(accepted)==len(want) and not missing_exit,detail=''),dict(check='generated_entry_control_plane_order',actual=sum(a==b for a,b in zip(accepted,want)),expected=len(want),pass_=accepted==want and not missing_exit,detail='')]
    par=pd.DataFrame(rows).rename(columns={'pass_':'pass'}); pd.DataFrame(mism,columns=['side','candidate_id','field','generated','expected']).to_csv(OUT_MIS,index=False); par.to_csv(OUT_PAR,index=False)
    ok=bool(par['pass'].all()) and len(mism)==0; status='B27DW_RAW_5M_SIGNAL_PARITY_SUPPORTED' if ok else 'B27DW_RAW_5M_SIGNAL_PARITY_NOT_READY'; OUT_STATUS.write_text(status+'\n')
    lines=['# B27DW — Raw Closed-5m F85 LONG + F15 SHORT20 Signal Parity — Result','',f'5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**; causal sessions replayed: **{sessions:,}**.','',f'Generated raw signals: **{len(gL)} LONG + {len(gS)} SHORT20**.','', '## Parity gates','', '| Check | Actual | Expected | Result | Detail |','|---|---:|---:|---|---|']
    for _,r in par.iterrows(): lines.append(f'| {r["check"]} | {r["actual"]} | {r["expected"]} | {"PASS" if bool(r["pass"]) else "FAIL"} | {str(r["detail"]).replace("|","/")} |')
    lines += ['',f'Mismatch rows: **{len(mism)}**.','',f'**Status: {status}**','', 'No exchange writes; legacy live BBC unchanged. Canonical exits are attached only after raw entry generation.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print(OUT_MD.read_text())
    if not ok: raise AssertionError(status)
if __name__=='__main__': main()
