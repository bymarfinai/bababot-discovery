"""Saturday18 A7.23 — frozen A7.19 robustness audit.

No search for a new champion. Primary frozen candidate under audit:
  Saturday18 BUY parent TP2.6/SL1.2/18h
  at 240 completed minutes, decision next 5m open
  if 0.50 <= MFE < 0.80, current progress 0.20..0.40, taker edge <0 -> DIRECT exit.

Audit only:
- year and 8-block distribution
- leave-one-action-out sensitivity
- small boundary perturbation of natural A7.12 C/D split (0.75/0.80/0.85/0.90)
- checkpoint perturbation 210/240/270m with otherwise same rule
- extra execution-cost stress, both strategy-wide and intervention-only

All calculations retain historical funding and one original roundtrip fee.
"""
import json
import btc_temporal_saturday18_a717_lockable_profit_protection as a717
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b

CAPS=(0.75,0.80,0.85,0.90)
CPS=(210,240,270)
EXTRA=(0.00,0.02,0.05,0.10)

def detector(s,cap=0.80):return bool(s and 0.5<=s['mfe']<cap and 0.20<=s['progress']<=0.40 and s['taker']<0)

def managed(rows,r,funding,tsmap,cap=0.80):
    s=r['state']
    if not detector(s,cap):return r['base'],False
    j=s['decision_i'];e=r['entry'];dec=rows[j][1]
    return a717.pnl_at_exit(e,dec,rows[r['i']][0],rows[j][0],funding,tsmap),True

def summarize_pairs(vals,key):return a717.summarize([{'ts':x['ts'],key:x[key]} for x in vals],key)

def eval_recs(rows,recs,funding,tsmap,cap=0.80):
    vals=[];acts=[]
    for ix,r in enumerate(recs):
        f,a=managed(rows,r,funding,tsmap,cap); vals.append({'ts':r['ts'],'base':r['base'],'final':f})
        if a:acts.append({'idx':ix,'ts':r['ts'],'base':r['base'],'final':f,'delta':f-r['base']})
    return vals,acts

def stats(vals,key):return a717.summarize(vals,key)

def year_stats(vals):
    import datetime as dt
    out={}
    for y in (2023,2024,2025,2026):
        q=[x for x in vals if dt.datetime.fromtimestamp(x['ts']/1000,dt.timezone.utc).year==y]
        if q:
            b=stats(q,'base');f=stats(q,'final');out[str(y)]={'n':len(q),'base_wr':b['wr'],'final_wr':f['wr'],'base_pnl':b['pnl'],'final_pnl':f['pnl'],'delta':a717.rnd(f['pnl']-b['pnl'],3)}
    return out

def main():
    rows,tsmap,funding,miss,recs=a717.build();disc=recs[:83];val=recs[83:]
    vals,acts=eval_recs(rows,recs,funding,tsmap,0.80)
    base=stats(vals,'base');final=stats(vals,'final')
    dvals,dacts=eval_recs(rows,disc,funding,tsmap,0.80);vvals,vacts=eval_recs(rows,val,funding,tsmap,0.80)
    # Leave one action out: restore that action to parent while all other frozen actions remain.
    loo=[]
    for a in acts:
        q=[dict(x) for x in vals];q[a['idx']]['final']=q[a['idx']]['base'];s=stats(q,'final')
        loo.append({'ts':a['ts'],'removed_delta':a717.rnd(a['delta'],3),'pnl':s['pnl'],'wr':s['wr'],'pf':s['pf'],'mdd':s['mdd']})
    # Natural boundary sensitivity; not used to select.
    caps=[]
    for cap in CAPS:
        q,aa=eval_recs(rows,recs,funding,tsmap,cap);ds,_=eval_recs(rows,disc,funding,tsmap,cap);vs,_=eval_recs(rows,val,funding,tsmap,cap)
        sf=stats(q,'final');sd=stats(ds,'final');sv=stats(vs,'final')
        caps.append({'cap':cap,'actions':len(aa),'full':sf,'discovery_delta':a717.rnd(sd['pnl']-stats(ds,'base')['pnl'],3),'validation_delta':a717.rnd(sv['pnl']-stats(vs,'base')['pnl'],3)})
    # Checkpoint perturbation: rebuild strict causal state at cp, same cap=.8.
    cpout=[]
    e7=a717.a74.ema_series(rows,7);e20=a717.a74.ema_series(rows,20)
    for cp in CPS:
        rr=[]
        for r in recs:
            z=dict(r);z['state']=a713b.causal_state(rows,r['i'],cp,e7,e20);rr.append(z)
        q,aa=eval_recs(rows,rr,funding,tsmap,0.80);ds,_=eval_recs(rows,rr[:83],funding,tsmap,0.80);vs,_=eval_recs(rows,rr[83:],funding,tsmap,0.80)
        sf=stats(q,'final');bd=stats(ds,'base');bv=stats(vs,'base');sd=stats(ds,'final');sv=stats(vs,'final')
        cpout.append({'checkpoint':cp,'actions':len(aa),'full':sf,'discovery_delta':a717.rnd(sd['pnl']-bd['pnl'],3),'validation_delta':a717.rnd(sv['pnl']-bv['pnl'],3)})
    # Extra costs. Percent is of $500 notional. strategy-wide applies to every trade; intervention-only to actions.
    cost=[]
    for ex in EXTRA:
        usd=a717.NOTIONAL*ex/100.0
        allq=[dict(x, stressed=x['final']-usd) for x in vals]
        actset={a['idx'] for a in acts};intq=[dict(x, stressed=x['final']-(usd if i in actset else 0)) for i,x in enumerate(vals)]
        cost.append({'extra_pct':ex,'all_trades':stats(allq,'stressed'),'interventions_only':stats(intq,'stressed')})
    out={'status':'SATURDAY18_A723_A719_ROBUSTNESS','funding_missing':miss,
      'frozen_rule':'240m / MFE 0.50..<0.80 / progress 0.20..0.40 / taker<0 / DIRECT next 5m open',
      'base':base,'frozen_full':final,'discovery':stats(dvals,'final'),'validation':stats(vvals,'final'),
      'discovery_delta':a717.rnd(stats(dvals,'final')['pnl']-stats(dvals,'base')['pnl'],3),
      'validation_delta':a717.rnd(stats(vvals,'final')['pnl']-stats(vvals,'base')['pnl'],3),
      'actions':acts,'year_stats':year_stats(vals),'leave_one_action_out':loo,'cap_sensitivity':caps,'checkpoint_sensitivity':cpout,'extra_cost':cost}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
