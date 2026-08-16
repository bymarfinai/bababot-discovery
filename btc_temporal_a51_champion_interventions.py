"""BTC Temporal A5.1 — causal interventions on frozen champion 1.35/0.8/6h.

Selection discipline:
- Parent TP/SL/hold is frozen.
- Chronological discovery first 83 Tuesdays, validation last 56.
- Only two intervention families justified by A5.0 are tested:
  A) early thesis-failure FLIP at minute 10 or 15;
  B) profit protection after meaningful short MFE.
- No pre-entry filtering; every Tuesday still enters SELL at 06:00.
- Profit-protection activation starts NEXT 5m bar after threshold is first reached,
  avoiding same-bar lookahead/order assumptions.
- Same-bar ambiguity is conservative/adverse-first.
"""
import json, math, statistics
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade, FEE_PCT, NOTIONAL, max_drawdown, loss_streak

TP=1.35; SL=0.80; HOLD=360
CPS=(10,15)
ADV=(0.02,0.04,0.06,0.08,0.10,0.12)
MFE_MAX=(0.10,0.15,0.20)
TAKER_MIN=(0.0,0.005,0.01)
CLOSEPOS_MIN=(0.55,0.60,0.65)
LONG_GEOMS=((0.8,0.8),(1.35,0.8))
PROTECT_TRIG=(0.4,0.5,0.6,0.8)
PROTECT_LOCK=(0.0,0.1,0.2,0.3)


def contiguous(rows,i,nb):
    return i+nb<=len(rows) and all(rows[j][0]==rows[i][0]+(j-i)*TF for j in range(i,i+nb))

def state(rows,i,cp):
    nb=cp//5
    if not contiguous(rows,i,nb+1): return None
    e=rows[i][1]; tp=e*(1-TP/100); sl=e*(1+SL/100); obs=rows[i:i+nb]
    for x in obs:
        if x[3]<=tp or x[2]>=sl:return None
    dec=rows[i+nb][1]; hi=max(x[2] for x in obs); lo=min(x[3] for x in obs)
    tbr=[(x[9]/x[6] if x[6] else .5) for x in obs]
    return {'net':100*(dec-e)/e,'mfe':100*(e-lo)/e,'mae':100*(hi-e)/e,
            'taker':statistics.mean(tbr)-.5,'close_pos':(dec-lo)/max(hi-lo,1e-9),
            'up_frac':sum(x[4]>x[1] for x in obs)/len(obs)}

def close_short(rows,i,j):
    e=rows[i][1]; px=rows[j][1]
    return NOTIONAL*((100*(e-px)/e)-FEE_PCT)/100

def long_trade(rows,j,end_i,tp,sl):
    e=rows[j][1]; tp_px=e*(1+tp/100); sl_px=e*(1-sl/100); ex=None
    for k in range(j,min(end_i,len(rows))):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return None
        ht=rows[k][2]>=tp_px; hs=rows[k][3]<=sl_px
        if ht and hs: ex=sl_px; break
        if hs: ex=sl_px; break
        if ht: ex=tp_px; break
    if ex is None: ex=rows[min(end_i,len(rows))-1][4]
    return NOTIONAL*((100*(ex-e)/e)-FEE_PCT)/100

def flip_pnl(rows,i,cp,ltp,lsl):
    s=state(rows,i,cp)
    if s is None:return None
    j=i+cp//5; end=min(len(rows),i+HOLD//5)
    lp=long_trade(rows,j,end,ltp,lsl)
    if lp is None:return None
    return close_short(rows,i,j)+lp

def protective_pnl(rows,i,trig,lock):
    """Frozen parent; after trigger is touched, protection stop starts next bar."""
    e=rows[i][1]; tp_px=e*(1-TP/100); orig_sl=e*(1+SL/100); pstop=e*(1-lock/100)
    end=min(len(rows),i+HOLD//5); active_from=None; ex=None
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF:return None
        # Existing active stop is adverse-first vs TP on ambiguous bar.
        if active_from is not None and j>=active_from:
            hp=x[2]>=pstop; ht=x[3]<=tp_px
            if hp and ht: ex=pstop; break
            if hp: ex=pstop; break
            if ht: ex=tp_px; break
        else:
            ht=x[3]<=tp_px; hs=x[2]>=orig_sl
            if ht and hs: ex=orig_sl; break
            if hs: ex=orig_sl; break
            if ht: ex=tp_px; break
        # Activate only for next bar after threshold observed.
        if active_from is None and x[3]<=e*(1-trig/100): active_from=j+1
    if ex is None: ex=rows[end-1][4]
    return NOTIONAL*((100*(e-ex)/e)-FEE_PCT)/100

def summary(records,key='final'):
    ps=[r[key] for r in records]; n=len(ps); w=sum(x>0 for x in ps); pos=sum(x for x in ps if x>0); neg=-sum(x for x in ps if x<=0)
    blocks=[]
    for b in range(8):
        q=[r[key] for r in records if min(7,max(0,int((r['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        blocks.append(sum(q))
    return {'trades':n,'wins':w,'losses':n-w,'wr':rnd(100*w/n,2),'pnl':rnd(sum(ps),3),'exp':rnd(sum(ps)/n,4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_drawdown(ps),3),'ls':loss_streak(ps),
            'blocks_pos':sum(x>0 for x in blocks)}

def build(rows,idx):
    out=[]
    for i in idx:
        b=trade(rows,i,TP,SL,HOLD)
        if b is not None: out.append({'i':i,'ts':rows[i][0],'base':b['net_usd'],'states':{cp:state(rows,i,cp) for cp in CPS}})
    return out

def eval_flip(rows,recs,cfg):
    cp,adv,mf,tk,cpos,ltp,lsl=cfg; out=[]; actions=rescued=damaged=0
    for r in recs:
        f=r['base']; s=r['states'][cp]
        if s and s['net']>=adv and s['mfe']<mf and s['taker']>tk and s['close_pos']>cpos:
            q=flip_pnl(rows,r['i'],cp,ltp,lsl)
            if q is not None:
                actions+=1
                if r['base']<=0 and q>0: rescued+=1
                if r['base']>0 and q<=0: damaged+=1
                f=q
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=summary(out); z.update({'cfg':cfg,'actions':actions,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-summary(out,'base')['pnl'],3)})
    return z

def eval_protect(rows,recs,cfg):
    trig,lock=cfg; out=[]; changed=rescued=damaged=0
    for r in recs:
        q=protective_pnl(rows,r['i'],trig,lock); f=q if q is not None else r['base']
        if abs(f-r['base'])>1e-9: changed+=1
        if r['base']<=0 and f>0: rescued+=1
        if r['base']>0 and f<=0: damaged+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=summary(out); z.update({'cfg':cfg,'changed':changed,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-summary(out,'base')['pnl'],3)})
    return z

def eval_hybrid(rows,recs,fcfg,pcfg):
    cp,adv,mf,tk,cpos,ltp,lsl=fcfg; trig,lock=pcfg; out=[]; flips=protected=rescued=damaged=0
    for r in recs:
        f=None; s=r['states'][cp]
        if s and s['net']>=adv and s['mfe']<mf and s['taker']>tk and s['close_pos']>cpos:
            q=flip_pnl(rows,r['i'],cp,ltp,lsl)
            if q is not None: f=q; flips+=1
        if f is None:
            q=protective_pnl(rows,r['i'],trig,lock); f=q if q is not None else r['base']; protected+=abs(f-r['base'])>1e-9
        if r['base']<=0 and f>0:rescued+=1
        if r['base']>0 and f<=0:damaged+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=summary(out); z.update({'flip_cfg':fcfg,'protect_cfg':pcfg,'flips':flips,'protected':protected,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-summary(out,'base')['pnl'],3)})
    return z

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=build(rows,idx); split=int(len(recs)*.60); disc=recs[:split]; val=recs[split:]
    base={'disc':summary([{'ts':r['ts'],'final':r['base']} for r in disc]),'val':summary([{'ts':r['ts'],'final':r['base']} for r in val]),'full':summary([{'ts':r['ts'],'final':r['base']} for r in recs])}

    flips=[]
    for cp in CPS:
      for adv in ADV:
       for mf in MFE_MAX:
        for tk in TAKER_MIN:
         for cpos in CLOSEPOS_MIN:
          for lg in LONG_GEOMS:
           cfg=(cp,adv,mf,tk,cpos,lg[0],lg[1]); d=eval_flip(rows,disc,cfg)
           if d['actions']>=4: flips.append((cfg,d))
    # Selection objective explicitly values both economics and conversion, penalizes collateral damage.
    flips.sort(key=lambda q:(q[1]['delta']+2.0*(q[1]['rescued']-q[1]['damaged']),q[1]['wr'],q[1]['pnl']),reverse=True)

    prots=[]
    for trig in PROTECT_TRIG:
      for lock in PROTECT_LOCK:
        cfg=(trig,lock); d=eval_protect(rows,disc,cfg); prots.append((cfg,d))
    prots.sort(key=lambda q:(q[1]['delta']+2.0*(q[1]['rescued']-q[1]['damaged']),q[1]['wr'],q[1]['pnl']),reverse=True)

    def pack(items,typ,n=12):
        z=[]
        for cfg,d in items[:n]:
            fun=eval_flip if typ=='flip' else eval_protect
            z.append({'discovery':d,'validation':fun(rows,val,cfg),'full':fun(rows,recs,cfg)})
        return z
    fp=pack(flips,'flip'); pp=pack(prots,'protect')

    # Frozen hybrid: combine the independently discovery-selected #1 from each family.
    h=None
    if flips and prots:
        fc=flips[0][0]; pc=prots[0][0]
        h={'discovery':eval_hybrid(rows,disc,fc,pc),'validation':eval_hybrid(rows,val,fc,pc),'full':eval_hybrid(rows,recs,fc,pc)}

    # Cross-period shortlist is descriptive only; selection remains discovery-only.
    cross=[]
    for cfg,d in flips[:80]:
        v=eval_flip(rows,val,cfg); f=eval_flip(rows,recs,cfg)
        if d['delta']>0 and v['delta']>0 and f['pnl']>=base['full']['pnl'] and f['wr']>base['full']['wr']:
            cross.append({'discovery':d,'validation':v,'full':f})
    cross.sort(key=lambda x:(x['full']['wr'],x['full']['pnl'],x['validation']['delta']),reverse=True)

    out={'status':'A51_CHAMPION_INTERVENTIONS','parent':{'tp':TP,'sl':SL,'hold_min':HOLD},'data':{'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'flip_configs':len(flips),'protect_configs':len(prots)},
         'baseline':base,'discovery_selected_flip':fp,'discovery_selected_protect':pp,'frozen_hybrid':h,'cross_period_flip_shortlist':cross[:15]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
