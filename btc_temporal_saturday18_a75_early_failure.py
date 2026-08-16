"""Saturday18 A7.5 — causal early-failure CUT / FLIP study.

Frozen parent remains unchanged:
  Saturday 18:00 WIB BUY, TP2.6%, SL1.2%, max18h.

A7.4 showed early separation between winners and losers. This study tests a compact,
interpretable family of post-entry failure rules at completed 15/30/60/120m bars.
Rules are selected ONLY on first 83 Saturdays (discovery), then frozen and evaluated
on the last 56 Saturdays (validation). All 139 original entries are retained.

Interventions:
- CUT: close BUY at the next 5m open after the completed observation window.
- FLIP: close BUY, then open SHORT at that same next-open price; the short uses
  TP1.2/SL1.2 or TP2.6/SL1.2 for the remaining original 18h horizon.

Both legs pay their own 0.15% round-trip fee. Historical funding is charged/credited
while each leg is actually open, using the same A7.3 approximation, including the
canonical entry-price fallback when a funding timestamp does not map to an exact 5m open.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade, FEE_PCT, NOTIONAL, max_dd, loss_streak
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.60; SL=1.20; HOLD=1080
CHECKPOINTS=(15,30,60,120)
PROG=(-0.00,-0.02,-0.05,-0.08,-0.12)
TAKER=(0.00,-0.01,-0.02,-0.03)
FAMILIES=('PT','PE','TE','PTE','PTS','PTES')
MIN_DISC_ACTIONS=6


def funding_pnl(funding,tsmap,entry_ts,exit_ts,qty,side,fallback_px):
    # Positive funding: long pays, short receives. Match A7.3 price fallback exactly.
    z=0.0; n=0
    sign=-1.0 if side=='BUY' else 1.0
    for ft,rate in funding:
        if ft<=entry_ts: continue
        if ft>exit_ts: break
        px=(tsmap.get(ft) or [None,fallback_px])[1]
        z += sign*qty*px*rate; n+=1
    return z,n

def parent_trade(rows,i,funding,tsmap):
    t=trade(rows,i,TP,SL,HOLD)
    if t is None:return None
    exit_i=i+t['bars']-1; exit_ts=rows[exit_i][0]
    qty=NOTIONAL/t['entry']
    fp,nev=funding_pnl(funding,tsmap,t['ts'],exit_ts,qty,'BUY',t['entry'])
    return {'ts':t['ts'],'i':i,'exit_i':exit_i,'entry':t['entry'],'pnl':t['net_usd']+fp,'raw':t['net_usd'],'funding':fp,'events':nev,'reason':t['reason']}

def state(rows,i,cp,e7,e20):
    return a74.state(rows,i,cp,e7,e20)

def rule_true(st,fam,p,t):
    if st is None:return False
    P=st['progress']<=p
    T=st['taker']<=t
    E=st['d20']<0
    S=st['s20_3']<0
    if fam=='PT':return P and T
    if fam=='PE':return P and E
    if fam=='TE':return T and E
    if fam=='PTE':return P and T and E
    if fam=='PTS':return P and T and S
    if fam=='PTES':return P and T and E and S
    return False

def close_buy(rows,i,j,funding,tsmap):
    e=rows[i][1]; px=rows[j][1]
    gross=100*(px-e)/e
    qty=NOTIONAL/e
    fp,_=funding_pnl(funding,tsmap,rows[i][0],rows[j][0],qty,'BUY',e)
    return NOTIONAL*(gross-FEE_PCT)/100.0+fp

def short_leg(rows,j,end_i,tp,sl,funding,tsmap):
    if j>=end_i:return None
    e=rows[j][1]; tp_px=e*(1-tp/100); sl_px=e*(1+sl/100); ex=None; ex_i=None; reason='TIMEOUT'
    for k in range(j,min(end_i,len(rows))):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        ht=rows[k][3]<=tp_px; hs=rows[k][2]>=sl_px
        if ht and hs:ex=sl_px;ex_i=k;reason='AMB_SL';break
        if hs:ex=sl_px;ex_i=k;reason='SL';break
        if ht:ex=tp_px;ex_i=k;reason='TP';break
    if ex is None:
        ex_i=min(end_i,len(rows))-1; ex=rows[ex_i][4]
    gross=100*(e-ex)/e
    qty=NOTIONAL/e
    fp,_=funding_pnl(funding,tsmap,rows[j][0],rows[ex_i][0],qty,'SHORT',e)
    return NOTIONAL*(gross-FEE_PCT)/100.0+fp,reason

def build(rows,funding):
    tsmap={x[0]:x for x in rows}; im={x[0]:i for i,x in enumerate(rows)}
    e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20)
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0:idx.append(im[x[0]])
    rec=[]
    for i in idx:
        b=parent_trade(rows,i,funding,tsmap)
        if not b:continue
        rec.append({**b,'states':{cp:state(rows,i,cp,e7,e20) for cp in CHECKPOINTS}})
    return rec,tsmap

def block_id(ts):return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))
def summarize(vals,key='final'):
    p=[x[key] for x in vals]; n=len(p); pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    blocks=[rnd(sum(x[key] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg>0 else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p),'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}

def apply(rows,recs,tsmap,funding,cand,mode):
    cp,fam,p,t=cand['cp'],cand['family'],cand['progress_le'],cand['taker_le']
    vals=[]; actions=rescued=damaged=improved_losses=0
    for r in recs:
        final=r['pnl']; action=False
        st=r['states'].get(cp)
        if st is not None and rule_true(st,fam,p,t):
            j=r['i']+cp//5
            if j<=r['exit_i']:
                buyclose=close_buy(rows,r['i'],j,funding,tsmap)
                if mode=='CUT':final=buyclose
                else:
                    stp=1.2 if mode=='FLIP12' else 2.6
                    q=short_leg(rows,j,r['i']+HOLD//5,stp,1.2,funding,tsmap)
                    if q is not None:final=buyclose+q[0]
                action=True
        if action:
            actions+=1
            if r['pnl']<=0 and final>0:rescued+=1
            if r['pnl']>0 and final<=0:damaged+=1
            if r['pnl']<=0 and final>r['pnl']:improved_losses+=1
        vals.append({'ts':r['ts'],'base':r['pnl'],'final':final})
    z=summarize(vals); b=summarize(vals,'base')
    z.update({'actions':actions,'rescued':rescued,'damaged':damaged,'improved_losses':improved_losses,'delta':rnd(z['pnl']-b['pnl'],3)})
    return z

def main():
    rows=load(); funding,headers,misses=load_funding(); recs,tsmap=build(rows,funding)
    disc=recs[:83]; val=recs[83:]
    base={'full':summarize([{'ts':r['ts'],'final':r['pnl']} for r in recs]),
          'discovery':summarize([{'ts':r['ts'],'final':r['pnl']} for r in disc]),
          'validation':summarize([{'ts':r['ts'],'final':r['pnl']} for r in val])}
    cands=[]
    for cp in CHECKPOINTS:
      for fam in FAMILIES:
       for p in PROG:
        for t in TAKER:
          c={'cp':cp,'family':fam,'progress_le':p,'taker_le':t}
          if 'P' not in fam and p!=PROG[0]:continue
          if 'T' not in fam and t!=TAKER[0]:continue
          dcut=apply(rows,disc,tsmap,funding,c,'CUT')
          if dcut['actions']>=MIN_DISC_ACTIONS:cands.append({**c,'mode':'CUT','discovery':dcut})
          for mode in ('FLIP12','FLIP26'):
              dz=apply(rows,disc,tsmap,funding,c,mode)
              if dz['actions']>=MIN_DISC_ACTIONS:cands.append({**c,'mode':mode,'discovery':dz})
    eligible=[x for x in cands if x['discovery']['delta']>0]
    eligible.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['pf'] or 0,-x['discovery']['damaged'],-x['discovery']['mdd']),reverse=True)
    selected=[]; seen_modes=set()
    for x in eligible:
        if x['mode'] in seen_modes:continue
        y=dict(x); y['validation']=apply(rows,val,tsmap,funding,y,y['mode']); y['full']=apply(rows,recs,tsmap,funding,y,y['mode'])
        selected.append(y); seen_modes.add(x['mode'])
        if len(seen_modes)==3:break
    audit=[]
    for x in eligible[:20]:
        y=dict(x); y['validation']=apply(rows,val,tsmap,funding,y,y['mode']); y['full']=apply(rows,recs,tsmap,funding,y,y['mode']); audit.append(y)
    out={'status':'SATURDAY18_A75_EARLY_FAILURE','parent':{'tp':TP,'sl':SL,'hold_min':HOLD,'trades':len(recs)},
      'funding':{'records':len(funding),'missing_months':misses},'baseline':base,
      'search':{'checkpoints':CHECKPOINTS,'progress_thresholds':PROG,'taker_thresholds':TAKER,'families':FAMILIES,'min_disc_actions':MIN_DISC_ACTIONS,'candidates':len(cands)},
      'selected_by_discovery_only':selected,'top20_discovery_ranked':audit}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
