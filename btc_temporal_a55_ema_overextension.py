"""BTC Temporal A5.5 — test EMA overextension/exhaustion after A5.4 forensic signal.

A5.4 found almost no trigger-candle EMA reclaim; all protect-better cases were
still below falling EMA7/20. The useful signal was distance: giveback cases were
more extended below EMA than runners at the +0.50% hinge.

This script tests a compact, interpretable local family only:
- frozen A5.2 state gated by EMA7/EMA20 overextension
- slightly broadened weak/giveback state gated by overextension
- steep EMA7 downside slope as exhaustion context
No initial entries are filtered; execution remains A5.2 realistic next-open protect.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END


def cond(cfg,r):
    s=r['state']; e=r.get('ema')
    if not s or not e:return False
    mode=cfg['mode']; d7=cfg.get('d7'); d20=cfg.get('d20'); slope=cfg.get('slope')
    if mode=='FROZEN': base=s['progress_close']<=0.35 and s['mae']>=0.20
    elif mode=='BROAD': base=s['progress_close']<=0.40 and s['mae']>=0.15
    elif mode=='WEAK': base=s['progress_close']<=0.35
    else:return False
    if not base:return False
    if d7 is not None and not (e['d7']<=-d7):return False
    if d20 is not None and not (e['d20']<=-d20):return False
    if slope is not None and not (e['s7_1']<=-slope):return False
    return True


def configs():
    z=[{'name':'A52_FROZEN','mode':'FROZEN'}]
    for x in (0.15,0.20,0.25,0.30):
        z.append({'name':f'FROZEN_D7_{x}','mode':'FROZEN','d7':x})
        z.append({'name':f'BROAD_D7_{x}','mode':'BROAD','d7':x})
        z.append({'name':f'WEAK_D7_{x}','mode':'WEAK','d7':x})
    for x in (0.25,0.30,0.35,0.40):
        z.append({'name':f'FROZEN_D20_{x}','mode':'FROZEN','d20':x})
        z.append({'name':f'BROAD_D20_{x}','mode':'BROAD','d20':x})
    for x in (0.06,0.07,0.08,0.09):
        z.append({'name':f'FROZEN_S7_{x}','mode':'FROZEN','slope':x})
        z.append({'name':f'BROAD_S7_{x}','mode':'BROAD','slope':x})
    # Stronger conjunctive states centered on A5.4 medians, not a large grid.
    z += [
      {'name':'BROAD_D7_020_S7_007','mode':'BROAD','d7':0.20,'slope':0.07},
      {'name':'BROAD_D7_025_S7_007','mode':'BROAD','d7':0.25,'slope':0.07},
      {'name':'BROAD_D7_020_D20_030','mode':'BROAD','d7':0.20,'d20':0.30},
      {'name':'FROZEN_D7_020_D20_030','mode':'FROZEN','d7':0.20,'d20':0.30},
    ]
    return z


def evaluate(recs,cfg):
    out=[]; actions=rescued=damaged=0
    for r in recs:
        f=r['base']
        if r['protect'] is not None and cond(cfg,r):
            f=r['protect']; actions+=1
            if r['base']<=0 and f>0:rescued+=1
            if r['base']>0 and f<=0:damaged+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=a52.summarize(out); b=a52.summarize(out,'base')
    z.update({'name':cfg['name'],'cfg':cfg,'actions':actions,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-b['pnl'],3)})
    return z


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); recs=a54.add_ema(rows,recs,a54.ema_series(rows,7),a54.ema_series(rows,20))
    split=int(len(recs)*.60); disc=recs[:split]; val=recs[split:]
    base=a52.summarize([{'ts':r['ts'],'final':r['base']} for r in recs])
    tests=[]
    for c in configs():
        d=evaluate(disc,c); v=evaluate(val,c); f=evaluate(recs,c)
        tests.append({'name':c['name'],'discovery':d,'validation':v,'full':f})
    # Same causal frozen rule in both periods; no full-sample selection criterion used for this shortlist.
    cross=[x for x in tests if x['discovery']['delta']>0 and x['validation']['delta']>0]
    cross.sort(key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['damaged']),reverse=True)
    # Compare explicitly against A5.2 frozen champion.
    frozen=next(x for x in tests if x['name']=='A52_FROZEN')
    upgrades=[x for x in cross if x['full']['pnl']>frozen['full']['pnl'] and x['full']['wr']>=frozen['full']['wr']]
    out={'status':'A55_EMA_OVEREXTENSION','data':{'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'configs':len(tests)},
         'parent_base':base,'a52_frozen':frozen,'cross_period':cross,'strict_upgrades_over_a52':upgrades,
         'best_full':sorted(tests,key=lambda x:(x['full']['pnl'],x['full']['wr']),reverse=True)}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
