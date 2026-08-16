"""Saturday18 A7.3 — actual historical funding + execution-cost stress.

Uses Binance Data Vision USD-M monthly fundingRate archives for BTCUSDT.
Evaluates the full 18h A7.2 plateau (TP 2.4-4.0, SL 1.0-1.4).
Funding payment approximation uses fixed contract qty = $500 / entry and BTCUSDT
5m open at funding settlement as settlement notional proxy. Positive funding is paid by BUY.
"""
import csv, io, json, urllib.request, zipfile
from datetime import datetime, timezone
from btc_temporal_saturday18_a70_money_geometry import load, ldt, EVAL_START, EVAL_END, TF, trade, max_dd, loss_streak, rnd

NOTIONAL=500.0
TPS=(2.4,2.6,2.8,3.0,3.2,3.4,3.6,3.8,4.0)
SLS=(1.0,1.1,1.2,1.3,1.4)
HOLD=1080
EXTRA_COSTS=(0.0,0.02,0.05,0.10,0.15)

def months(start_ms,end_ms):
    d=datetime.fromtimestamp(start_ms/1000,tz=timezone.utc).replace(day=1)
    e=datetime.fromtimestamp((end_ms-1)/1000,tz=timezone.utc).replace(day=1)
    out=[]
    while d<=e:
        out.append((d.year,d.month))
        if d.month==12: d=d.replace(year=d.year+1,month=1)
        else: d=d.replace(month=d.month+1)
    return out

def load_funding():
    rec=[]; headers=[]; misses=[]
    for y,m in months(EVAL_START,EVAL_END):
        ym=f'{y:04d}-{m:02d}'
        url=f'https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{ym}.zip'
        try:
            with urllib.request.urlopen(url,timeout=30) as r: raw=r.read()
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names=[n for n in z.namelist() if n.lower().endswith('.csv')]
                if not names: raise RuntimeError('no csv')
                text=io.TextIOWrapper(z.open(names[0]),encoding='utf-8')
                dr=csv.DictReader(text)
                fields=dr.fieldnames or []
                if fields and fields not in headers: headers.append(fields)
                tkey=next((k for k in fields if k.lower() in ('calc_time','fundingtime','funding_time')),None)
                rkey=next((k for k in fields if 'funding' in k.lower() and 'rate' in k.lower()),None)
                if rkey is None: rkey=next((k for k in fields if 'rate' in k.lower()),None)
                if not tkey or not rkey: raise RuntimeError(f'unknown header {fields}')
                for row in dr:
                    try:
                        t=int(float(row[tkey])); rate=float(row[rkey])
                        if EVAL_START<=t<EVAL_END: rec.append((t,rate))
                    except Exception: pass
        except Exception as exc:
            misses.append({'month':ym,'error':str(exc)[:120]})
    rec.sort()
    return rec,headers,misses

def block_id(ts):
    return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))

def eval_cfg(rows,idx,funding,tp,sl,extra):
    im={x[0]:x for x in rows}
    split=int(len(idx)*.60); vals=[]; funding_events=0; funding_total=0.0
    for i in idx:
        t=trade(rows,i,tp,sl,HOLD)
        if t is None: continue
        exit_ts=t['ts']+(t['bars']-1)*TF
        qty=NOTIONAL/t['entry']
        fpay=0.0; nev=0
        for ft,rate in funding:
            if ft<=t['ts']: continue
            if ft>exit_ts: break
            px=(im.get(ft) or [None,t['entry']])[1]
            fpay += -qty*px*rate
            nev += 1
        adj=t['net_usd']+fpay-NOTIONAL*extra/100.0
        vals.append({'ts':t['ts'],'pnl':adj,'funding':fpay,'events':nev})
        funding_events+=nev; funding_total+=fpay
    pnls=[x['pnl'] for x in vals]; n=len(vals)
    pos=sum(x for x in pnls if x>0); neg=-sum(x for x in pnls if x<0); wins=sum(x>0 for x in pnls)
    blocks=[rnd(sum(x['pnl'] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
    def sub(v):
        p=[x['pnl'] for x in v]; nn=len(v); po=sum(x for x in p if x>0); ne=-sum(x for x in p if x<0)
        return {'n':nn,'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/nn,4),'wr':rnd(100*sum(x>0 for x in p)/nn,2),'pf':rnd(po/ne,3) if ne>0 else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p)}
    return {'tp':tp,'sl':sl,'hold_min':HOLD,'extra_cost_pct':extra,'n':n,'net_pnl':rnd(sum(pnls),3),'exp':rnd(sum(pnls)/n,4),'wr':rnd(100*wins/n,2),'pf':rnd(pos/neg,3) if neg>0 else None,'mdd':rnd(max_dd(pnls),3),'ls':loss_streak(pnls),'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks,'funding_events':funding_events,'funding_usd':rnd(funding_total,3),'discovery':sub(vals[:split]),'validation':sub(vals[split:])}

def main():
    rows=load(); imidx={x[0]:i for i,x in enumerate(rows)}
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0: idx.append(imidx[x[0]])
    funding,headers,misses=load_funding()
    allres=[]
    for extra in EXTRA_COSTS:
      for tp in TPS:
       for sl in SLS:
        allres.append(eval_cfg(rows,idx,funding,tp,sl,extra))
    per_cost={}
    for extra in EXTRA_COSTS:
        q=[x for x in allres if x['extra_cost_pct']==extra]
        robust=[x for x in q if x['net_pnl']>0 and x['discovery']['pnl']>0 and x['validation']['pnl']>0 and x['positive_blocks']>=6]
        robust=sorted(robust,key=lambda x:(min(x['discovery']['exp'],x['validation']['exp']),x['net_pnl'],x['pf'] or 0,-x['mdd']),reverse=True)
        positive=[x for x in q if x['net_pnl']>0 and x['discovery']['pnl']>0 and x['validation']['pnl']>0]
        per_cost[str(extra)]={'robust_count':len(robust),'cross_positive_count':len(positive),'best_robust':robust[:10]}
    chosen={}
    for tp,sl in ((3.0,1.1),(3.0,1.2),(2.8,1.1),(3.2,1.1)):
        chosen[f'{tp}/{sl}']=[x for x in allres if x['tp']==tp and x['sl']==sl]
    out={'status':'SATURDAY18_A73_FUNDING_COST_STRESS','funding':{'records':len(funding),'headers':headers,'missing_months':misses,'sum_rate_pct':rnd(sum(r for _,r in funding)*100,5)},'plateau':per_cost,'chosen':chosen}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
