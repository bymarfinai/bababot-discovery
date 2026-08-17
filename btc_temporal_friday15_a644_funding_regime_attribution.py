"""BTC Friday15 A6.44 — Binance funding/settlement regime attribution.

Diagnostics only; no strategy changes.
Funding source: official Binance Data Vision USD-M monthly fundingRate archives.
For each Friday15 WIB entry (=08:00 UTC):
- exact_funding: rate stamped exactly at entry time (descriptive only; not assumed live-causal)
- prev_funding: latest settled funding strictly before entry (causal)
- prev24_avg / prev24_sum: all settled rates in prior 24h (causal)
- prev_count24 and prev_interval: context for variable funding intervals
Compare PRE_DD / DD / POST, plus A6.43 stress-core interaction.
"""
import csv, io, json, math, statistics, urllib.request, zipfile
from datetime import datetime, timezone
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a642_preentry_microstructure_attribution as a642
from btc_temporal_a34_5m_events import ldt, rnd

DD_START='2025-05-09'; DD_END='2026-01-30'
LOAD_MONTHS=[]
y,m=2023,11
while (y,m)<=(2026,7):
    LOAD_MONTHS.append((y,m)); m+=1
    if m==13:y,m=y+1,1


def mean(x): return statistics.mean(x) if x else None

def med(x): return statistics.median(x) if x else None

def sd(x): return statistics.stdev(x) if len(x)>1 else 0.0

def smd(a,b):
    a=[x for x in a if x is not None]; b=[x for x in b if x is not None]
    if len(a)<2 or len(b)<2:return None
    den=math.sqrt((statistics.variance(a)+statistics.variance(b))/2)
    return rnd((statistics.mean(a)-statistics.mean(b))/den,3) if den else 0.0

def corr(x,y):
    q=[(a,b) for a,b in zip(x,y) if a is not None and b is not None]
    if len(q)<3:return None
    xa=[a for a,b in q]; ya=[b for a,b in q]; mx=mean(xa); my=mean(ya)
    num=sum((a-mx)*(b-my) for a,b in q)
    den=math.sqrt(sum((a-mx)**2 for a in xa)*sum((b-my)**2 for b in ya))
    return rnd(num/den,3) if den else 0.0

def group(d):
    if d<DD_START:return 'PRE_DD'
    if d<=DD_END:return 'DD'
    return 'POST'

def load_funding():
    out=[]
    for y,m in LOAD_MONTHS:
        fn=f'BTCUSDT-fundingRate-{y:04d}-{m:02d}.zip'
        url=f'https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/{fn}'
        print('FUNDING_DOWNLOAD',fn,flush=True)
        try:
            with urllib.request.urlopen(url,timeout=60) as q:data=q.read()
        except Exception as e:
            print('FUNDING_SKIP',fn,type(e).__name__,str(e)[:120],flush=True);continue
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            txt=io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8')
            rd=csv.reader(txt); rows=list(rd)
        if not rows:continue
        header=[str(x).strip().lower() for x in rows[0]]
        has_header='calc_time' in header
        if has_header:
            ti=header.index('calc_time'); ii=header.index('funding_interval_hours') if 'funding_interval_hours' in header else None
            ri=header.index('last_funding_rate') if 'last_funding_rate' in header else (header.index('funding_rate') if 'funding_rate' in header else None)
            data_rows=rows[1:]
        else:
            # Published fundingRate bulk schema: calc_time, funding_interval_hours, last_funding_rate
            ti,ii,ri=0,1,2; data_rows=rows
        if ri is None:raise RuntimeError(f'No funding rate column in {fn}: {header}')
        for a in data_rows:
            try:
                ts=int(float(a[ti]));
                if ts>10**14: ts//=1000
                interval=float(a[ii]) if ii is not None and a[ii] != '' else None
                rate=float(a[ri])
                out.append((ts,interval,rate))
            except Exception:continue
    d={x[0]:x for x in out}
    out=[d[k] for k in sorted(d)]
    print('FUNDING_ROWS',len(out),'FIRST',out[0] if out else None,'LAST',out[-1] if out else None,flush=True)
    return out

def align(fund,ts):
    # small dataset; linear pointer handled by caller would be faster, but this is trivial N~3k x138
    prev=[x for x in fund if x[0]<ts]
    exact=next((x for x in fund if x[0]==ts),None)
    p=prev[-1] if prev else None
    p24=[x for x in prev if x[0]>=ts-24*3600*1000]
    return {
      'exact_funding': exact[2]*100 if exact else None,
      'prev_funding': p[2]*100 if p else None,
      'prev_interval_h': p[1] if p else None,
      'prev24_avg': statistics.mean([x[2]*100 for x in p24]) if p24 else None,
      'prev24_sum': sum(x[2]*100 for x in p24) if p24 else None,
      'prev24_n': len(p24),
      'fund_change_exact_prev': (exact[2]-p[2])*100 if exact and p else None,
    }

def stat(v):
    v=[x for x in v if x is not None]
    return {'n':len(v),'mean':rnd(mean(v),6),'median':rnd(med(v),6),'sd':rnd(sd(v),6),
            'positive_rate':rnd(100*sum(x>0 for x in v)/len(v),2) if v else None,
            'negative_rate':rnd(100*sum(x<0 for x in v)/len(v),2) if v else None}

def econ(q):
    p=[r['chosen'] for r in q]
    pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':len(p),'wr':rnd(100*sum(x>0 for x in p)/len(p),2) if p else None,
            'pnl':rnd(sum(p),3),'avg':rnd(mean(p),4) if p else None,
            'pf':rnd(pos/neg,3) if neg else None}

def main():
    rows,rec=a636.build(); fund=load_funding()
    assert fund,'No funding data loaded'
    for r in rec:
        r['date']=str(ldt(r['ts']).date());r['grp']=group(r['date']);r['fund']=align(fund,r['ts'])
        micro=a642.features(rows,r)
        r['stress_core']=micro['vol_ratio24_60']>1 and micro['range_ratio24_60']>1 and micro['taker_imb_60']<0 and micro['netret_60']<0
    groups={g:[r for r in rec if r['grp']==g] for g in ('PRE_DD','DD','POST')}
    names=['exact_funding','prev_funding','prev24_avg','prev24_sum','fund_change_exact_prev','prev_interval_h']
    features={}
    for n in names:
        pre=[r['fund'][n] for r in groups['PRE_DD']];dd=[r['fund'][n] for r in groups['DD']];post=[r['fund'][n] for r in groups['POST']]
        features[n]={'pre':stat(pre),'dd':stat(dd),'post':stat(post),
                     'smd_dd_vs_pre':smd(dd,pre),'smd_dd_vs_post':smd(dd,post),
                     'corr_vs_pnl':corr([r['fund'][n] for r in rec],[r['chosen'] for r in rec])}
    # Natural causal sign splits for prior funding, no fitted thresholds.
    splits={}
    for n in ('prev_funding','prev24_avg','prev24_sum'):
        posq=[r for r in rec if r['fund'][n] is not None and r['fund'][n]>0]
        nonq=[r for r in rec if r['fund'][n] is not None and r['fund'][n]<=0]
        splits[n+'_positive']={'positive':econ(posq),'nonpositive':econ(nonq)}
    # Interaction: structural stress state x causal prior funding sign.
    interactions={}
    for g,q in groups.items():
        z={}
        for stress in (False,True):
            for fpos in (False,True):
                a=[r for r in q if r['stress_core']==stress and r['fund']['prev_funding'] is not None and (r['fund']['prev_funding']>0)==fpos]
                z[f'stress{int(stress)}_prevfundpos{int(fpos)}']=econ(a)
        interactions[g]=z
    # Exact-funding timing coverage and prior event offset verify alignment.
    offsets=[]
    for r in rec:
        prev=[x for x in fund if x[0]<r['ts']]
        if prev:offsets.append((r['ts']-prev[-1][0])/3600000)
    out={'status':'FRIDAY15_A644_FUNDING_REGIME_ATTRIBUTION','source':'Binance Data Vision USD-M monthly fundingRate BTCUSDT',
         'features':features,'causal_sign_splits':splits,'stress_funding_interaction':interactions,
         'coverage':{'trades':len(rec),'exact_at_entry':sum(r['fund']['exact_funding'] is not None for r in rec),
                     'prior_available':sum(r['fund']['prev_funding'] is not None for r in rec),
                     'prior_offset_hours':stat(offsets),
                     'prev24_event_counts':{str(n):sum(r['fund']['prev24_n']==n for r in rec) for n in sorted(set(r['fund']['prev24_n'] for r in rec))}},
         'notes':'exact_funding is descriptive only. prev_funding and prev24 metrics use strictly earlier settlements and are causal at entry.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
