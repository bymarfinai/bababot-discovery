#!/usr/bin/env python3
"""F6.8 — Friday15 +10m early-sink recovery-guard forensic/counterfactual.

Research only; live BBC untouched.

F6.7 found +10m is the most informative early hinge:
- first5 red + no trade reclaim yet + alive => 29 actions
- catches 9/10 strict sinks but also 8 eventual winners
- full delta -$7.316, Discovery -$21.444, Validation +$14.128

This milestone does NOT tune numeric thresholds. It freezes a compact set of
natural sign/structure hypotheses available at the +10m open to distinguish
continued sink pressure from recoverable weakness.

Base state at +10m:
- first completed 5m closes below entry
- trade alive at +10m
- second completed 5m high remains below entry

Natural hypotheses (no fitted cutoffs):
H1_CONTINUATION = second bar bearish AND lower high AND lower low
H2_SELLER_PRESSURE = cumulative taker imbalance < 0 AND second close < first close AND second close < EMA7
H3_STRUCTURE_PRESSURE = lower high AND second close < first close AND second close < EMA7
H4_FAILED_BOUNCE = lower high AND second close < first close AND cumulative taker imbalance < 0
H5_FULL_PRESSURE = H2 AND lower high

Action: for base-state trades satisfying a hypothesis, exit at actual +10m open.
All other trades retain frozen parent.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517

OUT=Path(os.getenv('F68_OUT','f68_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N


def metrics(p):
    p=np.asarray(p,dtype=float)
    w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':w,'losses':int(len(p)-w),'wr':float(w/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'exp':float(p.mean()) if len(p) else np.nan,
            'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':int(ls)}


def auc(y,score):
    y=np.asarray(y,dtype=int); s=np.asarray(score,dtype=float)
    m=np.isfinite(s); y=y[m]; s=s[m]
    n1=int(y.sum()); n0=len(y)-n1
    if n1==0 or n0==0: return np.nan
    r=pd.Series(s).rank(method='average').to_numpy()
    return float((r[y==1].sum()-n1*(n1+1)/2)/(n1*n0))


def morph(b):
    o,h,l,c=map(float,[b.open,b.high,b.low,b.close]); rg=h-l
    if rg<=0: return {'body':0.,'uw':0.,'lw':0.,'close_loc':.5}
    return {'body':abs(c-o)/rg,'uw':(h-max(o,c))/rg,'lw':(min(o,c)-l)/rg,'close_loc':(c-l)/rg}


def strict_sink(k,t,tr):
    bars=k[(k.index>=t)&(k.index<tr.exit_t)]
    if bars.empty:return False
    first=bars.iloc[0]; rest=bars.iloc[1:]
    return bool(float(first.close)<tr.entry and (rest.empty or float(rest.high.max())<tr.entry-1e-12))


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        b1=k.loc[t]; b2=k.loc[t+pd.Timedelta(minutes=5)]
        dt=t+pd.Timedelta(minutes=10)
        first5_red=bool(float(b1.close)<tr.entry)
        alive=bool(tr.exit_t>dt)
        no_reclaim=bool(float(b2.high)<tr.entry-1e-12)
        base=bool(first5_red and alive and no_reclaim)

        q=float(b1.quote_volume)+float(b2.quote_volume)
        tb=float(b1.taker_buy_quote)+float(b2.taker_buy_quote)
        taker=(2*tb/q-1.0) if q>0 else np.nan
        m1=morph(b1); m2=morph(b2)
        lower_high=bool(float(b2.high)<float(b1.high))
        lower_low=bool(float(b2.low)<float(b1.low))
        second_bear=bool(float(b2.close)<float(b2.open))
        close_below_first=bool(float(b2.close)<float(b1.close))
        close_below_ema7=bool(float(b2.close)<float(b2.ema7))
        close_below_ema20=bool(float(b2.close)<float(b2.ema20))

        H1=bool(base and second_bear and lower_high and lower_low)
        H2=bool(base and taker<0 and close_below_first and close_below_ema7)
        H3=bool(base and lower_high and close_below_first and close_below_ema7)
        H4=bool(base and lower_high and close_below_first and taker<0)
        H5=bool(H2 and lower_high)

        win=bool(tr.pnl>0); sink=strict_sink(k,t,tr)
        # Features known by +10 open, for forensic separation only.
        f={
          'progress10':float(k.loc[dt,'open'])/tr.entry-1.0,
          'close2_progress':float(b2.close)/tr.entry-1.0,
          'low_sofar':min(float(b1.low),float(b2.low))/tr.entry-1.0,
          'high2_gap':float(b2.high)/tr.entry-1.0,
          'bounce_from_low':float(k.loc[dt,'open'])/min(float(b1.low),float(b2.low))-1.0,
          'taker10':taker,
          'ema7_dist2':float(b2.close)/float(b2.ema7)-1.0,
          'ema20_dist2':float(b2.close)/float(b2.ema20)-1.0,
          'ema_spread2':float(b2.ema7)/float(b2.ema20)-1.0,
          'bar2_ret':float(b2.close)/float(b2.open)-1.0,
          'bar2_close_vs_bar1':float(b2.close)/float(b1.close)-1.0,
          'bar2_body':m2['body'],'bar2_upper_wick':m2['uw'],'bar2_lower_wick':m2['lw'],'bar2_close_loc':m2['close_loc'],
        }
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,'entry':tr.entry,
             'parent_pnl':float(tr.pnl),'parent_win':win,'parent_reason':tr.reason,'strict_sink':sink,'base10':base,
             'lower_high':lower_high,'lower_low':lower_low,'second_bear':second_bear,'close_below_first':close_below_first,
             'close_below_ema7':close_below_ema7,'close_below_ema20':close_below_ema20,
             'H1_CONTINUATION':H1,'H2_SELLER_PRESSURE':H2,'H3_STRUCTURE_PRESSURE':H3,'H4_FAILED_BOUNCE':H4,'H5_FULL_PRESSURE':H5,
             **f}
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f68_rows.csv',index=False)
    if int(df.strict_sink.sum())!=10: raise RuntimeError('strict sink parity failed')
    if int(df.base10.sum())!=29: raise RuntimeError(f'F6.7 +10 base parity failed {int(df.base10.sum())}')

    parent=metrics(df.parent_pnl)
    base=df[df.base10].copy()
    cont=['progress10','close2_progress','low_sofar','high2_gap','bounce_from_low','taker10','ema7_dist2','ema20_dist2','ema_spread2','bar2_ret','bar2_close_vs_bar1','bar2_body','bar2_upper_wick','bar2_lower_wick','bar2_close_loc']
    atlas=[]
    for feat in cont:
        for name,g in [('full',base),('discovery',base[base.i<SPLIT]),('validation',base[base.i>=SPLIT])]:
            atlas.append({'feature':feat,'period':name,'n':int(len(g)),'sink_n':int(g.strict_sink.sum()),
                          'auc_sink_high':auc(g.strict_sink,g[feat]),
                          'sink_median':float(g[g.strict_sink][feat].median()) if g.strict_sink.any() else np.nan,
                          'recover_median':float(g[~g.strict_sink][feat].median()) if (~g.strict_sink).any() else np.nan})
    adf=pd.DataFrame(atlas); adf.to_csv(OUT/'f68_continuous_atlas.csv',index=False)

    hypotheses=['H1_CONTINUATION','H2_SELLER_PRESSURE','H3_STRUCTURE_PRESSURE','H4_FAILED_BOUNCE','H5_FULL_PRESSURE']
    tests=[]
    for h in hypotheses:
        action=df[df[h]].copy()
        managed=df.parent_pnl.copy()
        for idx,r in action.iterrows():
            t=pd.Timestamp(r.date,tz='UTC')+pd.Timedelta(hours=8)
            px=float(k.loc[t+pd.Timedelta(minutes=10),'open'])
            managed.loc[idx]=f517.NOTIONAL*(px/float(r.entry)-1.0)-f517.ROUND_TRIP_FEE
        delta=managed-df.parent_pnl
        dmask=df.i<SPLIT; vmask=~dmask
        m=metrics(managed)
        a_d=action[action.i<SPLIT]; a_v=action[action.i>=SPLIT]
        rec={
          'hypothesis':h,'actions':int(len(action)),'sink_actions':int(action.strict_sink.sum()),
          'non_sink_actions':int((~action.strict_sink).sum()),'parent_winners_cut':int(action.parent_win.sum()),
          'action_parent_wr':float(action.parent_win.mean()) if len(action) else np.nan,
          'full_delta':float(delta.sum()),'discovery_delta':float(delta[dmask].sum()),'validation_delta':float(delta[vmask].sum()),
          'discovery_actions':int(len(a_d)),'validation_actions':int(len(a_v)),
          'discovery_sink_actions':int(a_d.strict_sink.sum()),'validation_sink_actions':int(a_v.strict_sink.sum()),
          'discovery_winners_cut':int(a_d.parent_win.sum()),'validation_winners_cut':int(a_v.parent_win.sum()),
          'dd_improvement':float(parent['dd']-m['dd']),'managed':m,
        }
        rec['robust_pass']=bool(len(action)>=2 and rec['full_delta']>0 and rec['discovery_delta']>=0 and rec['validation_delta']>=0 and rec['dd_improvement']>=-1e-12 and rec['discovery_sink_actions']>=1 and rec['validation_sink_actions']>=1 and rec['parent_winners_cut']==0)
        tests.append(rec)
    tdf=pd.DataFrame(tests); tdf.to_csv(OUT/'f68_hypothesis_tests.csv',index=False)
    passes=[x for x in tests if x['robust_pass']]

    # Stable continuous clues: direction vs sink same in D/V and meaningful full separation.
    stable=[]
    for feat in cont:
        z=adf[adf.feature==feat].set_index('period')
        af=float(z.loc['full','auc_sink_high']); ad=float(z.loc['discovery','auc_sink_high']); av=float(z.loc['validation','auc_sink_high'])
        same=bool(np.isfinite(ad) and np.isfinite(av) and (ad-.5)*(av-.5)>0)
        stable.append({'feature':feat,'auc_full':af,'auc_disc':ad,'auc_val':av,'same_side_dv':same,'screen':bool(same and abs(af-.5)>=.15)})
    sdf=pd.DataFrame(stable).sort_values(['screen','auc_full'],ascending=[False,False]); sdf.to_csv(OUT/'f68_stable_features.csv',index=False)

    out={'base10':{'n':int(len(base)),'strict_sinks':int(base.strict_sink.sum()),'parent_winners':int(base.parent_win.sum())},
         'stable_features':sdf[sdf.screen].to_dict('records'),'hypotheses':tests,'robust_passes':passes}
    (OUT/'f68_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Friday15 F6.8 — +10m Early-Sink Recovery Guard','',
        f"**Status:** COMPLETE — {'ROBUST CANDIDATE FOUND' if passes else 'NO ROBUST ACTION RULE YET'}",'**Research only; live BBC untouched.**','',
        '## Frozen +10m base state',f"- N={len(base)}; strict sinks={int(base.strict_sink.sum())}; eventual parent winners={int(base.parent_win.sum())}",'',
        '## Stable continuous clues']
    if len(sdf[sdf.screen]):
        for x in sdf[sdf.screen].to_dict('records'):
            md.append(f"- `{x['feature']}` AUC sink full/D/V = {x['auc_full']:.3f}/{x['auc_disc']:.3f}/{x['auc_val']:.3f}")
    else: md.append('- none passed the fixed D/V direction screen')
    md += ['','## Natural mechanism counterfactuals']
    for x in tests:
        md += [f"### {x['hypothesis']}",f"- actions {x['actions']}; sinks {x['sink_actions']}; winners cut {x['parent_winners_cut']}",
               f"- delta full/D/V = {x['full_delta']:+.3f} / {x['discovery_delta']:+.3f} / {x['validation_delta']:+.3f}",
               f"- DD improvement {x['dd_improvement']:+.3f}; robust pass {x['robust_pass']}",'']
    md += ['## Guardrail','No numeric threshold was fitted. These five hypotheses were frozen before execution from natural sign/structure states at +10m.']
    (OUT/'F6.8_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
