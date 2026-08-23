#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
CR_MAP=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Map.csv'
OUT_MD=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Result.md'
OUT_ALL=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_AllVariants.csv'
OUT_SEL=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_SelectedTrades.csv'
OUT_CAND=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Candidates.csv'
OUT_SUM=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Summary.csv'
OUT_STATUS=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
REUSED=('external','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
TP_MAP={'00-04':.05,'04-08':.15,'08-12':.15,'12-16':.10,'16-20':.10,'20-00':.15}
CANDS=('BASE_H','R50','R75','R100')
RISK_MULT={'BASE_H':None,'R50':.50,'R75':.75,'R100':1.00}
TIE_ORDER={'R50':0,'R75':1,'R100':2}
NOTIONAL=500.0
FEE=.40
EPS=1e-12


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left'))
    return x.iloc[a:b]


def boundary_exit(x5,q,end,label):
    pos=int(x5.index.searchsorted(end,'left'))
    if pos<len(x5) and x5.index[pos]==end:
        return end,float(x5.iloc[pos].open),label+'_OPEN'
    assert len(q)>0
    return q.index[-1]+BAR5,float(q.iloc[-1].close),label+'_FALLBACK_CLOSE'


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','terminal_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d.eligible)
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    outcomes={
      'external':{'REBREAK_LOW':149,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':44},
      'development':{'REBREAK_LOW':237,'HIGH_BREAK':23,'NO_BOUNDARY_BY_BLOCK_END':73},
      'reference_validation':{'REBREAK_LOW':133,'HIGH_BREAK':9,'NO_BOUNDARY_BY_BLOCK_END':52}}
    assert len(q)==729
    for p,n in exp.items():
        z=q[q.partition.eq(p)]; assert len(z)==n
        got=z.terminal_type.value_counts().to_dict()
        for k,v in outcomes[p].items(): assert int(got.get(k,0))==v,(p,k,got.get(k,0),v)
    q=q.sort_values(['obs_start','partition']).reset_index(drop=True)
    q['event_id']=np.arange(len(q),dtype=int)
    return q


def validate_cr_map():
    assert CR_MAP.exists(),CR_MAP
    m=pd.read_csv(CR_MAP)
    assert set(CLOCKS).issubset(set(m.clock_block.astype(str)))
    for cb,t in TP_MAP.items():
        z=m[m.clock_block.astype(str).eq(cb)]
        assert len(z)==1,(cb,len(z))
        got=float(z.iloc[0].selected_target)
        assert abs(got-t)<1e-12,(cb,got,t)


def pnl(entry,exit_px):
    gross=(entry-exit_px)/entry
    return gross,gross*NOTIONAL-FEE


def target_name(t):
    return {0.05:'T5',0.10:'T10',0.15:'T15'}[round(float(t),2)]


def eval_one(x5,r,cand):
    risk_mult=RISK_MULT[cand]
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); ext_end=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=float(r.R4)
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4)
    F05=L+.05*R4; T5=L-.05*R4; T75=L-.075*R4; T10=L-.10*R4
    tf=float(TP_MAP[str(r.clock_block)]); target=L-tf*R4
    q0=fast_slice(x5,start,obs_end); qall=fast_slice(x5,start,ext_end)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)
    base={'event_id':int(r.event_id),'candidate':cand,'partition':str(r.partition),'regime':str(r.regime),
          'clock_block':str(r.clock_block),'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,
          'reclaim_complete_ts':start,'H':H,'L':L,'R4':R4,'F05':F05,
          'target_fraction':tf,'target_name':target_name(tf),'target_px':target,
          'T5':T5,'T7p5':T75,'T10':T10}

    fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q0.itertuples()):
        o=float(b.open); h=float(b.high); c=float(b.close)
        if o>=H:
            cancel='HIGH_INVALIDATED_BEFORE_FILL'; break
        if h>=F05:
            fill_idx=i; fill_ts=q0.index[i]; entry=o if o>=F05 else F05
            if entry>=H:
                fill_idx=None; fill_ts=pd.NaT; entry=np.nan; cancel='HIGH_INVALIDATED_BEFORE_FILL'
            break
        if c<L:
            cancel='REBREAK_BEFORE_FILL'; break
        if c>H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break
    if fill_idx is None:
        return {**base,'filled':False,'cancel_reason':cancel,'fill_ts':pd.NaT,'entry_px':np.nan,
                'reward_px':np.nan,'nominal_risk_px':np.nan,'nominal_rr':np.nan,'stop_px':np.nan,
                'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,
                't5_reached':False,'t75_reached':False,'t10_reached':False,'target_reached':False,
                'extension_used':False,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','exit_kind':'NONE',
                'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}

    reward=entry-target
    assert reward>0
    nominal_risk=reward*risk_mult if risk_mult is not None else np.nan
    stop_px=entry+nominal_risk if risk_mult is not None else np.nan
    nominal_rr=reward/nominal_risk if risk_mult is not None else np.nan
    if risk_mult is not None: assert nominal_rr>=1.0-EPS

    active=np.nan; active_kind='NONE'; pending=np.nan; pending_kind='NONE'
    rebreak=False; rb_complete=pd.NaT; t5=t75=t10=False; target_reached=False
    extension_used=False; reason=None; kind='NONE'; exit_ts=pd.NaT; exit_px=np.nan

    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; fb_c=float(fb.close)
    if fb_c>H:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'
    elif risk_mult is not None and fb_c>stop_px:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='PRE_T5_CLOSE_SL'; kind=cand
    elif fb_c<L:
        rebreak=True; rb_complete=fb_ts+BAR5

    for i in range(fill_idx+1,len(qall)):
        if reason is not None: break
        ts=qall.index[i]; b=qall.iloc[i]
        if ts>=obs_end and not extension_used:
            extension_used=True

        o=float(b.open); hi=float(b.high); lo=float(b.low); c=float(b.close)

        if np.isfinite(pending):
            if (not np.isfinite(active)) or pending<active-EPS:
                active=float(pending); active_kind=str(pending_kind)
            pending=np.nan; pending_kind='NONE'

        # Existing protection wins same-bar ambiguity conservatively.
        if np.isfinite(active):
            if o>=active:
                exit_ts=ts; exit_px=o; reason='PROTECTION_OPEN_EXIT'; kind=active_kind; break
            if hi>=active:
                exit_ts=ts+BAR5; exit_px=active; reason='PROTECTION_STOP'; kind=active_kind; break

        # A final resting TP is intrabar and therefore precedes completed-close invalidation.
        if rebreak and ts>=rb_complete:
            if o<=target:
                exit_ts=ts; exit_px=o; reason='TP_GAP_OPEN'; kind='TP'; target_reached=True; break
            if lo<=target:
                exit_ts=ts+BAR5; exit_px=target; reason='TP_TARGET'; kind='TP'; target_reached=True; break

        # Close invalidation is evaluated before a new non-final milestone earns protection.
        if not np.isfinite(active):
            if c>H:
                exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'; break
            if risk_mult is not None and (not t5) and c>stop_px:
                exit_ts=ts+BAR5; exit_px=c; reason='PRE_T5_CLOSE_SL'; kind=cand; break

        if not rebreak:
            if c<L:
                rebreak=True; rb_complete=ts+BAR5
            continue
        if ts<rb_complete: continue

        # For final T5 there are no post-T5 milestones because target would have exited above.
        milestone=np.nan; mkind='NONE'
        if tf>0.10+EPS and lo<=T10:
            t5=t75=t10=True; milestone=T10; mkind='T10_LOCK'
        elif tf>0.075+EPS and lo<=T75:
            t5=t75=True; milestone=T5; mkind='T5_LOCK'
        elif tf>0.05+EPS and lo<=T5:
            t5=True; milestone=L; mkind='L_LOCK'

        if np.isfinite(milestone):
            cur=active if np.isfinite(active) else math.inf
            pen=pending if np.isfinite(pending) else math.inf
            if milestone<min(cur,pen)-EPS:
                pending=milestone; pending_kind=mkind

    if reason is None:
        qend=fast_slice(x5,start,ext_end)
        exit_ts,exit_px,reason=boundary_exit(x5,qend,ext_end,'TIME_EXTENDED_END')
        kind='TIME_EXTENDED'
        extension_used=True

    gross,net=pnl(entry,float(exit_px))
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'reward_px':reward,'nominal_risk_px':nominal_risk,'nominal_rr':nominal_rr,'stop_px':stop_px,
            'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rb_complete,
            't5_reached':bool(t5),'t75_reached':bool(t75),'t10_reached':bool(t10),'target_reached':bool(target_reached),
            'extension_used':bool(extension_used),'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,'exit_kind':kind,
            'gross_return':gross,'net_pnl_usd':net,
            'hold_minutes':float((pd.Timestamp(exit_ts)-fill_ts)/pd.Timedelta(minutes=1))}


def max_dd(s):
    x=pd.to_numeric(s,errors='coerce').dropna().to_numpy(float)
    if len(x)==0:return np.nan
    cum=np.concatenate([[0.],np.cumsum(x)]); peak=np.maximum.accumulate(cum)
    return float(np.max(peak-cum))


def max_streak(s):
    x=pd.to_numeric(s,errors='coerce').dropna().to_numpy(float); cur=best=0
    for v in x:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)


def metrics(g):
    source_n=int(len(g)); t=g[g.filled].copy().sort_values(['fill_ts','event_id']); n=len(t)
    if n==0:
        return {'source_n':source_n,'trades_n':0,'fill_rate':0.,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'total_net':0.,
                'avg_win':np.nan,'avg_loss':np.nan,'max_dd':np.nan,'max_loss_streak':0,'median_hold_min':np.nan,
                'tp_n':0,'pre_t5_sl_n':0,'high_sl_n':0,'l_lock_n':0,'t5_lock_n':0,'t10_lock_n':0,'time_n':0,
                'target_reach_n':0,'extension_used_n':0,'median_nominal_rr':np.nan}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce'); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    kind=t.exit_kind.astype(str); reason=t.exit_reason.astype(str)
    rr=pd.to_numeric(t.nominal_rr,errors='coerce').dropna()
    return {'source_n':source_n,'trades_n':int(n),'fill_rate':n/source_n if source_n else np.nan,
            'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
            'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
            'max_dd':max_dd(net),'max_loss_streak':max_streak(net),'median_hold_min':float(t.hold_minutes.median()),
            'tp_n':int(kind.eq('TP').sum()),'pre_t5_sl_n':int(reason.eq('PRE_T5_CLOSE_SL').sum()),
            'high_sl_n':int(reason.eq('FULL_SL_HIGH_BREAK').sum()),'l_lock_n':int(kind.eq('L_LOCK').sum()),
            't5_lock_n':int(kind.eq('T5_LOCK').sum()),'t10_lock_n':int(kind.eq('T10_LOCK').sum()),
            'time_n':int(kind.eq('TIME_EXTENDED').sum()),'target_reach_n':int(t.target_reached.sum()),
            'extension_used_n':int(t.extension_used.sum()),'median_nominal_rr':float(rr.median()) if len(rr) else np.nan}


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def money(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfmt(x): return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')


def main():
    validate_cr_map()
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    parts=[]
    for cand in CANDS:
        parts.append(pd.DataFrame([eval_one(x5,r,cand) for r in src.itertuples(index=False)]))
    allv=pd.concat(parts,ignore_index=True); allv.to_csv(OUT_ALL,index=False)

    for cand in CANDS:
        z=allv[allv.candidate.eq(cand)]
        assert len(z)==729
        assert int(z.filled.sum())==652
        assert int(z[z.partition.eq('external')].filled.sum())==183
        assert int(z[z.partition.eq('development')].filled.sum())==297
        assert int(z[z.partition.eq('reference_validation')].filled.sum())==172
        if cand!='BASE_H':
            rr=pd.to_numeric(z.loc[z.filled,'nominal_rr'],errors='coerce')
            assert rr.notna().all() and float(rr.min())>=1.0-EPS

    # Development-only per-clock selection.
    crows=[]; selected={}
    for cb in CLOCKS:
        base_m=metrics(allv[(allv.candidate.eq('BASE_H'))&(allv.partition.eq('development'))&(allv.clock_block.eq(cb))])
        eligible=[]
        for cand in CANDS:
            m=metrics(allv[(allv.candidate.eq(cand))&(allv.partition.eq('development'))&(allv.clock_block.eq(cb))])
            qualifies=False
            if cand!='BASE_H':
                qualifies=bool(m['trades_n']>=30 and m['expectancy']>0 and m['pf']>=1.10 and m['expectancy']>base_m['expectancy']+EPS)
                if qualifies: eligible.append((m['expectancy'],m['pf'],-TIE_ORDER[cand],cand))
            crows.append({'clock_block':cb,'wib':WIB[cb],'candidate':cand,'target_name':target_name(TP_MAP[cb]),
                          **m,'qualifies':qualifies})
        selected[cb]=max(eligible)[-1] if eligible else 'BASE_H'
    canddf=pd.DataFrame(crows)

    # Reused confirmation of frozen map.
    conf=[]
    for cb in CLOCKS:
        cand=selected[cb]; new=cand!='BASE_H'; ok=new
        row={'clock_block':cb,'wib':WIB[cb],'target_name':target_name(TP_MAP[cb]),'selected':cand,'new_sl':new}
        for p in REUSED:
            sm=metrics(allv[(allv.candidate.eq(cand))&(allv.partition.eq(p))&(allv.clock_block.eq(cb))])
            bm=metrics(allv[(allv.candidate.eq('BASE_H'))&(allv.partition.eq(p))&(allv.clock_block.eq(cb))])
            row[p+'_n']=sm['trades_n']; row[p+'_wr']=sm['wr']; row[p+'_pf']=sm['pf']; row[p+'_exp']=sm['expectancy']; row[p+'_base_exp']=bm['expectancy']
            if new:
                ok=ok and sm['trades_n']>=10 and sm['expectancy']>0 and sm['pf']>1.0 and sm['expectancy']>=bm['expectancy']-EPS
        row['reused_confirmed']=bool(ok) if new else False
        conf.append(row)
    confdf=pd.DataFrame(conf)

    # Construct selected map, one candidate row per source event.
    pieces=[]
    for cb in CLOCKS:
        pieces.append(allv[(allv.clock_block.eq(cb))&(allv.candidate.eq(selected[cb]))].copy())
    sel=pd.concat(pieces,ignore_index=True); assert len(sel)==729
    sel.to_csv(OUT_SEL,index=False)

    # Summary selected and BASE_H under same clock-TP architecture.
    rows=[]
    for label,d in [('SELECTED',sel),('BASE_H',allv[allv.candidate.eq('BASE_H')])]:
        for p in MAJOR: rows.append({'architecture':label,'scope':'PARTITION','name':p,**metrics(d[d.partition.eq(p)])})
        rows.append({'architecture':label,'scope':'POOL','name':'POOLED_REUSED_EXTVAL',**metrics(d[d.partition.isin(REUSED)])})
        rows.append({'architecture':label,'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)})
        for cb in CLOCKS:
            rows.append({'architecture':label,'scope':'CLOCK_MAJOR','name':cb,**metrics(d[d.clock_block.eq(cb)])})
    sumdf=pd.DataFrame(rows); sumdf.to_csv(OUT_SUM,index=False)
    canddf=canddf.merge(confdf[['clock_block','selected','reused_confirmed']],on='clock_block',how='left')
    canddf['is_selected']=canddf.candidate.eq(canddf.selected)
    canddf.to_csv(OUT_CAND,index=False)

    def sm(label,name):
        q=sumdf[(sumdf.architecture.eq(label))&(sumdf.name.eq(name))]
        assert len(q)==1; return q.iloc[0]

    dev=sm('SELECTED','development'); ext=sm('SELECTED','external'); val=sm('SELECTED','reference_validation'); maj=sm('SELECTED','POOLED_MAJOR')
    new_n=sum(1 for x in selected.values() if x!='BASE_H')
    conf_n=int(confdf.reused_confirmed.sum())
    candidate=bool(new_n>=3 and conf_n>=math.ceil(new_n/2) and
                   float(dev.expectancy)>0 and float(dev.pf)>=1.10 and
                   float(ext.expectancy)>0 and float(ext.pf)>1.00 and
                   float(val.expectancy)>0 and float(val.pf)>1.00 and
                   float(maj.expectancy)>0 and float(maj.pf)>=1.10)
    verdict='B27CS_CLOCK_TP_SL_REUSED_CANDIDATE' if candidate else 'B27CS_CLOCK_TP_SL_NOT_SUPPORTED'
    high70=bool(float(ext.wr)>=.70 and float(dev.wr)>=.70 and float(val.wr)>=.70)
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\nrows={len(allv)}\nfills_external=183\nfills_development=297\nfills_validation=172\nfills_major=652\nclock_tp_map_b27cr_reproduced=TRUE\nmin_nominal_rr={float(pd.to_numeric(allv.loc[(allv.filled)&(~allv.candidate.eq("BASE_H")),"nominal_rr"],errors="coerce").min())}\nuntouched_holdout=NONE\n')

    lines=['# B27CS — BTC 24H Clock-TP Reward-Scaled SL Economics — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact executable F05 fills: external 183 / development 297 / validation 172 / pooled major 652. B27CR clock-TP map reproduced exactly.','',
           'Economics: $500 notional, $0.40 round-trip fee. Entry F05 is frozen. TP map: 07-11 T5; 11-15 T15; 15-19 T15; 19-23 T10; 23-03 T10; 03-07 T15.','',
           'Pre-T5 close-SL candidates: R50 (2:1), R75 (1.33:1), R100 (1:1), plus BASE_H. Candidate stop disables after valid T5; milestone protection then takes over.','',
           '## Six clocks — development selection first','',
           '| UTC / WIB | TP | Candidate | N | WR | PF | Exp/trade | Net | TP | Pre-T5 SL | High SL | Selected |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for cb in CLOCKS:
        for cand in CANDS:
            r=canddf[(canddf.clock_block.eq(cb))&(canddf.candidate.eq(cand))].iloc[0]
            lines.append(f'| {cb} / {WIB[cb]} | {target_name(TP_MAP[cb])} | {cand} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.tp_n)} | {int(r.pre_t5_sl_n)} | {int(r.high_sl_n)} | {"**YES**" if bool(r.is_selected) else ""} |')

    lines += ['', '## Frozen clock SL map + reused confirmation','',
              '| UTC / WIB | TP | Selected SL | External N / WR / PF / Exp | Validation N / WR / PF / Exp | Reused confirmed |',
              '|---|---|---|---|---|---|']
    for rr in confdf.itertuples(index=False):
        lines.append(f'| {rr.clock_block} / {rr.wib} | {rr.target_name} | **{rr.selected}** | {rr.external_n} / {pct(rr.external_wr)} / {pfmt(rr.external_pf)} / {money(rr.external_exp)} | {rr.reference_validation_n} / {pct(rr.reference_validation_wr)} / {pfmt(rr.reference_validation_pf)} / {money(rr.reference_validation_exp)} | {"YES" if rr.reused_confirmed else "NO"} |')

    lines += ['', '## Selected-map economics — all clocks retained','',
              '| Scope | Trades | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | TP | Pre-T5 SL | High SL | L/T5/T10 locks | Time |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name in ('external','development','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        r=sm('SELECTED',name)
        lines.append(f'| {name} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | ${float(r.max_dd):.2f} | {int(r.max_loss_streak)} | {int(r.tp_n)} | {int(r.pre_t5_sl_n)} | {int(r.high_sl_n)} | {int(r.l_lock_n)}/{int(r.t5_lock_n)}/{int(r.t10_lock_n)} | {int(r.time_n)} |')

    lines += ['', '## Direct selected map vs BASE_H under the same clock-TP architecture','',
              '| Scope | WR BASE→selected | PF BASE→selected | Exp BASE→selected | Net BASE→selected |',
              '|---|---|---|---|---|']
    for name in ('external','development','reference_validation','POOLED_MAJOR'):
        b=sm('BASE_H',name); a=sm('SELECTED',name)
        lines.append(f'| {name} | {pct(b.wr)} → **{pct(a.wr)}** | {pfmt(b.pf)} → **{pfmt(a.pf)}** | {money(b.expectancy)} → **{money(a.expectancy)}** | {money(b.total_net)} → **{money(a.total_net)}** |')

    lines += ['',f'New SL selected in **{new_n}/6** clocks; reused-confirmed new SLs **{conf_n}/{new_n if new_n else 0}**.','',
              f'HIGH_QUALITY_70: **{"PASS" if high70 else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'External/reference_validation are reused-data confirmation, not untouched OOS. No live BBC changes.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
