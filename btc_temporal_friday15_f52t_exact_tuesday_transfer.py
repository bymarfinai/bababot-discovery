"""Friday T-Method F5.2T — exact directional mirror of Tuesday A5.2.
Negative/control transfer only; no selection.
Friday15 BUY parent TP2.0/SL0.7/6h.
Hinge +0.50 MFE, protect +0.20 iff completed hinge close progress <= +0.35 AND cumulative MAE >=0.20.
Also report Tuesday local-plateau sibling weak_close<=0.40 / MAE>=0.20.
"""
import json
from btc_temporal_a34_5m_events import load, ldt, EVAL_START, EVAL_END
from btc_temporal_friday15_f52_runner_protect import build, evaluate, summarize


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==15 and d.minute==0: idx.append(im[x[0]])
    recs=build(rows,idx); split=int(len(recs)*.60); disc=recs[:split]; val=recs[split:]
    base={
      'discovery':summarize([{'ts':r['ts'],'final':r['base']} for r in disc]),
      'validation':summarize([{'ts':r['ts'],'final':r['base']} for r in val]),
      'full':summarize([{'ts':r['ts'],'final':r['base']} for r in recs]),
    }
    out={'status':'FRIDAY_TMETHOD_F52T_EXACT_TUESDAY_A52_TRANSFER','baseline':base,'exact_frozen_mirror':{},'plateau_sibling':{}}
    for label,wc in [('exact_frozen_mirror',0.35),('plateau_sibling',0.40)]:
        p={'weak_close':wc,'mae':0.20}
        out[label]={'discovery':evaluate(disc,'HIGH_MAE_WEAK',p),'validation':evaluate(val,'HIGH_MAE_WEAK',p),'full':evaluate(recs,'HIGH_MAE_WEAK',p)}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
