"""BTC Friday15 A6.45 — pre-entry futures positioning attribution.

Diagnostics only; no strategy changes.
Source: official Binance Data Vision USD-M daily metrics archives.
For each Friday15 WIB entry (=08:00 UTC), use only metric snapshots strictly before entry.
Features: OI/OI-value 30/60/120m changes, top-trader account/position ratios,
global account ratio, taker long-short volume ratio and 60m changes.
Mechanistic interaction: seller-led pre-entry price/flow state x OI rising/falling.
"""
import csv, io, json, math, statistics, urllib.request, zipfile
from datetime import datetime, timezone
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'
COLS=['create_time','symbol','sum_open_interest','sum_open_interest_value','count_toptrader_long_short_ratio','sum_toptrader_long_short_ratio','count_long_short_ratio','sum_taker_long_short_vol_ratio']

def mean(x):return statistics.mean(x) if x else None

def med(x):return statistics.median(x) if x else None

def sd(x):return statistics.stdev(x) if len(x)>1 else 0.0

def smd(a,b):
    a=[x for x in a if x is not None];b=[x for x in b if x is not None]
    if len(a)<2 or len(b)<2:return None
    den=math.sqrt((statistics.variance(a)+statistics.variance(b))/2)
    return rnd((mean(a)-mean(b))/den,3) if den else 0.0

def corr(x,y):
    q=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(q)<3:return None
    xa=[a for a,b in q];ya=[b for a,b in q];mx=mean(xa);my=mean(ya)
    num=sum((a-mx)*(b-my) for a,b in q);den=math.sqrt(sum((a-mx)**2 for a in xa)*sum((b-my)**2 for b in ya))
    return rnd(num/den,3) if den else 0.0

def group(d):
    if d<DD_START:return 'PRE_DD'
    if d<=DD_END:return 'DD'
    return 'POST'

def parse_time(s):
    s=str(s).strip()
    try:
        v=int(float(s))
        if v>10**14:v//=1000
        if v>10**11:return v
    except:pass
    z=s.replace('Z','+00:00')
    dt=datetime.fromisoformat(z)
    if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp()*1000)

def load_day(date):
    fn=f'BTCUSDT-metrics-{date}.zip'
    url=f'https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/{fn}'
    try:
        with urllib.request.urlopen(url,timeout=30) as q:data=q.read()
    except Exception as e:
        print('METRICS_SKIP',date,type(e).__name__,str(e)[:100],flush=True);return []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        rd=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8')); rows=list(rd)
    if not rows:return []
    hdr=[x.strip().lower() for x in rows[0]]; has='create_time' in hdr
    if has:
        idx={c:hdr.index(c) for c in COLS if c in hdr}; data_rows=rows[1:]
    else:
        idx={c:i for i,c in enumerate(COLS)};data_rows=rows
    out=[]
    for a in data_rows:
        try:
            d={'ts':parse_time(a[idx['create_time']])}
            for c in COLS[2:]:d[c]=float(a[idx[c]])
            out.append(d)
        except:continue
    return sorted(out,key=lambda z:z['ts'])

def pct(a,b):return 100*(a/b-1) if b else None

def nearest_at_or_before(q,ts):
    a=[x for x in q if x['ts']<=ts]
    return a[-1] if a else None

def features(q,entry_ts):
    last=nearest_at_or_before(q,entry_ts-1)
    if not last:return None
    out={
      'top_account':last['count_toptrader_long_short_ratio'],
      'top_position':last['sum_toptrader_long_short_ratio'],
      'global_account':last['count_long_short_ratio'],
      'taker_ls':last['sum_taker_long_short_vol_ratio'],
      'oi_value':last['sum_open_interest_value'],
    }
    for mins in (30,60,120):
        old=nearest_at_or_before(q,entry_ts-mins*60000)
        out[f'oi_base_chg_{mins}']=pct(last['sum_open_interest'],old['sum_open_interest']) if old else None
        out[f'oi_value_chg_{mins}']=pct(last['sum_open_interest_value'],old['sum_open_interest_value']) if old else None
        out[f'top_account_chg_{mins}']=pct(last['count_toptrader_long_short_ratio'],old['count_toptrader_long_short_ratio']) if old else None
        out[f'top_position_chg_{mins}']=pct(last['sum_toptrader_long_short_ratio'],old['sum_toptrader_long_short_ratio']) if old else None
        out[f'global_account_chg_{mins}']=pct(last['count_long_short_ratio'],old['count_long_short_ratio']) if old else None
        out[f'taker_ls_chg_{mins}']=pct(last['sum_taker_long_short_vol_ratio'],old['sum_taker_long_short_vol_ratio']) if old else None
    out['snapshot_offset_min']=(entry_ts-last['ts'])/60000
    return out

def stat(v):
    v=[x for x in v if x is not None]
    return {'n':len(v),'mean':rnd(mean(v),4),'median':rnd(med(v),4),'sd':rnd(sd(v),4)}

def econ(q):
    p=[r['chosen'] for r in q]
    if not p:return {'n':0,'wr':None,'pnl':0,'avg':None,'pf':None}
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2),'pnl':rnd(sum(p),3),'avg':rnd(mean(p),4),'pf':rnd(pos/neg,3) if neg else None}

def main():
    rows,rec=a636.build();cache={};usable=[]
    for r in rec:
        d=str(ldt(r['ts']).date());r['date']=d;r['grp']=group(d)
        if d not in cache:
            cache[d]=load_day(d);print('METRICS_DAY',d,'ROWS',len(cache[d]),flush=True)
        r['pos']=features(cache[d],r['ts'])
        if r['pos'] is None:continue
        micro=a642.features(rows,r)
        r['seller_led']=micro['taker_imb_60']<0 and micro['netret_60']<0
        r['expansion']=micro['vol_ratio24_60']>1 and micro['range_ratio24_60']>1
        r['stress_core']=r['seller_led'] and r['expansion']
        usable.append(r)
    print('METRICS_USABLE',len(usable),flush=True)
    groups={g:[r for r in usable if r['grp']==g] for g in ('PRE_DD','DD','POST')}
    names=list(usable[0]['pos'].keys()) if usable else []
    feats={}
    for n in names:
        pre=[r['pos'][n] for r in groups['PRE_DD']];dd=[r['pos'][n] for r in groups['DD']];post=[r['pos'][n] for r in groups['POST']]
        feats[n]={'pre':stat(pre),'dd':stat(dd),'post':stat(post),'smd_dd_vs_pre':smd(dd,pre),'smd_dd_vs_post':smd(dd,post),
                  'corr_vs_pnl':corr([r['pos'][n] for r in usable],[r['chosen'] for r in usable])}
    ranked=sorted([{'feature':n,**feats[n]} for n in names if n!='oi_value'],key=lambda z:abs(z['smd_dd_vs_pre'] or 0),reverse=True)
    # Mechanistic sign interaction: seller-led/stress x OI-value change sign, thresholds only zero.
    interactions={}
    for g,q in groups.items():
        z={}
        for state_name in ('seller_led','stress_core'):
            for oi_up in (False,True):
                a=[r for r in q if r[state_name] and r['pos']['oi_value_chg_60'] is not None and (r['pos']['oi_value_chg_60']>0)==oi_up]
                z[f'{state_name}_OIUP{int(oi_up)}']=econ(a)
        # all OI sign regardless micro state
        z['ALL_OIUP']=econ([r for r in q if r['pos']['oi_value_chg_60'] is not None and r['pos']['oi_value_chg_60']>0])
        z['ALL_OIDOWN']=econ([r for r in q if r['pos']['oi_value_chg_60'] is not None and r['pos']['oi_value_chg_60']<=0])
        interactions[g]=z
    # Frequency of seller-led OI build vs deleveraging.
    freq={}
    for g,q in groups.items():
        sell=[r for r in q if r['seller_led'] and r['pos']['oi_value_chg_60'] is not None]
        freq[g]={'n':len(q),'seller_led_n':len(sell),
                 'seller_oi_up_rate':rnd(100*sum(r['pos']['oi_value_chg_60']>0 for r in sell)/len(sell),2) if sell else None,
                 'stress_rate':rnd(100*sum(r['stress_core'] for r in q)/len(q),2) if q else None}
    out={'status':'FRIDAY15_A645_POSITIONING_ATTRIBUTION','coverage':{'usable':len(usable),'total':len(rec),'days':len(cache)},
         'features':feats,'ranked_dd_vs_pre':ranked,'interactions':interactions,'frequency':freq,
         'notes':'Diagnostics only. All snapshots strictly precede entry; OI interaction threshold is sign only, not optimized.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
