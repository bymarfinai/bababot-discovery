"""Friday T-Method F5.10 — reversal geometry sensitivity.

F5.9 found no actionable causal BUY->SHORT router with the fixed 0.7/0.7/180m
SHORT leg. This milestone changes ONLY the sequential SHORT geometry while
keeping the same causal trigger families and discovery->validation discipline.

Diagnostic geometries are broad prior research shapes, not a fine optimizer:
- 0.7/0.7/180
- 1.0/0.7/240
- 1.3/0.7/360
- 1.5/0.5/360

All Friday entries retained. First causal trigger only. Selection discovery only.
"""
import json, statistics
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
import btc_temporal_friday15_f58_prepivot_causal_signature as F58
import btc_temporal_friday15_f59_causal_reversal_router as F59
from btc_temporal_a34_5m_events import load, rnd
from btc_temporal_friday15_a60_money_geometry import trade, FEE_PCT, NOTIONAL, max_dd, loss_streak

GEOMS=[(0.7,0.7,180),(1.0,0.7,240),(1.3,0.7,360),(1.5,0.5,360)]


def short_trade(rows,j,tp,sl,hold):
    e=rows[j][1];tp_px=e*(1-tp/100);sl_px=e*(1+sl/100);end=min(len(rows),j+hold//5);ex=None;reason='TIMEOUT'
    for k in range(j,end):
        if rows[k][0]!=rows[j][0]+(k-j)*F57.TF:return None
        x=rows[k];ht=x[3]<=tp_px;hs=x[2]>=sl_px
        if ht and hs:ex=sl_px;reason='SL_AMBIG';break
        if hs:ex=sl_px;reason='SL';break
        if ht:ex=tp_px;reason='TP';break
    if ex is None:
        if end<=j:return None
        ex=rows[end-1][4]
    gross=100*(e-ex)/e
    return NOTIONAL*(gross-FEE_PCT)/100


def summarize(ps):
    if not ps:return {'n':0,'pnl':0}
    pos=sum(x for x in ps if x>0);neg=-sum(x for x in ps if x<=0);w=sum(x>0 for x in ps)
    return {'n':len(ps),'wr':rnd(100*w/len(ps),2),'pnl':rnd(sum(ps),3),'exp':rnd(statistics.mean(ps),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(ps),3),'ls':loss_streak(ps)}


def build(rows,geom):
    tp,sl,hold=geom;recs=[]
    for i in F57.indices(rows):
        p=trade(rows,i,F57.BUY_TP,F57.BUY_SL,F57.BUY_HOLD)
        if p is None:continue
        ev=[]
        for m in range(F57.START_MIN,F57.END_MIN+1,F57.STEP_MIN):
            j=i+m//5
            if j>=len(rows) or rows[j][0]!=rows[i][0]+(j-i)*F57.TF:continue
            if not F57.parent_alive_before(rows,i,j):continue
            z=F58.feat(rows,i,j);s=short_trade(rows,j,tp,sl,hold)
            if z is None or s is None:continue
            buy=F57.buy_close_pnl(rows[i][1],rows[j][1]);z.update({'m':m,'exit_only':buy,'reverse':buy+s,'short':s});ev.append(z)
        recs.append({'ts':rows[i][0],'parent':p['net_usd'],'events':ev})
    return recs


def evaluate(recs,name,p):
    par=[];ex=[];rv=[];sh=[];mins=[]
    for r in recs:
        par.append(r['parent']);sig=None
        for z in r['events']:
            if F59.fires(name,p,z):sig=z;break
        if sig is None:ex.append(r['parent']);rv.append(r['parent'])
        else:ex.append(sig['exit_only']);rv.append(sig['reverse']);sh.append(sig['short']);mins.append(sig['m'])
    a=summarize(par);b=summarize(ex);c=summarize(rv);d=summarize(sh)
    return {'rule':name,'params':p,'actions':len(sh),'parent':a,'exit_only':b,'reverse':c,'short_legs':d,
            'exit_delta':rnd(b['pnl']-a['pnl'],3),'reverse_delta':rnd(c['pnl']-a['pnl'],3),'reverse_vs_exit':rnd(c['pnl']-b['pnl'],3),
            'median_min':rnd(statistics.median(mins),2) if mins else None}


def main():
    rows=load();out=[]
    for geom in GEOMS:
        recs=build(rows,geom);split=int(len(recs)*.60);disc=recs[:split];val=recs[split:]
        ds=[];cross=[]
        for n,p in F59.configs():
            d=evaluate(disc,n,p)
            if d['actions']<5:continue
            if d['reverse_delta']>0 and d['reverse_vs_exit']>0 and d['short_legs']['pnl']>0:
                v=evaluate(val,n,p);f=evaluate(recs,n,p);x={'discovery':d,'validation':v,'full':f};ds.append(x)
                if v['reverse_delta']>0 and v['reverse_vs_exit']>0 and v['short_legs']['pnl']>0:cross.append(x)
        ds.sort(key=lambda x:(x['discovery']['reverse_delta'],x['discovery']['reverse_vs_exit']),reverse=True)
        cross.sort(key=lambda x:(x['full']['reverse']['pnl'],x['validation']['reverse_delta']),reverse=True)
        out.append({'geometry':{'tp':geom[0],'sl':geom[1],'hold':geom[2]},'discovery_candidates':len(ds),'cross_positive':len(cross),
                    'best_discovery':ds[:5],'best_cross':cross[:5]})
    print('RESULT_JSON',json.dumps({'status':'FRIDAY_TMETHOD_F510_REVERSAL_GEOMETRY_SENSITIVITY','results':out,
      'notes':'Same F5.9 trigger families; only SHORT geometry changes. Diagnostic, not fresh OOS.'},separators=(',',':')),flush=True)
if __name__=='__main__':main()
