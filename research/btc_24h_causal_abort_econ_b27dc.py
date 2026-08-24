#!/usr/bin/env python3
from __future__ import annotations

# no-semantic workflow trigger
from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_full_loser_separability_b27cv as cv

ROOT=Path(__file__).resolve().parent.parent
ALLV=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_AllVariants.csv'
OUT_MD=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Result.md'
OUT_TRADES=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Trades.csv'
OUT_CLOCK=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Clock.csv'
OUT_SUM=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Summary.csv'
OUT_ATTR=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Attribution.csv'
OUT_STATUS=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CAUSAL_ABORT_ECON_B27DC_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
T10_SAFE=0.5898635948838399
T15_SAFE=0.6079191233470493
IMPULSE=0.28173076923076923
EPS=1e-12
NOTIONAL=500.0
FEE=.40
CANDS=('BASE_H','R100')
RULES=('NO_ABORT','GLOBAL_PLUS15_SAFE','PERSIST_10_15','REFINED_BULL_IMPULSE')
PARTS=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
CAT=cv.CAT


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def load_candidates():
    d=pd.read_csv(ALLV)
    for c in ('obs_start','obs_end','reclaim_complete_ts','fill_ts','rebreak_complete_ts','exit_ts'):
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    for c in ('filled','target_reached','rebreak_confirmed','extension_used'):
        if c in d.columns:d[c]=as_bool(d[c])
    d=d[d.candidate.isin(CANDS)&d.partition.isin(PARTS)&d.filled].copy()
    for cand in CANDS:
        z=d[d.candidate.eq(cand)]
        exp={'external':183,'development':297,'reference_validation':172}
        assert len(z)==652,(cand,len(z))
        for p,n in exp.items():assert len(z[z.partition.eq(p)])==n,(cand,p,len(z[z.partition.eq(p)]),n)
    a=d[d.candidate.eq('BASE_H')][['event_id','fill_ts','entry_px']].sort_values('event_id').reset_index(drop=True)
    b=d[d.candidate.eq('R100')][['event_id','fill_ts','entry_px']].sort_values('event_id').reset_index(drop=True)
    assert a.event_id.equals(b.event_id)
    assert (a.fill_ts.values==b.fill_ts.values).all()
    assert np.allclose(a.entry_px.astype(float),b.entry_px.astype(float),rtol=0,atol=1e-9)
    rr=pd.to_numeric(d.loc[d.candidate.eq('R100'),'nominal_rr'],errors='coerce')
    assert rr.notna().all() and float(rr.min())>=1.0-EPS and float(rr.max())<=1.0+1e-9
    return d


def frozen_scores(x5):
    trades=cv.load_trades(); h1=cv.build_h1(x5); feats=cv.make_features(trades,x5,h1)
    sc,thr,coef,models=cv.score_all(feats)
    s10=thr[(thr.checkpoint.eq('PLUS10'))&thr['mode'].eq('SAFE')].iloc[0]
    s15=thr[(thr.checkpoint.eq('PLUS15'))&thr['mode'].eq('SAFE')].iloc[0]
    assert abs(float(s10.development_auc)-0.8452298452298452)<1e-12
    assert abs(float(s15.development_auc)-0.8860088365243004)<1e-12
    assert abs(float(s10.threshold)-T10_SAFE)<1e-10
    assert abs(float(s15.threshold)-T15_SAFE)<1e-10
    pieces=[]
    for cp,short in [('PLUS10','p10'),('PLUS15','p15')]:
        q=feats[feats.checkpoint.eq(cp)].copy(); nums=cv.num_cols(cp)
        q[short]=models[cp].predict_proba(q[nums+CAT])[:,1]
        keep=['event_id','partition','clock_block','regime','label','decision_ts',short]
        if cp=='PLUS15': keep+=['max_bull_body_r4']
        pieces.append(q[keep])
    a,b=pieces; keys=['event_id','partition','clock_block','regime','label']
    d=a.merge(b,on=keys,how='inner',validate='one_to_one',suffixes=('_10','_15')); assert len(d)==652
    d['decision_ts']=pd.to_datetime(d['decision_ts_15'],utc=True)
    assert (pd.to_datetime(d.decision_ts_15,utc=True)==pd.to_datetime(d.decision_ts_10,utc=True)+BAR5).all()
    d['f10']=pd.to_numeric(d.p10,errors='coerce').ge(T10_SAFE-EPS); d['f15']=pd.to_numeric(d.p15,errors='coerce').ge(T15_SAFE-EPS)
    imp=pd.to_numeric(d.max_bull_body_r4,errors='coerce')
    d['GLOBAL_PLUS15_SAFE']=d.f15; d['PERSIST_10_15']=d.f10&d.f15
    d['REFINED_BULL_IMPULSE']=(d.f10&d.f15)|((~d.f10)&d.f15&imp.ge(IMPULSE-EPS))
    return d[['event_id','partition','clock_block','regime','label','decision_ts','p10','p15','max_bull_body_r4','GLOBAL_PLUS15_SAFE','PERSIST_10_15','REFINED_BULL_IMPULSE']],float(s10.development_auc),float(s15.development_auc)


def short_net(entry,exit_px): return ((entry-exit_px)/entry)*NOTIONAL-FEE


def apply_rule(x5,cands,scores,rule):
    d=cands.merge(scores,on=['event_id','partition','clock_block','regime'],how='left',validate='many_to_one',suffixes=('','_score'))
    assert d.decision_ts.notna().all()
    raw=pd.Series(False,index=d.index) if rule=='NO_ABORT' else d[rule].astype(bool)
    alive=pd.to_datetime(d.exit_ts,utc=True)>pd.to_datetime(d.decision_ts,utc=True)
    d['abort']=raw&alive
    d['abort_ts']=pd.Series(pd.NaT,index=d.index,dtype='datetime64[ns, UTC]')
    d['abort_px']=np.nan
    for i in d.index[d.abort]:
        t=pd.Timestamp(d.at[i,'decision_ts']); assert t in x5.index,t
        d.at[i,'abort_ts']=t; d.at[i,'abort_px']=float(x5.loc[t,'open'])
    d['adj_exit_ts']=d.exit_ts.copy(); d['adj_exit_px']=pd.to_numeric(d.exit_px,errors='coerce'); d['adj_exit_reason']=d.exit_reason.astype(str)
    idx=d.index[d.abort]
    if len(idx):
        d.loc[idx,'adj_exit_ts']=d.loc[idx,'abort_ts']; d.loc[idx,'adj_exit_px']=d.loc[idx,'abort_px']; d.loc[idx,'adj_exit_reason']='DETECTOR_ABORT_'+rule
    d['adj_net_pnl']=pd.to_numeric(d.net_pnl_usd,errors='coerce')
    if len(idx): d.loc[idx,'adj_net_pnl']=[short_net(float(d.at[i,'entry_px']),float(d.at[i,'abort_px'])) for i in idx]
    d['rule']=rule
    return d


def max_dd(vals):
    x=np.asarray(vals,dtype=float)
    if len(x)==0:return np.nan
    c=np.concatenate([[0.],np.cumsum(x)]); p=np.maximum.accumulate(c)
    return float(np.max(p-c))


def max_loss_streak(vals):
    cur=best=0
    for v in np.asarray(vals,dtype=float):
        if v<0:cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)


def econ(g):
    t=g.sort_values(['fill_ts','event_id']).copy(); n=len(t)
    if n==0:return {'trades_n':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'total_net':0.,'avg_win':np.nan,'avg_loss':np.nan,'max_dd':np.nan,'max_loss_streak':0,'abort_n':0,'abort_rate':0.,'trades_per_week':np.nan}
    net=pd.to_numeric(t.adj_net_pnl,errors='coerce').to_numpy(float); pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    span=(pd.Timestamp(t.fill_ts.max())-pd.Timestamp(t.fill_ts.min()))/pd.Timedelta(days=7); tpw=n/span if span>0 else np.nan
    return {'trades_n':n,'wr':float(np.mean(net>0)),'pf':pf,'expectancy':float(np.mean(net)),'total_net':float(np.sum(net)),'avg_win':float(np.mean(pos)) if len(pos) else np.nan,'avg_loss':float(np.mean(neg)) if len(neg) else np.nan,'max_dd':max_dd(net),'max_loss_streak':max_loss_streak(net),'abort_n':int(t.abort.sum()),'abort_rate':float(t.abort.mean()),'trades_per_week':float(tpw) if pd.notna(tpw) else np.nan}


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def money(x):return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfmt(x):return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')


def main():
    x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12
    cands=load_candidates(); scores,auc10,auc15=frozen_scores(x5)
    allrows=[]
    for cand in CANDS:
        z=cands[cands.candidate.eq(cand)].copy()
        for rule in RULES: allrows.append(apply_rule(x5,z,scores,rule))
    allout=pd.concat(allrows,ignore_index=True); allout.to_csv(OUT_TRADES,index=False)
    b=allout[(allout.candidate.eq('BASE_H'))&(allout.rule.eq('NO_ABORT'))]; bm=econ(b)
    assert bm['trades_n']==652; assert abs(bm['total_net']-(-278.39))<0.03,bm['total_net']
    rows=[]
    scopes=[('external',lambda z:z.partition.eq('external')),('development',lambda z:z.partition.eq('development')),('reference_validation',lambda z:z.partition.eq('reference_validation')),('POOLED_REUSED_EXTVAL',lambda z:z.partition.isin(['external','reference_validation'])),('POOLED_MAJOR',lambda z:pd.Series(True,index=z.index))]
    for cand in CANDS:
        for rule in RULES:
            z=allout[(allout.candidate.eq(cand))&(allout.rule.eq(rule))]
            for name,fn in scopes: rows.append({'candidate':cand,'rule':rule,'scope':name,**econ(z[fn(z)])})
    summ=pd.DataFrame(rows); summ.to_csv(OUT_SUM,index=False)
    crows=[]
    for cb in CLOCKS:
        for cand in CANDS:
            for rule in RULES:
                z=allout[(allout.clock_block.eq(cb))&(allout.candidate.eq(cand))&(allout.rule.eq(rule))]
                crows.append({'clock_block':cb,'wib':WIB[cb],'candidate':cand,'rule':rule,**econ(z)})
    clock=pd.DataFrame(crows); clock.to_csv(OUT_CLOCK,index=False)
    attrs=[]
    for cand in CANDS:
        for rule in RULES[1:]:
            z=allout[(allout.candidate.eq(cand))&(allout.rule.eq(rule))&allout.abort]
            for lab in ('BAD','GOOD','OTHER'): attrs.append({'candidate':cand,'rule':rule,'base_label':lab,'abort_n':int((z.label.astype(str)==lab).sum())})
    attr=pd.DataFrame(attrs); attr.to_csv(OUT_ATTR,index=False)
    OUT_STATUS.write_text('B27DC_CAUSAL_ABORT_ECON_RESEARCH_ONLY_NO_LIVE_PROMOTION\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nbase_h_fills=652\nr100_fills=652\nb27cv_plus10_auc={auc10}\nb27cv_plus15_auc={auc15}\nbase_h_baseline_total_net={bm["total_net"]}\nbase_h_rr_guaranteed=false\nr100_min_nominal_rr=1.0\ninference_scores_all_alive_labels=true\nuntouched_holdout=NONE_B27DA_INSUFFICIENT\n')
    def get(scope,cand,rule):
        q=summ[(summ.scope.eq(scope))&(summ.candidate.eq(cand))&(summ.rule.eq(rule))];assert len(q)==1;return q.iloc[0]
    lines=['# B27DC — BTC 24H F05 SHORT Causal Abort Economics — Result','',f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**. Audit **PASS**.','', '**Critical inference correction:** frozen B27CV models are trained exactly as before, but inference now scores every trade still alive at +10/+15, including eventual OTHER outcomes. Future labels do not gate abort eligibility.','',f'Parent reproduction: +10 AUC **{auc10:.10f}**, +15 AUC **{auc15:.10f}**; BASE_H no-abort total net **{money(bm["total_net"])}**.','', 'BASE_H is diagnostic/non-promotable because nominal RR>=1:1 is not guaranteed. R100 is the RR-compliant 1:1 lane. External/reference_validation are reused; B27DA fresh holdout remains insufficient.','', '## Six clocks independently','', '| WIB | Candidate | Rule | N | WR | PF | Exp/trade | Total net | MaxDD | Loss streak | Aborts |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        for cand in CANDS:
            for rule in RULES:
                r=clock[(clock.clock_block.eq(cb))&(clock.candidate.eq(cand))&(clock.rule.eq(rule))].iloc[0]
                lines.append(f'| {WIB[cb]} | {cand} | {rule} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.abort_n)} |')
    lines += ['', '## Pooled and partition economics','', '| Scope | Candidate | Rule | N | WR | PF | Exp/trade | Total net | Avg win | Avg loss | MaxDD | Loss streak | Abort rate | Trades/wk |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        for cand in CANDS:
            for rule in RULES:
                r=get(scope,cand,rule)
                lines.append(f'| {scope} | {cand} | {rule} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.abort_rate)} | {float(r.trades_per_week):.2f} |')
    lines += ['', '## Abort attribution (post-simulation only)','', '| Candidate | Rule | BAD aborts | GOOD aborts | OTHER aborts |','|---|---|---:|---:|---:|']
    for cand in CANDS:
        for rule in RULES[1:]:
            q=attr[(attr.candidate.eq(cand))&(attr.rule.eq(rule))]; vals={r.base_label:int(r.abort_n) for r in q.itertuples(index=False)}
            lines.append(f'| {cand} | {rule} | {vals.get("BAD",0)} | {vals.get("GOOD",0)} | {vals.get("OTHER",0)} |')
    lines += ['', '**Frozen status: `B27DC_CAUSAL_ABORT_ECON_RESEARCH_ONLY_NO_LIVE_PROMOTION`.**','', 'B27DC reports executable historical economics only. It does not upgrade reused anatomy evidence into untouched OOS evidence and does not change live BBC.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__':main()
