#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
BASE_SUM=ROOT/'BTC_24H_F05_PREMATURE_PROTECTION_B27CN_Summary.csv'
OUT_MD=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_Result.md'
OUT_ALL=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_AllVariants.csv'
OUT_MAP=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_SelectedTrades.csv'
OUT_CAND=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_Candidates.csv'
OUT_SUM=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_Summary.csv'
OUT_STATUS=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_F05_CLOCK_SL_B27CO_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
REUSED=('external','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
CANDS=('BASE_H','S05','S10','S15')
STOP_FRAC={'BASE_H':None,'S05':.05,'S10':.10,'S15':.15}
ORDER={'S05':0,'S10':1,'S15':2}
NOTIONAL=500.0
FEE=.40
EPS=1e-12


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


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


def pnl(entry,exit_px):
    gross=(entry-exit_px)/entry
    return gross,gross*NOTIONAL-FEE


def eval_one(x5,r,cand):
    stop_frac=STOP_FRAC[cand]
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); ext_end=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=float(r.R4)
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4)
    F05=L+.05*R4; T5=L-.05*R4; T75=L-.075*R4; T10=L-.10*R4
    q0=fast_slice(x5,start,obs_end); qall=fast_slice(x5,start,ext_end)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)
    base={'event_id':int(r.event_id),'candidate':cand,'partition':str(r.partition),'regime':str(r.regime),
          'clock_block':str(r.clock_block),'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,
          'reclaim_complete_ts':start,'H':H,'L':L,'R4':R4,'F05':F05,'T5':T5,'T7p5':T75,'T10':T10}

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
        return {**base,'filled':False,'cancel_reason':cancel,'fill_ts':pd.NaT,'entry_px':np.nan,'stop_px':np.nan,
          'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,'t5_reached':False,'t75_reached':False,'t10_reached':False,
          'extension_used':False,'ratchets':0,'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','exit_kind':'NONE',
          'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}

    stop_px=entry+stop_frac*R4 if stop_frac is not None else np.nan
    active=np.nan; active_kind='NONE'; pending=np.nan; pending_kind='NONE'
    rebreak=False; rebreak_complete=pd.NaT; t5=t75=t10=False; ratchets=0
    extension_used=False; reason=None; kind='NONE'; exit_ts=pd.NaT; exit_px=np.nan
    highs=qall.high.astype(float).to_numpy()

    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; fb_c=float(fb.close)
    if fb_c>H:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'
    elif stop_frac is not None and fb_c>stop_px:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='PRE_T5_CLOSE_SL'; kind=cand
    elif fb_c<L:
        rebreak=True; rebreak_complete=fb_ts+BAR5

    for i in range(fill_idx+1,len(qall)):
        if reason is not None:break
        ts=qall.index[i]; b=qall.iloc[i]
        if ts>=obs_end and not extension_used:
            if t10:
                exit_ts=obs_end; exit_px=float(b.open); reason='TIME_ORIGINAL_BLOCK_END_OPEN'; kind='TIME_ORIGINAL'; break
            extension_used=True
        o=float(b.open); hi=float(b.high); lo=float(b.low); c=float(b.close)

        if np.isfinite(pending):
            if (not np.isfinite(active)) or pending<active-EPS:
                active=float(pending); active_kind=str(pending_kind)
            pending=np.nan; pending_kind='NONE'

        if np.isfinite(active):
            if o>=active:
                exit_ts=ts; exit_px=o; reason='CEILING_OPEN_EXIT'; kind=active_kind; break
            if hi>=active:
                exit_ts=ts+BAR5; exit_px=active; reason='CEILING_STOP'; kind=active_kind; break

        # New T5 protection is only earned at this bar close, so close invalidation has priority.
        if not np.isfinite(active):
            if c>H:
                exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'; break
            if stop_frac is not None and (not t5) and c>stop_px:
                exit_ts=ts+BAR5; exit_px=c; reason='PRE_T5_CLOSE_SL'; kind=cand; break

        if not rebreak:
            if c<L:
                rebreak=True; rebreak_complete=ts+BAR5
            continue
        if ts<rebreak_complete:continue

        milestone=np.nan; mkind='NONE'
        if lo<=T10:
            t5=t75=t10=True; milestone=T10; mkind='T10'
        elif lo<=T75:
            t5=t75=True; milestone=T5; mkind='T5'
        elif lo<=T5:
            t5=True; milestone=L; mkind='L'
        if np.isfinite(milestone):
            cur=active if np.isfinite(active) else math.inf
            pen=pending if np.isfinite(pending) else math.inf
            if milestone<min(cur,pen)-EPS:
                pending=milestone; pending_kind=mkind

        if t10 and i>=2 and qall.index[i-2]>=rebreak_complete:
            if highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
                piv=float(highs[i-1]); cur=active if np.isfinite(active) else math.inf; pen=pending if np.isfinite(pending) else math.inf
                if piv<min(cur,pen)-EPS:
                    pending=piv; pending_kind='STRUCTURAL'; ratchets+=1

    if reason is None:
        if extension_used:
            qend=fast_slice(x5,start,ext_end); exit_ts,exit_px,reason=boundary_exit(x5,qend,ext_end,'TIME_EXTENDED_END'); kind='TIME_EXTENDED'
        else:
            qend=fast_slice(x5,start,obs_end); exit_ts,exit_px,reason=boundary_exit(x5,qend,obs_end,'TIME_ORIGINAL_BLOCK_END'); kind='TIME_ORIGINAL'

    gross,net=pnl(entry,float(exit_px))
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,'stop_px':stop_px,
      'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rebreak_complete,'t5_reached':bool(t5),'t75_reached':bool(t75),'t10_reached':bool(t10),
      'extension_used':bool(extension_used),'ratchets':int(ratchets),'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,'exit_kind':kind,
      'gross_return':gross,'net_pnl_usd':net,'hold_minutes':float((pd.Timestamp(exit_ts)-fill_ts)/pd.Timedelta(minutes=1))}


def max_dd(s):
    x=pd.to_numeric(s,errors='coerce').dropna().to_numpy(float)
    if len(x)==0:return np.nan
    cum=np.concatenate([[0.],np.cumsum(x)]); peak=np.maximum.accumulate(cum)
    return float(np.max(peak-cum))


def max_streak(s):
    x=pd.to_numeric(s,errors='coerce').dropna().to_numpy(float); cur=best=0
    for v in x:
        if v<0:cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)


def metrics(g):
    source_n=int(len(g)); t=g[g.filled].copy().sort_values(['fill_ts','event_id']); n=len(t)
    if n==0:
        return {'source_n':source_n,'trades_n':0,'fill_rate':0.,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'total_net':0.,
          'avg_win':np.nan,'avg_loss':np.nan,'max_dd':np.nan,'max_loss_streak':0,'median_hold_min':np.nan,
          'pre_t5_sl_n':0,'high_sl_n':0,'total_sl_n':0,'l_lock_n':0,'t5_lock_n':0,'t10_lock_n':0,'structural_n':0,
          'time_original_n':0,'time_extended_n':0,'extension_used_n':0,'t10_reach_n':0}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce'); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    reason=t.exit_reason.astype(str); kind=t.exit_kind.astype(str)
    pre=int(reason.eq('PRE_T5_CLOSE_SL').sum()); high=int(reason.eq('FULL_SL_HIGH_BREAK').sum())
    return {'source_n':source_n,'trades_n':int(n),'fill_rate':n/source_n if source_n else np.nan,
      'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
      'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
      'max_dd':max_dd(net),'max_loss_streak':max_streak(net),'median_hold_min':float(t.hold_minutes.median()),
      'pre_t5_sl_n':pre,'high_sl_n':high,'total_sl_n':pre+high,
      'l_lock_n':int(kind.eq('L').sum()),'t5_lock_n':int(kind.eq('T5').sum()),'t10_lock_n':int(kind.eq('T10').sum()),
      'structural_n':int(kind.eq('STRUCTURAL').sum()),'time_original_n':int(kind.eq('TIME_ORIGINAL').sum()),
      'time_extended_n':int(kind.eq('TIME_EXTENDED').sum()),'extension_used_n':int(t.extension_used.sum()),
      't10_reach_n':int(t.t10_reached.sum())}


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):return '-' if pd.isna(x) else f'{float(x):.2f}'
def money(x):return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    parts=[]
    for cand in CANDS:
        parts.append(pd.DataFrame([eval_one(x5,r,cand) for r in src.itertuples(index=False)]))
    allv=pd.concat(parts,ignore_index=True)
    allv.to_csv(OUT_ALL,index=False)

    # Exact fill identity must be invariant across candidates.
    for cand in CANDS:
        z=allv[allv.candidate.eq(cand)]
        assert int(z.filled.sum())==652
        assert int(z[z.partition.eq('external')].filled.sum())==183
        assert int(z[z.partition.eq('development')].filled.sum())==297
        assert int(z[z.partition.eq('reference_validation')].filled.sum())==172

    # BASE_H must reproduce B27CN economics on all major partitions.
    bs=pd.read_csv(BASE_SUM)
    basev=allv[allv.candidate.eq('BASE_H')]
    for p in MAJOR:
        m=metrics(basev[basev.partition.eq(p)])
        r=bs[(bs.scope=='PARTITION')&(bs.name==p)].iloc[0]
        assert m['trades_n']==int(r.trades_n)
        for k in ('wr','pf','expectancy','total_net'):
            assert abs(float(m[k])-float(r[k]))<1e-9,(p,k,m[k],r[k])

    # Development-only candidate table and frozen per-clock selection.
    crows=[]; selected={}
    for cb in CLOCKS:
        elig=[]
        for cand in CANDS:
            g=allv[(allv.candidate.eq(cand))&(allv.partition.eq('development'))&(allv.clock_block.eq(cb))]
            m=metrics(g)
            qualifies=(cand!='BASE_H' and m['trades_n']>=30 and m['expectancy']>0 and m['pf']>=1.10)
            crows.append({'clock':cb,'candidate':cand,**m,'qualifies_dev':qualifies})
            if qualifies:elig.append((cand,m))
        if elig:
            elig.sort(key=lambda cm:(-cm[1]['expectancy'],-cm[1]['pf'],ORDER[cm[0]]))
            selected[cb]=elig[0][0]
        else:selected[cb]='BASE_H'

    canddf=pd.DataFrame(crows)
    canddf['selected']=canddf.apply(lambda r:r.candidate==selected[r.clock],axis=1)

    # Reused external/validation readout of frozen selected rule per clock.
    confirms=[]
    for cb in CLOCKS:
        cand=selected[cb]; row={'clock':cb,'selected':cand}
        ok_new=(cand!='BASE_H')
        for p in ('external','reference_validation'):
            m=metrics(allv[(allv.candidate.eq(cand))&(allv.partition.eq(p))&(allv.clock_block.eq(cb))])
            row[p+'_n']=m['trades_n']; row[p+'_wr']=m['wr']; row[p+'_pf']=m['pf']; row[p+'_exp']=m['expectancy']; row[p+'_net']=m['total_net']
            if not (m['trades_n']>=10 and m['expectancy']>0 and m['pf']>1.0):ok_new=False
        row['reused_confirmed']=bool(ok_new)
        confirms.append(row)
    conf=pd.DataFrame(confirms)
    canddf=canddf.merge(conf[['clock','selected','reused_confirmed']],on=['clock','selected'],how='left')
    canddf.to_csv(OUT_CAND,index=False)

    # One row per event using the development-frozen clock map; no clock excluded.
    mapped=pd.concat([allv[(allv.clock_block.eq(cb))&(allv.candidate.eq(selected[cb]))] for cb in CLOCKS],ignore_index=True)
    assert len(mapped)==729 and mapped.event_id.nunique()==729
    mapped.to_csv(OUT_MAP,index=False)

    srows=[]
    for p in MAJOR:srows.append({'scope':'PARTITION','name':p,**metrics(mapped[mapped.partition.eq(p)])})
    srows.append({'scope':'POOL','name':'POOLED_REUSED_EXTVAL',**metrics(mapped[mapped.partition.isin(REUSED)])})
    srows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(mapped)})
    for cb in CLOCKS:
        srows.append({'scope':'CLOCK_DEVELOPMENT','name':cb,**metrics(mapped[(mapped.partition.eq('development'))&(mapped.clock_block.eq(cb))])})
        srows.append({'scope':'CLOCK_REUSED','name':cb,**metrics(mapped[(mapped.partition.isin(REUSED))&(mapped.clock_block.eq(cb))])})
    summ=pd.DataFrame(srows); summ.to_csv(OUT_SUM,index=False)

    def sr(scope,name):
        z=summ[(summ.scope==scope)&(summ.name==name)]; assert len(z)==1; return z.iloc[0]
    dev=sr('PARTITION','development'); ext=sr('PARTITION','external'); val=sr('PARTITION','reference_validation'); maj=sr('POOL','POOLED_MAJOR')
    n_new=sum(v!='BASE_H' for v in selected.values())
    gate=(dev.expectancy>0 and dev.pf>=1.10 and ext.expectancy>0 and ext.pf>1.0 and val.expectancy>0 and val.pf>1.0 and maj.expectancy>0 and maj.pf>=1.10 and n_new>=3)
    verdict='B27CO_CLOCK_SL_REUSED_CANDIDATE' if gate else 'B27CO_CLOCK_SL_NOT_SUPPORTED'
    high70=all(sr('PARTITION',p).wr>=.70 for p in MAJOR)
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major=729\nfills_external=183\nfills_development=297\nfills_validation=172\nfills_major=652\nbase_b27cn_reproduced=TRUE\nuntouched_holdout=NONE\n')

    lines=['# B27CO — BTC 24H F05 Clock-Specific Pre-T5 SL Economics — Result','',
      f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
      '**Audit status: PASS.** BASE_H reproduces B27CN exactly. External/reference_validation are reused-data confirmation, not untouched OOS.','',
      'Entry is frozen at F05. Candidate close-stops before T5: S05=entry+5%R4 (RR>=3:1), S10=+10%R4 (RR>=1.5:1), S15=+15%R4 (RR>=1:1).','',
      '## Six clocks — development selection first','',
      '| UTC / WIB | Candidate | N | WR | PF | Exp | Net | Pre-T5 SL | High SL | T10 reached | Dev gate | Selected |',
      '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for cb in CLOCKS:
        for cand in CANDS:
            r=canddf[(canddf.clock==cb)&(canddf.candidate==cand)].iloc[0]
            lines.append(f'| {cb} / {WIB[cb]} | {cand} | {int(r.trades_n)} | {pct(r.wr)} | {num(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.pre_t5_sl_n)} | {int(r.high_sl_n)} | {int(r.t10_reach_n)} | {"PASS" if bool(r.qualifies_dev) else "-"} | {"**YES**" if bool(r.selected) else ""} |')

    lines += ['', '## Frozen clock map + reused confirmation','',
      '| UTC / WIB | Selected | External N / WR / PF / Exp | Validation N / WR / PF / Exp | Reused-confirmed new SL |',
      '|---|---|---|---|---|']
    for _,r in conf.iterrows():
        lines.append(f'| {r.clock} / {WIB[r.clock]} | **{r.selected}** | {int(r.external_n)} / {pct(r.external_wr)} / {num(r.external_pf)} / {money(r.external_exp)} | {int(r.reference_validation_n)} / {pct(r.reference_validation_wr)} / {num(r.reference_validation_pf)} / {money(r.reference_validation_exp)} | {"YES" if r.reused_confirmed else "NO"} |')

    lines += ['', '## Selected-map economics — all clocks retained','',
      '| Scope | Trades | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | Pre-T5 SL | High SL | T10 reached | Ext used |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_REUSED_EXTVAL'),('POOL','POOLED_MAJOR')]:
        r=sr(scope,name)
        lines.append(f'| {name} | {int(r.trades_n)} | {pct(r.wr)} | {num(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | ${float(r.max_dd):.2f} | {int(r.max_loss_streak)} | {int(r.pre_t5_sl_n)} | {int(r.high_sl_n)} | {int(r.t10_reach_n)} | {int(r.extension_used_n)} |')

    lines += ['', '## Direct selected-map vs B27CN','',
      '| Scope | WR B27CN -> map | PF | Exp | Net |', '|---|---|---|---|---|']
    for p in MAJOR:
        r=sr('PARTITION',p); b=bs[(bs.scope=='PARTITION')&(bs.name==p)].iloc[0]
        lines.append(f'| {p} | {pct(b.wr)} -> **{pct(r.wr)}** | {float(b.pf):.2f} -> **{float(r.pf):.2f}** | {money(b.expectancy)} -> **{money(r.expectancy)}** | {money(b.total_net)} -> **{money(r.total_net)}** |')
    b=bs[(bs.scope=='POOL')&(bs.name=='POOLED_MAJOR')].iloc[0]; r=maj
    lines.append(f'| POOLED_MAJOR | {pct(b.wr)} -> **{pct(r.wr)}** | {float(b.pf):.2f} -> **{float(r.pf):.2f}** | {money(b.expectancy)} -> **{money(r.expectancy)}** | {money(b.total_net)} -> **{money(r.total_net)}** |')

    lines += ['',f'New SL selected in **{n_new}/6** clocks.','',f'HIGH_QUALITY_70: **{"PASS" if high70 else "FAIL"}**.','',f'**Frozen verdict: `{verdict}`.**','',
      'No clock was excluded and no entry was changed. Even a candidate PASS would still require a fresh holdout before any live rule.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
