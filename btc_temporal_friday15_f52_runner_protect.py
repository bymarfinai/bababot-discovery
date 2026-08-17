"""Friday T-Method F5.2 — conditional RUNNER vs PROTECT after +0.50% BUY MFE.

Mirrors Tuesday A5.2 discovery process, not its final thresholds.
Frozen parent: Friday 15:00 BUY, TP2.0, SL0.7, hold6h.
Frozen hinge from F5.1: first +0.50% favorable excursion.
At completed trigger 5m candle, decide next 5m open:
- RUNNER: parent unchanged
- PROTECT: +0.20% profit lock
If next open already lost the lock, exit at actual open.
No EMA, no A6.x layers, no entry filtering.
"""
import json, statistics
from btc_temporal_a34_5m_events import load, ldt, context, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_friday15_a60_money_geometry import trade, FEE_PCT, NOTIONAL

TP=2.0; SL=0.7; HOLD=360; HINGE=0.50; LOCK=0.20


def med(xs): return rnd(statistics.median(xs),4) if xs else None
def contiguous(rows,i,nb):
    return i+nb<=len(rows) and all(rows[j][0]==rows[i][0]+(j-i)*TF for j in range(i,i+nb))
def max_dd(ps):
    eq=peak=mdd=0.0
    for p in ps:
        eq+=p; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    return mdd
def loss_streak(ps):
    best=cur=0
    for p in ps:
        if p<=0:cur+=1;best=max(best,cur)
        else:cur=0
    return best
def base_result(rows,i):return trade(rows,i,TP,SL,HOLD)
def trigger_state(rows,i):
    e=rows[i][1]; hinge=e*(1+HINGE/100); tp=e*(1+TP/100); sl=e*(1-SL/100)
    end=min(len(rows),i+HOLD//5); pre=rows[max(0,i-12):i]
    pre_rng=statistics.median([x[2]-x[3] for x in pre]) if pre else 1.0
    pre_vol=statistics.median([x[6] for x in pre]) if pre else 1.0
    mfe=mae=0.0; takers=[]; rets=[]; up=0
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF:return None
        hit_tp=x[2]>=tp; hit_sl=x[3]<=sl
        if hit_tp and hit_sl:return None
        if hit_sl:return None
        if hit_tp:return None
        mfe=max(mfe,100*(x[2]-e)/e); mae=max(mae,100*(e-x[3])/e)
        takers.append(x[9]/x[6]-0.5 if x[6] else 0.0)
        r=100*(x[4]-x[1])/x[1]; rets.append(r); up+=x[4]>x[1]
        if x[2]>=hinge:
            dec=j+1
            if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[j][0]+TF:return None
            dec_open=rows[dec][1]; close=x[4]
            progress=100*(close-e)/e; dec_progress=100*(dec_open-e)/e
            close_pos=(close-x[3])/max(x[2]-x[3],1e-9)
            path_abs=sum(abs(z) for z in rets); efficiency=abs(progress)/max(path_abs,1e-9)
            c=context(rows,i)
            return {'trigger_i':j,'decision_i':dec,'time_min':(j-i+1)*5,
              'progress_close':progress,'progress_decision':dec_progress,'mfe':mfe,'mae':mae,
              'taker_avg':statistics.mean(takers),'taker_last':takers[-1],'close_pos_trigger':close_pos,
              'up_frac':up/len(rets),'efficiency':efficiency,'range_ratio':(x[2]-x[3])/max(pre_rng,1e-9),
              'volume_ratio':x[6]/max(pre_vol,1e-9),'day_pos':c['day_pos'] if c else None,
              'pre1':c['pre1'] if c else None,'pre4':c['pre4'] if c else None,'pre24':c['pre24'] if c else None}
    return None
def protect_result(rows,i,s):
    e=rows[i][1]; pstop=e*(1+LOCK/100); tp=e*(1+TP/100); j=s['decision_i']; end=min(len(rows),i+HOLD//5); op=rows[j][1]
    if op<=pstop:
        ex=op; reason='MARKET_LOCK_LOST'
    else:
        ex=None; reason='TIMEOUT'
        for k in range(j,end):
            x=rows[k]
            if x[0]!=rows[j][0]+(k-j)*TF:return None
            hs=x[3]<=pstop; ht=x[2]>=tp
            if hs and ht:ex=pstop;reason='PROTECT';break
            if hs:ex=pstop;reason='PROTECT';break
            if ht:ex=tp;reason='TP';break
        if ex is None:ex=rows[end-1][4]
    gross=100*(ex-e)/e
    return {'net_usd':NOTIONAL*(gross-FEE_PCT)/100,'reason':reason}
def summarize(rs,key='final'):
    ps=[r[key] for r in rs];n=len(ps);w=sum(x>0 for x in ps);pos=sum(x for x in ps if x>0);neg=-sum(x for x in ps if x<=0)
    blocks=[]
    for b in range(8):
        q=[r[key] for r in rs if min(7,max(0,int((r['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        blocks.append(sum(q))
    return {'trades':n,'wins':w,'losses':n-w,'wr':rnd(100*w/n,2),'pnl':rnd(sum(ps),3),'exp':rnd(sum(ps)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(ps),3),'ls':loss_streak(ps),'blocks_pos':sum(x>0 for x in blocks)}
def build(rows,idx):
    out=[]
    for i in idx:
        b=base_result(rows,i)
        if b is None:continue
        s=trigger_state(rows,i);p=protect_result(rows,i,s) if s else None
        out.append({'i':i,'ts':rows[i][0],'base':b['net_usd'],'state':s,'protect':p['net_usd'] if p else None})
    return out
def rule(name,s,p):
    if s is None:return False
    wc=p.get('weak_close');tk=p.get('taker');cp=p.get('closepos');slow=p.get('slow');mae=p.get('mae');eff=p.get('eff')
    if name=='WEAK_CLOSE':return s['progress_close']<=wc
    if name=='WEAK_CLOSE_SELLERS':return s['progress_close']<=wc and s['taker_avg']<=tk
    if name=='TRIGGER_REJECTION':return s['progress_close']<=wc and s['close_pos_trigger']<=cp
    if name=='SLOW_WEAK':return s['time_min']>=slow and s['progress_close']<=wc
    if name=='HIGH_MAE_WEAK':return s['mae']>=mae and s['progress_close']<=wc
    if name=='LOW_EFF_WEAK':return s['efficiency']<=eff and s['progress_close']<=wc
    if name=='SELLERS_REJECTION':return s['progress_close']<=wc and s['taker_avg']<=tk and s['close_pos_trigger']<=cp
    return False
def configs():
    out=[]
    for wc in (0.15,0.20,0.25,0.30,0.35,0.40):
        out.append(('WEAK_CLOSE',{'weak_close':wc}))
        for tk in (0.01,0.0,-0.01):out.append(('WEAK_CLOSE_SELLERS',{'weak_close':wc,'taker':tk}))
        for cp in (0.45,0.35,0.25):out.append(('TRIGGER_REJECTION',{'weak_close':wc,'closepos':cp}))
        for slow in (30,60,90,120):out.append(('SLOW_WEAK',{'weak_close':wc,'slow':slow}))
        for mae in (0.10,0.20,0.30):out.append(('HIGH_MAE_WEAK',{'weak_close':wc,'mae':mae}))
        for ef in (0.10,0.20,0.30):out.append(('LOW_EFF_WEAK',{'weak_close':wc,'eff':ef}))
        for tk in (0.0,-0.01):
            for cp in (0.45,0.35):out.append(('SELLERS_REJECTION',{'weak_close':wc,'taker':tk,'closepos':cp}))
    seen=set();z=[]
    for n,p in out:
        k=(n,tuple(sorted(p.items())))
        if k not in seen:seen.add(k);z.append((n,p))
    return z
def evaluate(recs,name,p):
    out=[];actions=rescued=damaged=0
    for r in recs:
        f=r['base']
        if r['protect'] is not None and rule(name,r['state'],p):
            f=r['protect'];actions+=1
            if r['base']<=0 and f>0:rescued+=1
            if r['base']>0 and f<=0:damaged+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=summarize(out);bz=summarize(out,'base')
    z.update({'rule':name,'params':p,'actions':actions,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-bz['pnl'],3)})
    return z
def atlas(recs):
    trig=[r for r in recs if r['state'] and r['protect'] is not None]
    pb=[r for r in trig if r['protect']>r['base']];rb=[r for r in trig if r['base']>=r['protect']]
    fields=('time_min','progress_close','progress_decision','mfe','mae','taker_avg','taker_last','close_pos_trigger','up_frac','efficiency','range_ratio','volume_ratio')
    def grp(q):return {'n':len(q),**{k+'_med':med([r['state'][k] for r in q]) for k in fields}}
    return {'hinge_trades':len(trig),'protect_better':grp(pb),'runner_better':grp(rb),'protect_all_realistic':evaluate(recs,'WEAK_CLOSE',{'weak_close':999.0})}
def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==4 and dt.hour==15 and dt.minute==0:idx.append(im[x[0]])
    recs=build(rows,idx);split=int(len(recs)*.60);disc=recs[:split];val=recs[split:]
    base={'discovery':summarize([{'ts':r['ts'],'final':r['base']} for r in disc]),'validation':summarize([{'ts':r['ts'],'final':r['base']} for r in val]),'full':summarize([{'ts':r['ts'],'final':r['base']} for r in recs])}
    grid=[]
    for n,p in configs():
        d=evaluate(disc,n,p)
        if d['actions']>=3:grid.append((n,p,d))
    grid.sort(key=lambda q:(q[2]['pnl']+2*(q[2]['rescued']-q[2]['damaged']),q[2]['wr'],-q[2]['damaged']),reverse=True)
    selected=[]
    for n,p,d in grid[:25]:selected.append({'discovery':d,'validation':evaluate(val,n,p),'full':evaluate(recs,n,p)})
    cross=[]
    for n,p,d in grid:
        v=evaluate(val,n,p);f=evaluate(recs,n,p)
        if d['delta']>0 and v['delta']>0 and f['pnl']>=base['full']['pnl'] and f['wr']>base['full']['wr']:
            cross.append({'discovery':d,'validation':v,'full':f})
    cross.sort(key=lambda x:(x['full']['pnl'],x['full']['wr'],x['validation']['delta']),reverse=True)
    frontier=[]
    for n,p,d in grid:
        v=evaluate(val,n,p);f=evaluate(recs,n,p)
        if f['pnl']>=0.90*base['full']['pnl'] and f['wr']>base['full']['wr']:
            frontier.append({'discovery':d,'validation':v,'full':f})
    frontier.sort(key=lambda x:(x['full']['wr'],x['full']['pnl']),reverse=True)
    out={'status':'FRIDAY_TMETHOD_F52_RUNNER_VS_PROTECT','parent':{'tp':TP,'sl':SL,'hold_min':HOLD,'hinge':HINGE,'lock':LOCK},
      'data':{'fridays':len(recs),'discovery':len(disc),'validation':len(val),'configs':len(grid)},'baseline':base,
      'atlas':{'discovery':atlas(disc),'validation':atlas(val),'full':atlas(recs)},
      'discovery_selected':selected,'strict_cross_period':cross[:20],'pnl90_wr_frontier':frontier[:20],
      'notes':'Friday detector thresholds discovered locally from F5.2; Tuesday final rule not copied.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
