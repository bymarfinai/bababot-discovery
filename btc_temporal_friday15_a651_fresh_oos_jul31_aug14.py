"""BTC Friday15 A6.51 — fresh OOS test for 2026-07-31, 2026-08-07, 2026-08-14.

Frozen before reading OOS outcomes:
- A6.33 Friday15 BUY engine and management
- A6.48 online shadow-health detector architecture
- A6.50 risk governor: 50% notional only when DEFENSIVE + current stress_unwind

No parameter selection or retuning is performed on these OOS Fridays.
The historical research sample ended 2026-07-30; these three Fridays are fresh.
"""
import csv,io,json,statistics,urllib.request,zipfile
from datetime import datetime,timezone,timedelta
import btc_temporal_friday15_a649_regime_direction_switch as a649
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
import btc_temporal_friday15_a645_positioning_attribution as a645
from btc_temporal_a34_5m_events import ldt,rnd,TF

OOS_DATES=['2026-07-31','2026-08-07','2026-08-14']
FAST_W=8;SLOW_W=13;COND_W=13;MIN_COND=2;HYST=2;SCALE=.5;HOLD=360
TZ=timezone(timedelta(hours=7))

def load_daily(date):
    fn=f'BTCUSDT-5m-{date}.zip';url=f'https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/5m/{fn}'
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
    start=datetime(2026,7,30,tzinfo=timezone.utc);end=datetime(2026,8,16,tzinfo=timezone.utc)
    cur=start
    while cur<end:
        ds=cur.strftime('%Y-%m-%d')
        for x in load_daily(ds):d[x[0]]=x
        cur+=timedelta(days=1)
    return [d[k] for k in sorted(d)]

def make_record(rows,im,e7,e20,date):
    dt=datetime.strptime(date+' 15:00','%Y-%m-%d %H:%M').replace(tzinfo=TZ).astimezone(timezone.utc)
    ts=int(dt.timestamp()*1000);i=im[ts];x=rows[i]
    t=a636.a60.trade(rows,i,2.,.7,HOLD);p=a636.a69.path_stats(rows,i,x[1])
    if t is None or p is None:raise RuntimeError('incomplete OOS path '+date)
    r={'rows':rows,'i':i,'ts':ts,'entry':x[1],'trade':t,'path':p,'base':t['net_usd']};r['label']=a636.a69.label(r)
    r['wrongway']=a636.a620.confirmed(rows,r,e7,e20);r['prior_stop']=r['wrongway'] and a636.a617b.exited_before_120(r)
    r['hinge']=None if r['wrongway'] else a636.a613.actionable_hinge(rows,r)
    r['sig']=a636.a613.find_signal(rows,r,e20,a636.RULE) if r['hinge'] is not None else None
    r['dist_active']=not r['wrongway'] and a636.a620.distribution_active(r['sig'])
    r['baseline']=a636.a630.baseline(rows,r)
    r['c60']=a636.a69.checkpoint(rows,r,e7,e20,60)
    r['ema45']=a636.a632.ema_state(rows,r,e7,e20,45)
    r['chosen'],r['action'],r['source']=a636.a633.managed(rows,r,'EMA45_OR_FULL60')
    r['date']=date
    return r

def raw120(rows,r):return 100*(rows[r['i']+24][1]-r['entry'])/r['entry']
def mean(x):return statistics.mean(x) if x else None

def econ(p):
    if not p:return {'n':0,'wr':None,'pnl':0.,'avg':None,'pf':None,'mdd':None,'ls':None}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),'avg':rnd(mean(p),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a636.a60.max_dd(p),3),'ls':a636.a60.loss_streak(p)}

def main():
    # a649.build reconstructs the frozen 138-Friday historical shadow records and stress states.
    hist_rows,hist=a649.build()
    rows=extend_rows(hist_rows);im={x[0]:i for i,x in enumerate(rows)}
    e7=a636.a74.ema_series(rows,7);e20=a636.a74.ema_series(rows,20)
    oos=[]
    for date in OOS_DATES:
        r=make_record(rows,im,e7,e20,date)
        m=a642.features(rows,r);pos=a645.features(a645.load_day(date),r['ts'])
        seller=m['taker_imb_60']<0 and m['netret_60']<0
        stress=seller and m['vol_ratio24_60']>1 and m['range_ratio24_60']>1
        r['stress_unwind']=stress and pos['oi_value_chg_60']<=0
        r['ret120']=raw120(rows,r);oos.append(r)

    allr=hist+oos
    # Re-run frozen A6.48 state machine over history + OOS. Historical current outcomes only
    # affect subsequent Fridays; never their own state.
    state=False;en=0;ex=0
    audit=[]
    for i,r in enumerate(allr):
        fast=allr[max(0,i-FAST_W):i];slow=allr[max(0,i-SLOW_W):i];cw=allr[max(0,i-COND_W):i]
        cond=[x for x in cw if x.get('stress_unwind',False)]
        f=mean([x['chosen'] for x in fast]) if len(fast)==FAST_W else None
        s=mean([x['chosen'] for x in slow]) if len(slow)==SLOW_W else None
        cp=mean([x['chosen'] for x in cond]) if len(cond)>=MIN_COND else None
        cr=mean([x['ret120'] for x in cond if x.get('ret120') is not None]) if len(cond)>=MIN_COND else None
        confirms=sum(v is not None and v<0 for v in (s,cp,cr))
        enter=f is not None and f<0 and confirms>=1;exit_=f is not None and s is not None and f>0 and s>0
        en=en+1 if enter else 0;ex=ex+1 if exit_ else 0
        if not state and en>=HYST:state=True;ex=0
        elif state and ex>=HYST:state=False;en=0
        r['defensive_oos']=state
        if r in oos:
            scale=SCALE if state and r['stress_unwind'] else 1.0
            r['scale']=scale;r['a650']=r['chosen']*scale
            audit.append({'date':r['date'],'defensive':state,'stress_unwind':r['stress_unwind'],'scale':scale,
                          'fast8':rnd(f,4) if f is not None else None,'slow13':rnd(s,4) if s is not None else None,
                          'cond_n':len(cond),'cond_pnl':rnd(cp,4) if cp is not None else None,'cond_ret120':rnd(cr,4) if cr is not None else None,
                          'a633_pnl':rnd(r['chosen'],3),'a650_pnl':rnd(r['a650'],3),'parent_reason':r['trade']['reason'],
                          'wrongway':r['wrongway'],'damage_source':r['source'],'ret120':rnd(r['ret120'],3)})
    out={'status':'FRIDAY15_A651_FRESH_OOS_JUL31_AUG14','historical_end':'2026-07-30','oos_dates':OOS_DATES,
         'frozen_rules':'A6.33 + A6.48 + A6.50, no OOS retuning','oos_a633':econ([r['chosen'] for r in oos]),
         'oos_a650':econ([r['a650'] for r in oos]),'cases':audit,
         'combined_141_a633':econ([r['chosen'] for r in allr]),
         'combined_141_a650':econ([r['chosen'] for r in hist]+[r['a650'] for r in oos]),
         'notes':'Fresh OOS only: OOS outcomes were not used to select or alter any rule. Current Friday state uses prior outcomes only.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
