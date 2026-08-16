"""Saturday18 A7.14 — strict-causal thesis-failure intervention.

Frozen parent remains BUY Saturday 18:00 WIB, TP2.6%, SL1.2%, max18h.
Signal is evaluated after 60 completed minutes; decision is next 5m OPEN.
EMA variants use only EMA values through the last completed 5m candle.

Two frozen detector families from A7.13b:
- FLOW: progress <= -0.10% and completed-hour taker edge < 0
- EMA:  progress <= -0.10%, decision open below last-completed EMA20,
        and EMA20 3-bar slope < 0

Actions:
- CUT: close BUY at actual decision open, no phantom fill.
- FLIP: close BUY at decision open and open SHORT at same actual price.
  Both legs pay full assumed 0.15% round-trip fee; historical funding is charged
  with correct long/short sign. Same-bar TP+SL for SHORT uses SL-first precedence.

Compact flip geometries are predeclared. Discovery first83 ranks them; validation
last56 is then reported. No entry filtering: all 139 Saturdays still generate an entry.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade, FEE_PCT, NOTIONAL, max_dd, loss_streak
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6; SL=1.2; HOLD=1080; CP=60
DETECTORS={
 'FLOW': lambda s:s['progress']<=-0.10 and s['taker']<0,
 'EMA20_SLOPE': lambda s:s['progress']<=-0.10 and s['d20']<0 and s['s20_3']<0,
}
# name,tp,sl,max_hold_after_flip_minutes; REMAIN means until original 18h end.
FLIPS=(
 ('S08_08_4H',0.8,0.8,240),
 ('S08_08_8H',0.8,0.8,480),
 ('S12_12_6H',1.2,1.2,360),
 ('S12_12_12H',1.2,1.2,720),
 ('S12_08_6H',1.2,0.8,360),
 ('S12_08_12H',1.2,0.8,720),
 ('S26_12_REMAIN',2.6,1.2,None),
)

def block_id(ts): return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))

def funding_leg(funding,tsmap,start_ts,end_ts,qty,side,entry_px):
    z=0.0
    for ft,rate in funding:
        if ft<=start_ts:continue
        if ft>end_ts:break
        px=(tsmap.get(ft) or [None,entry_px])[1]
        # Positive funding: longs pay, shorts receive.
        z += (-1 if side=='LONG' else 1)*qty*px*rate
    return z

def short_leg(rows,j,end_i,tp,sl,funding,tsmap):
    if j>=end_i:return None
    e=rows[j][1]; tp_px=e*(1-tp/100.0); sl_px=e*(1+sl/100.0)
    exit_px=None; exit_i=None; reason='TIMEOUT'
    for k in range(j,end_i):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        x=rows[k]; hit_tp=x[3]<=tp_px; hit_sl=x[2]>=sl_px
        if hit_tp and hit_sl: exit_px=sl_px;exit_i=k;reason='AMB_SL';break
        if hit_sl: exit_px=sl_px;exit_i=k;reason='SL';break
        if hit_tp: exit_px=tp_px;exit_i=k;reason='TP';break
    if exit_px is None:
        exit_i=end_i-1; exit_px=rows[exit_i][4]
    gross_pct=100*(e-exit_px)/e
    raw=NOTIONAL*(gross_pct-FEE_PCT)/100.0
    fp=funding_leg(funding,tsmap,rows[j][0],rows[exit_i][0],NOTIONAL/e,'SHORT',e)
    return raw+fp,exit_i,reason

def intervention(rows,r,detector,mode,funding,tsmap,flip_cfg=None):
    s=r['state'];
    if not s or not detector(s):return r['base'],False,'NO_SIGNAL'
    j=s['decision_i']; e=r['entry']; dec=rows[j][1]
    # Long leg closes at actual decision open; one full long round-trip fee.
    long_gross_pct=100*(dec-e)/e
    long_raw=NOTIONAL*(long_gross_pct-FEE_PCT)/100.0
    long_funding=funding_leg(funding,tsmap,rows[r['i']][0],rows[j][0],NOTIONAL/e,'LONG',e)
    long_pnl=long_raw+long_funding
    if mode=='CUT':return long_pnl,True,'CUT'
    name,tp,sl,fh=flip_cfg
    original_end=min(len(rows),r['i']+HOLD//5)
    flip_end=original_end if fh is None else min(original_end,j+fh//5)
    sh=short_leg(rows,j,flip_end,tp,sl,funding,tsmap)
    if sh is None:return r['base'],False,'DATA_GAP'
    return long_pnl+sh[0],True,'FLIP_'+name+'_'+sh[2]

def summary(vals,key):
    p=[x[key] for x in vals]; n=len(p); pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    blocks=[rnd(sum(x[key] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p),
      'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}

def evaluate(rows,recs,detector,mode,funding,tsmap,flip_cfg=None):
    vals=[]; actions=rescued=damaged=improved_losses=0; reasons={}
    for r in recs:
        final,act,reason=intervention(rows,r,detector,mode,funding,tsmap,flip_cfg)
        if act:
            actions+=1;reasons[reason]=reasons.get(reason,0)+1
            if r['base']<=0 and final>0:rescued+=1
            if r['base']>0 and final<=0:damaged+=1
            if r['base']<=0 and final>r['base']:improved_losses+=1
        vals.append({'ts':r['ts'],'base':r['base'],'final':final})
    b=summary(vals,'base'); z=summary(vals,'final')
    z.update({'delta':rnd(z['pnl']-b['pnl'],3),'actions':actions,'rescued':rescued,'damaged':damaged,
              'improved_losses':improved_losses,'reasons':reasons})
    return z

def build():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; tsmap={x[0]:x for x in rows}
    e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,miss=load_funding();recs=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
        i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,_,_=a74.funding_adjust(rows,t,funding,tsmap)
        recs.append({'i':i,'ts':x[0],'entry':t['entry'],'base':base,
                     'state':a713b.causal_state(rows,i,CP,e7,e20)})
    return rows,tsmap,funding,miss,recs

def main():
    rows,tsmap,funding,miss,recs=build();disc=recs[:83];val=recs[83:]
    base=summary([{'ts':r['ts'],'base':r['base']} for r in recs],'base')
    out=[]
    for dname,dfn in DETECTORS.items():
        # CUT is not ranked against flip geometry; always report.
        out.append({'detector':dname,'action':'CUT','discovery':evaluate(rows,disc,dfn,'CUT',funding,tsmap),
                    'validation':evaluate(rows,val,dfn,'CUT',funding,tsmap),'full':evaluate(rows,recs,dfn,'CUT',funding,tsmap)})
        for cfg in FLIPS:
            out.append({'detector':dname,'action':cfg[0],'cfg':cfg,
                        'discovery':evaluate(rows,disc,dfn,'FLIP',funding,tsmap,cfg),
                        'validation':evaluate(rows,val,dfn,'FLIP',funding,tsmap,cfg),
                        'full':evaluate(rows,recs,dfn,'FLIP',funding,tsmap,cfg)})
    # Discovery-only ranking among FLIPs. CUT kept separately.
    flips=[x for x in out if x['action']!='CUT']
    flips.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['pf'] or 0,-x['discovery']['mdd'],-x['discovery']['damaged']),reverse=True)
    cuts=[x for x in out if x['action']=='CUT']
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A714_THESIS_FAILURE_INTERVENTION','parent':base,
      'funding_missing':miss,'detectors':list(DETECTORS),'flip_configs':FLIPS,
      'cuts':cuts,'flips_ranked_discovery_only':flips},separators=(',',':')),flush=True)
if __name__=='__main__':main()
