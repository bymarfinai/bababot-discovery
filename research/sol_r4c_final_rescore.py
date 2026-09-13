#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent.parent

def b(v): return v if isinstance(v,bool) else str(v).strip().lower() in {'true','1','yes'}
def pooled(r):
    net=float(r.net_pnl)
    return (int(r.trades)>=160 and float(r.win_rate)>0.55 and net>0 and float(r.expectancy)>=0.50 and float(r.pf)>=1.20 and float(r.max_dd)<=0.15*net and int(r.max_loss_streak)<=8)
def rank(d): return d.sort_values(['min_year_exp','supportive_anchors','expectancy','win_rate','pf'],ascending=[False]*5,kind='stable')
def reasons(r):
    z=[]
    if not b(r.anchor_gate): z.append('anchor_gate')
    if not b(r.era_gate): z.append('era_gate')
    if int(r.trades)<160:z.append('trades<160')
    if float(r.win_rate)<=0.55:z.append('WR<=55%')
    if float(r.net_pnl)<=0:z.append('net<=0')
    if float(r.expectancy)<0.50:z.append('exp<0.50')
    if float(r.pf)<1.20:z.append('PF<1.20')
    if not(float(r.net_pnl)>0 and float(r.max_dd)<=0.15*float(r.net_pnl)):z.append('DD/net>15%')
    if int(r.max_loss_streak)>8:z.append('LS>8')
    return ';'.join(z) if z else 'PASS'

def main():
    hs=[]; ps=[]
    for h in range(24):
        p=ROOT/f'SOL_R4C_H{h:02d}_ETHSTYLE_LONG_CHARACTER_DevelopmentGrid.csv'
        D=pd.read_csv(p); assert len(D)==3240,(h,len(D))
        D['old']=D.candidate_gate.map(b); D['ag']=D.anchor_gate.map(b); D['eg']=D.era_gate.map(b)
        D['pg2']=D.apply(pooled,axis=1); D['new']=D.ag&D.eg&D.pg2
        D['ratio']=D.apply(lambda r:float(r.max_dd)/float(r.net_pnl) if float(r.net_pnl)>0 else float('inf'),axis=1)
        D['rescued']=D.new&~D.old; D['dropped']=D.old&~D.new
        P=D[D.new].copy()
        if len(P): sel=rank(P).iloc[0]; verdict='PASS'; role='SELECTED_FINAL_PASSER'
        else:
            E=D[D.ag&D.eg].copy(); sel=rank(E if len(E) else D).iloc[0]; verdict='FAIL'; role='BEST_FINAL_NEAR_MISS'
        for _,r in P.iterrows():
            ps.append({'hour_wib':h,'window_wib':f'{h:02d}:00-{(h+1)%24:02d}:00','rescued':bool(r.rescued),'character_rule':r.character_rule,'lookback_min':int(r.lookback_min),'hold_min':int(r.hold_min),'trades':int(r.trades),'win_rate':float(r.win_rate),'net_pnl':float(r.net_pnl),'expectancy':float(r.expectancy),'pf':float(r.pf),'max_dd':float(r.max_dd),'dd_net_ratio':float(r.ratio),'max_loss_streak':int(r.max_loss_streak),'supportive_anchors':int(r.supportive_anchors),'evaluable_anchors':int(r.evaluable_anchors),'min_year_exp':float(r.min_year_exp)})
        hs.append({'hour_wib':h,'window_wib':f'{h:02d}:00-{(h+1)%24:02d}:00','verdict':verdict,'old_passers':int(D.old.sum()),'final_passers':int(D.new.sum()),'rescued_passers':int(D.rescued.sum()),'dropped_old_passers':int(D.dropped.sum()),'role':role,'character_rule':sel.character_rule,'lookback_min':int(sel.lookback_min),'hold_min':int(sel.hold_min),'trades':int(sel.trades),'win_rate':float(sel.win_rate),'net_pnl':float(sel.net_pnl),'expectancy':float(sel.expectancy),'pf':float(sel.pf),'max_dd':float(sel.max_dd),'dd_net_ratio':float(sel.ratio),'max_loss_streak':int(sel.max_loss_streak),'supportive_anchors':int(sel.supportive_anchors),'evaluable_anchors':int(sel.evaluable_anchors),'min_year_exp':float(sel.min_year_exp),'fail_reasons':reasons(sel)})
    H=pd.DataFrame(hs); P=pd.DataFrame(ps)
    H.to_csv(ROOT/'SOL_R4C_FINAL_RESCORE_24H.csv',index=False); P.to_csv(ROOT/'SOL_R4C_FINAL_RESCORE_PASSERS.csv',index=False)
    ph=H.loc[H.verdict=='PASS','hour_wib'].tolist(); total=int(H.final_passers.sum()); resc=int(H.rescued_passers.sum()); drop=int(H.dropped_old_passers.sum())
    L=['# SOL R4c Final Re-score','', 'All 77,760 authoritative Development candidates were re-scored. `anchor_gate` and `era_gate` were preserved exactly. Only pooled WR is strict `>55%` and pooled DD is `max_dd <= 15% of net_pnl`; every other pooled threshold is unchanged.','',f'- PASS hours: **{len(ph)}/24** — {ph}',f'- Final passers: **{total}**',f'- Rescued: **{resc}**',f'- Dropped old passers: **{drop}**','', '| WIB | Verdict | Old | Final | Rescued | Dropped | Selected / near-miss | LB | Hold | N | WR | Net | PF | DD/Net | LS | Anchors | Fail |','|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in H.itertuples(index=False): L.append(f'| {r.window_wib} | {r.verdict} | {r.old_passers} | {r.final_passers} | {r.rescued_passers} | {r.dropped_old_passers} | `{r.character_rule}` | {r.lookback_min} | {r.hold_min} | {r.trades} | {100*r.win_rate:.2f}% | ${r.net_pnl:+,.2f} | {r.pf:.3f} | {100*r.dd_net_ratio:.2f}% | {r.max_loss_streak} | {r.supportive_anchors}/{r.evaluable_anchors} | {r.fail_reasons} |')
    if len(P):
        L+=['','## All final passers','']
        for h in ph:
            L.append(f'### H{h:02d}')
            for r in rank(P[P.hour_wib==h]).itertuples(index=False): L.append(f"- {'RESCUED' if r.rescued else 'RETAINED'} `{r.character_rule}` LB{r.lookback_min} H{r.hold_min}: N {r.trades}, WR {100*r.win_rate:.2f}%, net ${r.net_pnl:+,.2f}, exp ${r.expectancy:+.2f}, PF {r.pf:.3f}, DD/net {100*r.dd_net_ratio:.2f}%, LS {r.max_loss_streak}, anchors {r.supportive_anchors}/{r.evaluable_anchors}, min-era exp ${r.min_year_exp:+.2f}")
    (ROOT/'SOL_R4C_FINAL_RESCORE_SUMMARY.md').write_text('\n'.join(L),encoding='utf-8')
    status=f'SOL_R4C_FINAL_RESCORE_{len(ph)}_PASS_HOURS_{total}_PASSERS_{resc}_RESCUED_{drop}_DROPPED'; (ROOT/'SOL_R4C_FINAL_RESCORE_Status.txt').write_text(status+'\n'); print(status); print(H.to_string(index=False))
if __name__=='__main__': main()
