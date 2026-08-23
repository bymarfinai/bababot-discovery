#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
REG_SRC=ROOT/'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
CS_SUM=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_Summary.csv'
CR_MAP=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Map.csv'
OUT_MD=ROOT/'BTC_24H_BEAR_REGIME_DYNAMIC_TP_B27CT_Result.md'
OUT_TRADES=ROOT/'BTC_24H_BEAR_REGIME_DYNAMIC_TP_B27CT_Trades.csv'
OUT_SUM=ROOT/'BTC_24H_BEAR_REGIME_DYNAMIC_TP_B27CT_Summary.csv'
OUT_STATUS=ROOT/'BTC_24H_BEAR_REGIME_DYNAMIC_TP_B27CT_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_BEAR_REGIME_DYNAMIC_TP_B27CT_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
TP_MAP={'00-04':.05,'04-08':.15,'08-12':.15,'12-16':.10,'16-20':.10,'20-00':.15}
VARIANTS=('FIXED_CLOCK_TP','DYNAMIC_CLOCK_TP')
ALLOW=('BEAR','SIDEWAYS')
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
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d.eligible)
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    assert len(q)==729
    for p,n in exp.items(): assert len(q[q.partition.eq(p)])==n,(p,len(q[q.partition.eq(p)]),n)
    q=q.sort_values(['obs_start','partition']).reset_index(drop=True)
    q['event_id']=np.arange(len(q),dtype=int)
    return q


def validate_regime_provenance(src):
    r=pd.read_csv(REG_SRC)
    for c in ('obs_start','regime_available_ts'):
        r[c]=pd.to_datetime(r[c],utc=True,errors='coerce')
    r=r[r.partition.isin(MAJOR)].copy()
    keys=r[['partition','obs_start','regime','regime_available_ts','clock_block']].copy()
    assert not keys.duplicated(['partition','obs_start']).any()
    m=src[['event_id','partition','obs_start','regime','clock_block']].merge(
        keys,on=['partition','obs_start'],how='left',suffixes=('_event','_atlas'),validate='many_to_one')
    assert len(m)==len(src) and m.regime_atlas.notna().all()
    assert (m.regime_event.astype(str)==m.regime_atlas.astype(str)).all()
    assert (m.clock_block_event.astype(str)==m.clock_block_atlas.astype(str)).all()
    assert m.regime_available_ts.notna().all()
    assert (m.regime_available_ts<=m.obs_start).all()
    return m


def validate_cr_map():
    m=pd.read_csv(CR_MAP)
    for cb,t in TP_MAP.items():
        z=m[m.clock_block.astype(str).eq(cb)]
        assert len(z)==1,(cb,len(z))
        assert abs(float(z.iloc[0].selected_target)-t)<1e-12,(cb,z.iloc[0].selected_target,t)


def target_name(t):
    return {0.05:'T5',0.10:'T10',0.15:'T15'}[round(float(t),2)]


def pnl(entry,exit_px):
    gross=(entry-exit_px)/entry
    return gross,gross*NOTIONAL-FEE


def eval_one(x5,r,variant):
    assert variant in VARIANTS
    dynamic=variant=='DYNAMIC_CLOCK_TP'
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); ext_end=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=float(r.R4)
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4)
    F05=L+.05*R4; T5=L-.05*R4; T75=L-.075*R4; T10=L-.10*R4
    tf=float(TP_MAP[str(r.clock_block)]); target=L-tf*R4
    q0=fast_slice(x5,start,obs_end); qall=fast_slice(x5,start,ext_end)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)
    base={'event_id':int(r.event_id),'variant':variant,'partition':str(r.partition),'regime':str(r.regime),
          'allowed_regime':bool(str(r.regime) in ALLOW),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4,'F05':F05,'target_fraction':tf,'target_name':target_name(tf),
          'target_px':target,'T5':T5,'T7p5':T75,'T10':T10}

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
                'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,
                't5_reached':False,'t75_reached':False,'t10_reached':False,
                'target_reached':False,'target_reached_ts':pd.NaT,'ratchets':0,'extension_used':False,
                'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','exit_kind':'NONE',
                'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}

    active=np.nan; active_kind='NONE'; pending=np.nan; pending_kind='NONE'
    rebreak=False; rb_complete=pd.NaT; t5=t75=t10=False
    target_reached=False; target_ts=pd.NaT; target_activate=pd.NaT; ratchets=0
    reason=None; kind='NONE'; exit_ts=pd.NaT; exit_px=np.nan; extension_used=False
    highs=qall.high.astype(float).to_numpy()

    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; fb_c=float(fb.close)
    if fb_c>H:
        exit_ts=fb_ts+BAR5; exit_px=fb_c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'
    elif fb_c<L:
        rebreak=True; rb_complete=fb_ts+BAR5

    for i in range(fill_idx+1,len(qall)):
        if reason is not None:break
        ts=qall.index[i]; b=qall.iloc[i]
        if ts>=obs_end and not extension_used: extension_used=True
        o=float(b.open); hi=float(b.high); lo=float(b.low); c=float(b.close)

        # Prior completed bar's earned protection activates now.
        if np.isfinite(pending):
            if (not np.isfinite(active)) or pending<active-EPS:
                active=float(pending); active_kind=str(pending_kind)
            pending=np.nan; pending_kind='NONE'

        # Existing resting protection wins any same-bar ambiguity conservatively.
        if np.isfinite(active):
            if o>=active:
                exit_ts=ts; exit_px=o; reason='PROTECTION_OPEN_EXIT'; kind=active_kind; break
            if hi>=active:
                exit_ts=ts+BAR5; exit_px=active; reason='PROTECTION_STOP'; kind=active_kind; break

        if not rebreak:
            if c>H:
                exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'; break
            if c<L:
                rebreak=True; rb_complete=ts+BAR5
            continue
        if ts<rb_complete:continue

        # FIXED variant exits immediately at valid target. DYNAMIC only marks the target bar.
        target_hit=False; target_hit_ts=pd.NaT
        target_gap=False
        if not target_reached:
            if o<=target:
                target_hit=True; target_hit_ts=ts; target_gap=True
            elif lo<=target:
                target_hit=True; target_hit_ts=ts+BAR5
            if target_hit and not dynamic:
                exit_ts=ts if target_gap else ts+BAR5
                exit_px=o if target_gap else target
                reason='TP_GAP_OPEN' if target_gap else 'TP_TARGET'; kind='TP'; target_reached=True; target_ts=target_hit_ts; break

        # New milestone/final-floor is earned only after this completed bar, so close invalidation comes first.
        if not np.isfinite(active) and c>H:
            exit_ts=ts+BAR5; exit_px=c; reason='FULL_SL_HIGH_BREAK'; kind='HIGH'; break

        milestone=np.nan; mkind='NONE'
        if target_hit and dynamic:
            target_reached=True; target_ts=target_hit_ts; target_activate=ts+BAR5
            if tf>=.15-EPS: t5=t75=t10=True
            elif tf>=.10-EPS: t5=t75=t10=True
            else: t5=True
            milestone=target; mkind='TARGET_FLOOR'
        elif not target_reached:
            if tf>.10+EPS and lo<=T10:
                t5=t75=t10=True; milestone=T10; mkind='T10_LOCK'
            elif tf>.075+EPS and lo<=T75:
                t5=t75=True; milestone=T5; mkind='T5_LOCK'
            elif tf>.05+EPS and lo<=T5:
                t5=True; milestone=L; mkind='L_LOCK'

        if np.isfinite(milestone):
            cur=active if np.isfinite(active) else math.inf
            pen=pending if np.isfinite(pending) else math.inf
            if milestone<min(cur,pen)-EPS:
                pending=float(milestone); pending_kind=mkind

        # Strict causal pivot-high ratchet only from a fully post-target 3-bar window.
        if dynamic and target_reached and pd.notna(target_activate) and i>=2:
            if qall.index[i-2]>=target_activate:
                if highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
                    piv=float(highs[i-1])
                    cur=active if np.isfinite(active) else math.inf
                    pen=pending if np.isfinite(pending) else math.inf
                    if piv<min(cur,pen)-EPS:
                        pending=piv; pending_kind='STRUCTURAL'; ratchets+=1

    if reason is None:
        qend=fast_slice(x5,start,ext_end)
        exit_ts,exit_px,reason=boundary_exit(x5,qend,ext_end,'TIME_EXTENDED_END')
        kind='TIME_EXTENDED'; extension_used=True

    gross,net=pnl(entry,float(exit_px))
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rb_complete,
            't5_reached':bool(t5),'t75_reached':bool(t75),'t10_reached':bool(t10),
            'target_reached':bool(target_reached),'target_reached_ts':target_ts,'ratchets':int(ratchets),
            'extension_used':bool(extension_used),'exit_ts':exit_ts,'exit_px':float(exit_px),
            'exit_reason':reason,'exit_kind':kind,'gross_return':gross,'net_pnl_usd':net,
            'hold_minutes':float((pd.Timestamp(exit_ts)-fill_ts)/pd.Timedelta(minutes=1))}


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
                'target_reach_n':0,'target_floor_n':0,'structural_n':0,'high_sl_n':0,'time_n':0,'ratchet_total':0,
                'l_lock_n':0,'t5_lock_n':0,'t10_lock_n':0}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce'); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    kind=t.exit_kind.astype(str); reason=t.exit_reason.astype(str)
    return {'source_n':source_n,'trades_n':int(n),'fill_rate':n/source_n if source_n else np.nan,
            'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
            'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
            'max_dd':max_dd(net),'max_loss_streak':max_streak(net),'median_hold_min':float(t.hold_minutes.median()),
            'target_reach_n':int(t.target_reached.sum()),'target_floor_n':int(kind.eq('TARGET_FLOOR').sum()),
            'structural_n':int(kind.eq('STRUCTURAL').sum()),'high_sl_n':int(reason.eq('FULL_SL_HIGH_BREAK').sum()),
            'time_n':int(kind.eq('TIME_EXTENDED').sum()),'ratchet_total':int(pd.to_numeric(t.ratchets,errors='coerce').fillna(0).sum()),
            'l_lock_n':int(kind.eq('L_LOCK').sum()),'t5_lock_n':int(kind.eq('T5_LOCK').sum()),'t10_lock_n':int(kind.eq('T10_LOCK').sum())}


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def pfmt(x):return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')
def money(x):return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    validate_cr_map()
    src=load_source(); prov=validate_regime_provenance(src)
    x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12

    allv=pd.concat([pd.DataFrame([eval_one(x5,r,v) for r in src.itertuples(index=False)]) for v in VARIANTS],ignore_index=True)
    allv.to_csv(OUT_TRADES,index=False)

    # Exact B27CS executable fill identity before filtering must reproduce for both variants.
    for v in VARIANTS:
        z=allv[allv.variant.eq(v)]
        assert len(z)==729
        assert int(z.filled.sum())==652
        assert int(z[z.partition.eq('external')].filled.sum())==183
        assert int(z[z.partition.eq('development')].filled.sum())==297
        assert int(z[z.partition.eq('reference_validation')].filled.sum())==172

    # FIXED all-regime must reproduce B27CS BASE_H economics exactly.
    cs=pd.read_csv(CS_SUM)
    fixed_all=allv[allv.variant.eq('FIXED_CLOCK_TP')]
    for p in MAJOR:
        m=metrics(fixed_all[fixed_all.partition.eq(p)])
        q=cs[(cs.architecture.eq('BASE_H'))&(cs.scope.eq('PARTITION'))&(cs.name.eq(p))]
        assert len(q)==1
        r=q.iloc[0]
        assert m['trades_n']==int(r.trades_n)
        for k in ('wr','pf','expectancy','total_net'):
            assert abs(float(m[k])-float(r[k]))<1e-9,(p,k,m[k],r[k])

    filtered=allv[allv.allowed_regime].copy()
    blocked=allv[~allv.allowed_regime].copy()

    rows=[]
    # filtered main summaries
    for v in VARIANTS:
        z=filtered[filtered.variant.eq(v)]
        for p in MAJOR:rows.append({'population':'FILTERED_BEAR_SIDEWAYS','variant':v,'scope':'PARTITION','name':p,**metrics(z[z.partition.eq(p)])})
        rows.append({'population':'FILTERED_BEAR_SIDEWAYS','variant':v,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for cb in CLOCKS:rows.append({'population':'FILTERED_BEAR_SIDEWAYS','variant':v,'scope':'CLOCK_MAJOR','name':cb,**metrics(z[z.clock_block.eq(cb)])})
        for rg in ALLOW:rows.append({'population':'FILTERED_BEAR_SIDEWAYS','variant':v,'scope':'REGIME_MAJOR','name':rg,**metrics(z[z.regime.eq(rg)])})
    # all-regime fixed and blocked-BULL fixed for filter attribution
    rows.append({'population':'ALL_REGIME','variant':'FIXED_CLOCK_TP','scope':'POOL','name':'POOLED_MAJOR',**metrics(fixed_all)})
    rows.append({'population':'BLOCKED_BULL','variant':'FIXED_CLOCK_TP','scope':'POOL','name':'POOLED_MAJOR',**metrics(blocked[blocked.variant.eq('FIXED_CLOCK_TP')])})
    sumdf=pd.DataFrame(rows); sumdf.to_csv(OUT_SUM,index=False)

    def sm(pop,v,scope,name):
        q=sumdf[(sumdf.population.eq(pop))&(sumdf.variant.eq(v))&(sumdf.scope.eq(scope))&(sumdf.name.eq(name))]
        assert len(q)==1,(pop,v,scope,name,len(q));return q.iloc[0]

    dyn_parts={p:sm('FILTERED_BEAR_SIDEWAYS','DYNAMIC_CLOCK_TP','PARTITION',p) for p in MAJOR}
    dyn=sm('FILTERED_BEAR_SIDEWAYS','DYNAMIC_CLOCK_TP','POOL','POOLED_MAJOR')
    fix=sm('FILTERED_BEAR_SIDEWAYS','FIXED_CLOCK_TP','POOL','POOLED_MAJOR')
    alla=sm('ALL_REGIME','FIXED_CLOCK_TP','POOL','POOLED_MAJOR')
    bull=sm('BLOCKED_BULL','FIXED_CLOCK_TP','POOL','POOLED_MAJOR')

    candidate=bool(all(int(dyn_parts[p].trades_n)>=30 and float(dyn_parts[p].expectancy)>0 and float(dyn_parts[p].pf)>1.0 for p in MAJOR)
                   and float(dyn.expectancy)>0 and float(dyn.pf)>=1.20 and float(dyn.total_net)>0
                   and float(dyn.expectancy)>float(fix.expectancy)+EPS and float(dyn.pf)>float(fix.pf)+EPS)
    verdict='B27CT_BEAR_FILTER_DYNAMIC_REUSED_CANDIDATE' if candidate else 'B27CT_BEAR_FILTER_DYNAMIC_NOT_SUPPORTED'
    high70=bool(all(float(dyn_parts[p].wr)>=.70 for p in MAJOR))
    OUT_STATUS.write_text(verdict+'\n')

    allowed_src=src[src.regime.astype(str).isin(ALLOW)]
    filt_fixed=filtered[filtered.variant.eq('FIXED_CLOCK_TP')]
    filt_dyn=filtered[filtered.variant.eq('DYNAMIC_CLOCK_TP')]
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\n'
        f'regime_provenance_rows={len(prov)}\nregime_provenance_causal=TRUE\n'
        f'all_fills_external=183\nall_fills_development=297\nall_fills_validation=172\nall_fills_major=652\n'
        f'allowed_source_major={len(allowed_src)}\nfiltered_fills_fixed={int(filt_fixed.filled.sum())}\nfiltered_fills_dynamic={int(filt_dyn.filled.sum())}\n'
        f'clock_tp_map_b27cr_reproduced=TRUE\nb27cs_fixed_economics_reproduced=TRUE\nuntouched_holdout=NONE\n')

    lines=['# B27CT — BTC 24H BEAR Regime-Filter + Dynamic Clock-TP Economics — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CS all-regime executable fills reproduced: external 183 / development 297 / validation 172 / pooled major 652. Causal 4H regime provenance verified before each obs_start.','',
           'Frozen filter: **ALLOW BEAR + SIDEWAYS; BLOCK BULL**. Entry remains F05. Clock TP map remains B27CR. Dynamic variant turns the final clock target into a next-bar profit ceiling and ratchets it down only with strict causal 3-bar pivot highs.','',
           'Economics: $500 notional and $0.40 round-trip fee. External/reference_validation are reused-data confirmation, not untouched OOS.','',
           '## Six clocks first — filtered DYNAMIC','',
           '| UTC / WIB | TP | N | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | Target reach | Target-floor | Pivot exit | High SL | Time |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=sm('FILTERED_BEAR_SIDEWAYS','DYNAMIC_CLOCK_TP','CLOCK_MAJOR',cb)
        lines.append(f'| {cb} / {WIB[cb]} | {target_name(TP_MAP[cb])} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | ${float(r.max_dd):.2f} | {int(r.max_loss_streak)} | {int(r.target_reach_n)} | {int(r.target_floor_n)} | {int(r.structural_n)} | {int(r.high_sl_n)} | {int(r.time_n)} |')

    lines += ['', '## Major partitions — filtered FIXED vs DYNAMIC','',
              '| Partition | Variant | N | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | Target reach | High SL | Time |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*MAJOR,'POOLED_MAJOR'):
        scope='POOL' if p=='POOLED_MAJOR' else 'PARTITION'
        for v in VARIANTS:
            r=sm('FILTERED_BEAR_SIDEWAYS',v,scope,p)
            lines.append(f'| {p} | {v} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | ${float(r.max_dd):.2f} | {int(r.max_loss_streak)} | {int(r.target_reach_n)} | {int(r.high_sl_n)} | {int(r.time_n)} |')

    lines += ['', '## Filter effect — fixed clock TP','',
              '| Population | N | WR | PF | Exp/trade | Net |',
              '|---|---:|---:|---:|---:|---:|',
              f'| ALL regimes | {int(alla.trades_n)} | {pct(alla.wr)} | {pfmt(alla.pf)} | {money(alla.expectancy)} | {money(alla.total_net)} |',
              f'| BEAR + SIDEWAYS allowed | {int(fix.trades_n)} | {pct(fix.wr)} | {pfmt(fix.pf)} | {money(fix.expectancy)} | {money(fix.total_net)} |',
              f'| BULL blocked cohort only | {int(bull.trades_n)} | {pct(bull.wr)} | {pfmt(bull.pf)} | {money(bull.expectancy)} | {money(bull.total_net)} |']

    lines += ['', '## Dynamic effect on the same filtered cohort','',
              '| Metric | FIXED | DYNAMIC |',
              '|---|---:|---:|',
              f'| Trades | {int(fix.trades_n)} | {int(dyn.trades_n)} |',
              f'| WR | {pct(fix.wr)} | **{pct(dyn.wr)}** |',
              f'| PF | {pfmt(fix.pf)} | **{pfmt(dyn.pf)}** |',
              f'| Expectancy/trade | {money(fix.expectancy)} | **{money(dyn.expectancy)}** |',
              f'| Total net | {money(fix.total_net)} | **{money(dyn.total_net)}** |',
              f'| Avg win | {money(fix.avg_win)} | **{money(dyn.avg_win)}** |',
              f'| Avg loss | {money(fix.avg_loss)} | **{money(dyn.avg_loss)}** |',
              f'| Max DD | ${float(fix.max_dd):.2f} | **${float(dyn.max_dd):.2f}** |']

    lines += ['', '## Filtered regime components — DYNAMIC','',
              '| Regime | N | WR | PF | Exp/trade | Net | Target reach | High SL |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for rg in ALLOW:
        r=sm('FILTERED_BEAR_SIDEWAYS','DYNAMIC_CLOCK_TP','REGIME_MAJOR',rg)
        lines.append(f'| {rg} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.target_reach_n)} | {int(r.high_sl_n)} |')

    n=max(1,int(dyn.trades_n))
    lines += ['', '## Per 100 filtered DYNAMIC trades','',
              f'- Net winners: **{100*float(dyn.wr):.1f}**.',
              f'- Full structural High losses: **{100*int(dyn.high_sl_n)/n:.1f}**.',
              f'- Final clock target reached: **{100*int(dyn.target_reach_n)/n:.1f}**.',
              f'- Target-floor exits: **{100*int(dyn.target_floor_n)/n:.1f}**.',
              f'- Structural pivot exits: **{100*int(dyn.structural_n)/n:.1f}**.',
              f'- Time exits: **{100*int(dyn.time_n)/n:.1f}**.',
              '',f'HIGH_QUALITY_70: **{"PASS" if high70 else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'No post-hoc filter, target, pivot, SL, clock, or horizon changes were made. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
