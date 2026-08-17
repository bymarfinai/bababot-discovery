"""Friday T-Method F5.6 — fresh OOS test on 2026-07-31, 2026-08-07, 2026-08-14.

Frozen before reading these OOS outcomes:
- Friday15 BUY parent TP2.0 / SL0.7 / hold6h
- causal +0.50% MFE hinge
- F5.4/F5.5 fixed conjunction:
    range_ratio >= 2.683993
    AND pre_eff240 >= 0.165628
  -> PROTECT +0.20%, otherwise RUNNER

Historical research sample ended 2026-07-30. No OOS retuning is allowed.
"""
import csv,io,json,urllib.request,zipfile
from datetime import datetime,timezone,timedelta
import btc_temporal_friday15_f52_runner_protect as F
import btc_temporal_friday15_f53_separability_attribution as A
from btc_temporal_a34_5m_events import load, rnd

OOS_DATES=['2026-07-31','2026-08-07','2026-08-14']
RANGE=2.683993
EFF240=0.165628
TZ=timezone(timedelta(hours=7))


def load_daily(date):
    fn=f'BTCUSDT-5m-{date}.zip'
    url=f'https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/5m/{fn}'
    print('DAILY',fn,flush=True)
    with urllib.request.urlopen(url,timeout=60) as q:data=q.read()
    out=[]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        rd=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8'))
        for a in rd:
            try:t=int(a[0])
            except:continue
            if t>10**14:t//=1000
            out.append((t,float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5]),float(a[7]),float(a[8]),float(a[9]),float(a[10])))
    return out


def extend_rows(hist):
    d={x[0]:x for x in hist}
    cur=datetime(2026,7,30,tzinfo=timezone.utc)
    end=datetime(2026,8,16,tzinfo=timezone.utc)
    while cur<end:
        ds=cur.strftime('%Y-%m-%d')
        for x in load_daily(ds):d[x[0]]=x
        cur+=timedelta(days=1)
    return [d[k] for k in sorted(d)]


def idx_for(rows,date):
    dt=datetime.strptime(date+' 15:00','%Y-%m-%d %H:%M').replace(tzinfo=TZ).astimezone(timezone.utc)
    ts=int(dt.timestamp()*1000)
    im={x[0]:i for i,x in enumerate(rows)}
    return im[ts]


def econ(ps):
    if not ps:return {'n':0,'wr':None,'pnl':0.0,'avg':None,'pf':None}
    pos=sum(x for x in ps if x>0);neg=-sum(x for x in ps if x<=0)
    return {'n':len(ps),'wr':rnd(100*sum(x>0 for x in ps)/len(ps),2),'pnl':rnd(sum(ps),3),
            'avg':rnd(sum(ps)/len(ps),4),'pf':rnd(pos/neg,3) if neg else None}


def main():
    hist=load();rows=extend_rows(hist)
    cases=[];parent=[];cand=[]
    for date in OOS_DATES:
        i=idx_for(rows,date)
        b=F.base_result(rows,i)
        if b is None:raise RuntimeError('incomplete parent '+date)
        s=F.trigger_state(rows,i)
        p=F.protect_result(rows,i,s) if s else None
        if s:
            s.update(A.preentry_features(rows,i))
        fire=bool(s is not None and p is not None and s.get('range_ratio') is not None and s.get('pre_eff240') is not None and
                  s['range_ratio']>=RANGE and s['pre_eff240']>=EFF240)
        base=b['net_usd']; final=p['net_usd'] if fire else base
        parent.append(base);cand.append(final)
        cases.append({'date':date,'parent':rnd(base,3),'candidate':rnd(final,3),'delta':rnd(final-base,3),
                      'parent_reason':b['reason'],'hinge':s is not None,'protect_fired':fire,
                      'range_ratio':rnd(s['range_ratio'],4) if s else None,
                      'pre_eff240':rnd(s['pre_eff240'],4) if s and s.get('pre_eff240') is not None else None,
                      'progress_close':rnd(s['progress_close'],4) if s else None,
                      'time_min':s['time_min'] if s else None})
    out={'status':'FRIDAY_TMETHOD_F56_FRESH_OOS_JUL31_AUG14',
         'historical_end':'2026-07-30','oos_dates':OOS_DATES,
         'frozen_rule':{'range_ratio_min':RANGE,'pre_eff240_min':EFF240,'hinge':0.5,'lock':0.2},
         'parent':econ(parent),'candidate':econ(cand),'cases':cases,
         'notes':'Fresh OOS only. No parameter selection or retuning used OOS outcomes.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
