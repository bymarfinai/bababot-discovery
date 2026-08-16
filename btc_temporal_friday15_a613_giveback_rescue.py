"""BTC Friday15 A6.13 — executable giveback rescue on full 138 Friday entries.

Baseline layer is A6.12 provisional wrong-way intervention:
- every Friday 15:00 WIB BUY enters, TP2.0/SL0.7/max6h
- at 60m initial failure: MFE<.3, progress<0, taker<0, below EMA20, EMA20 slope<0
- at 120m persistent MFE<.3 and progress<0 -> close BUY and flip SHORT TP1.0/SL0.7 for remaining horizon

A6.13 studies a separate giveback layer only when the A6.12 wrong-way flip did NOT fire.
Crucially, +0.5% hinge must occur while the original BUY is still open. If +0.5 and SL occur
on the same 5m bar, adverse-first policy means the hinge is NOT actionable.

Candidate deterioration signals are selected on first 82 discovery Fridays only.
Validation last 56 is opened only after selection. Research only; live untouched.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_friday15_a611_recovery_confirmation as a611
import btc_temporal_friday15_a612_wrongway_robustness as a612
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0; SL=.7; HOLD=360; FEE=.15; NOTIONAL=500.0
LOCKS=(.20,.25,.30)


def econ(p):
    n=len(p); pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
            'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),
            'ls':a60.loss_streak(p)}


def wrongway_signal(rows,r,e7,e20):
    c60=a69.checkpoint(rows,r,e7,e20,60); c120=a69.checkpoint(rows,r,e7,e20,120)
    if c60 is None or c120 is None:return False
    return a612.initial(c60) and a612.confirmed(c120)


def wrongway_pnl(rows,r):
    if not r['wrongway']:return r['trade']['net_usd']
    rr=dict(r); rr['confirmed']=True
    return a611.action(rows,rr,120,'FLIP',(1.0,.7))


def actionable_hinge(rows,r):
    """First +0.5% high strictly before the original BUY exit bar.
    Same exit bar is excluded to preserve adverse-first ambiguity policy.
    """
    i=r['i']; e=r['entry']; bars=r['trade']['bars']; target=e*1.005
    # exit bar index is i+bars-1. Search only bars strictly before it.
    last=i+max(0,bars-1)
    for j in range(i,last):
        if rows[j][0]!=rows[i][0]+(j-i)*TF:return None
        if rows[j][2]>=target:return j
    return None


def bar_state(rows,r,e20,j):
    """State known at close of completed bar j; decision can occur at open j+1."""
    e=r['entry']; lo=max(r['i'],j-2); q=rows[lo:j+1]
    tak=sum((x[9]/x[6] if x[6] else .5) for x in q)/len(q)-.5
    prev=max(0,j-3)
    return {'progress':100*(rows[j][4]-e)/e,
            'taker':tak,
            'd20':100*(rows[j][4]-e20[j])/e20[j],
            's20':100*(e20[j]-e20[prev])/e20[prev] if e20[prev] else 0}

RULES=(
 ('GB40_30',.40,30,False,False),
 ('GB40_60',.40,60,False,False),
 ('GB30_60',.30,60,False,False),
 ('GB30_90',.30,90,False,False),
 ('GB40_FLOW_60',.40,60,True,False),
 ('GB30_FLOW_90',.30,90,True,False),
 ('GB40_D20_90',.40,90,False,True),
 ('GB40_FLOW_D20_90',.40,90,True,True),
)


def find_signal(rows,r,e20,rule):
    name,thr,maxmin,need_flow,need_d20=rule
    h=r.get('hinge')
    if h is None:return None
    # decision must occur before original BUY exit and before original 6h horizon.
    exit_idx=r['i']+r['trade']['bars']-1
    maxj=min(exit_idx-1,h+maxmin//5,r['i']+HOLD//5-2)
    for j in range(h+1,maxj+1):
        st=bar_state(rows,r,e20,j)
        if st['progress']>thr:continue
        if need_flow and st['taker']>=0:continue
        if need_d20 and st['d20']>=0:continue
        return {'bar':j,'decision':j+1,'state':st,'mins_after_hinge':(j-h)*5}
    return None


def protect_pnl(rows,r,sig,lock):
    """At next 5m open after completed deterioration signal, arm profit lock.
    If open has already fallen through lock, exit at actual open. Otherwise keep TP2 alive
    and use lock as protective stop. Same-bar TP+lock -> lock first (adverse-first).
    """
    if sig is None:return r['trade']['net_usd']
    i=r['i']; e=r['entry']; j=sig['decision']; end=i+HOLD//5
    if j>=end:return r['trade']['net_usd']
    open_px=rows[j][1]; lock_px=e*(1+lock/100); tp_px=e*(1+TP/100)
    if open_px<=lock_px:
        exit_px=open_px
    else:
        exit_px=None
        for k in range(j,end):
            x=rows[k]
            if x[0]!=rows[i][0]+(k-i)*TF:return r['trade']['net_usd']
            hit_lock=x[3]<=lock_px; hit_tp=x[2]>=tp_px
            if hit_lock and hit_tp:
                exit_px=lock_px; break
            if hit_lock:
                exit_px=lock_px; break
            if hit_tp:
                exit_px=tp_px; break
        if exit_px is None: exit_px=rows[end-1][4]
    gross=100*(exit_px-e)/e
    return NOTIONAL*(gross-FEE)/100


def candidate_stats(rec,rule,lock,subset):
    q=rec[subset]
    pn=[]; signals=[]
    for r in q:
        if r['wrongway']:
            pn.append(r['a612']); continue
        sig=r['signals'][rule[0]]
        new=protect_pnl(r['rows'],r,sig,lock) if sig else r['base']
        pn.append(new)
        if sig: signals.append((r,new))
    base=[r['a612'] for r in q]
    return {'stats':econ(pn),'baseline':econ(base),'delta':rnd(sum(pn)-sum(base),3),
            'signals':len(signals),
            'loss_to_win':sum(r['base']<=0 and new>0 for r,new in signals),
            'win_to_loss':sum(r['base']>0 and new<=0 for r,new in signals),
            'win_clipped':sum(r['base']>0 and 0<new<r['base'] for r,new in signals),
            'loss_still_loss':sum(r['base']<=0 and new<=0 for r,new in signals)}


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20); rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]]; t=a60.trade(rows,i,TP,SL,HOLD); p=a69.path_stats(rows,i,x[1])
        if t is None or p is None:continue
        r={'rows':rows,'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p,'base':t['net_usd']}; r['label']=a69.label(r)
        r['wrongway']=wrongway_signal(rows,r,e7,e20); r['a612']=wrongway_pnl(rows,r)
        r['hinge']=None if r['wrongway'] else actionable_hinge(rows,r)
        r['signals']={rule[0]:find_signal(rows,r,e20,rule) for rule in RULES}
        rec.append(r)
    assert len(rec)==138
    # executable hinge capacity among ORIGINAL eventual losses / winners, excluding wrong-way-flipped states
    eligible=[r for r in rec if not r['wrongway'] and r['hinge'] is not None]
    cap={'eligible_total':len(eligible),'eligible_original_winners':sum(r['base']>0 for r in eligible),
         'eligible_original_losses':sum(r['base']<=0 for r in eligible),
         'eligible_C':sum(r['label']=='C_GIVEBACK_05_10' for r in eligible),
         'eligible_D':sum(r['label']=='D_DEEP_GIVEBACK_GE_10' for r in eligible)}
    # discovery-only ranking by combined PnL delta vs A6.12; require >=5 discovery signals.
    candidates=[]
    for rule in RULES:
        for lock in LOCKS:
            disc=candidate_stats(rec,rule,lock,slice(0,82))
            val=candidate_stats(rec,rule,lock,slice(82,None))
            full=candidate_stats(rec,rule,lock,slice(None))
            score=disc['delta'] if disc['signals']>=5 else -1e9
            candidates.append({'rule':rule[0],'lock':lock,'score_disc':rnd(score,3),'discovery':disc,'validation':val,'full':full})
    chosen=max(candidates,key=lambda z:(z['score_disc'],z['discovery']['loss_to_win'],-z['discovery']['win_to_loss']))
    crule=next(r for r in RULES if r[0]==chosen['rule']); clock=chosen['lock']
    # materialize combined chosen layer for robustness summaries
    for r in rec:
        if r['wrongway']:r['combined']=r['a612'];r['gb_action']=False
        else:
            sig=r['signals'][crule[0]]; r['gb_action']=sig is not None
            r['combined']=protect_pnl(rows,r,sig,clock) if sig else r['base']
    base=[r['base'] for r in rec]; dyn=[r['a612'] for r in rec]; comb=[r['combined'] for r in rec]
    blocks=[]
    for b in range(8):
        lo=round(len(rec)*b/8);hi=round(len(rec)*(b+1)/8);q=rec[lo:hi]
        blocks.append({'block':b+1,'n':len(q),'parent':rnd(sum(r['base'] for r in q),3),
                       'a612':rnd(sum(r['a612'] for r in q),3),'combined':rnd(sum(r['combined'] for r in q),3),
                       'gb_delta':rnd(sum(r['combined']-r['a612'] for r in q),3),'gb_actions':sum(r['gb_action'] for r in q)})
    years={}
    for y in sorted(set(ldt(r['ts']).year for r in rec)):
        q=[r for r in rec if ldt(r['ts']).year==y]
        years[str(y)]={'n':len(q),'gb_actions':sum(r['gb_action'] for r in q),
                       'parent':econ([r['base'] for r in q]),'a612':econ([r['a612'] for r in q]),
                       'combined':econ([r['combined'] for r in q]),
                       'gb_delta':rnd(sum(r['combined']-r['a612'] for r in q),3)}
    acts=[r for r in rec if r['gb_action']]
    trans={'actions':len(acts),'loss_to_win':sum(r['base']<=0 and r['combined']>0 for r in acts),
           'win_to_loss':sum(r['base']>0 and r['combined']<=0 for r in acts),
           'win_clipped':sum(r['base']>0 and 0<r['combined']<r['base'] for r in acts),
           'loss_still_loss':sum(r['base']<=0 and r['combined']<=0 for r in acts)}
    out={'status':'FRIDAY15_A613_EXECUTABLE_GIVEBACK_RESCUE','n':138,
         'parent':econ(base),'a612_baseline':econ(dyn),'actionable_hinge_capacity':cap,
         'selection':'giveback rule+lock ranked on first82 discovery delta only; validation unopened for selection',
         'candidates':sorted(candidates,key=lambda z:z['score_disc'],reverse=True),
         'chosen':chosen,'combined':econ(comb),'combined_delta_vs_parent':rnd(sum(comb)-sum(base),3),
         'giveback_delta_vs_a612':rnd(sum(comb)-sum(dyn),3),'transitions':trans,
         'blocks':blocks,'positive_gb_delta_blocks':sum(b['gb_delta']>0 for b in blocks),'years':years}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
