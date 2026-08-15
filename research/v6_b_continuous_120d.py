#!/usr/bin/env python3
"""V6-B continuous 120d actual-liquidation scientific screen.

FROZEN BEFORE ENTITLED RESULTS.
Requires TARDIS_API_KEY. If absent, prints BLOCKED and exits successfully.

Hypothesis: an extreme one-sided forced-liquidation cascade is an exhaustion
signal and has a short-term reversal edge.

Definition:
- Binance USD-M actual liquidation records from Tardis normalized liquidations.
- 5m UTC bins; sell=long liquidation, buy=short liquidation.
- pair/side-specific rolling baseline: previous 7d (2016 completed 5m bins),
  current bar excluded.
- among nonzero same-side historical bins, require >=50 observations.
- shock if current same-side notional >= rolling 99th percentile of those nonzero
  bins and current same-side notional > opposite-side notional.
- first transition only for same-side consecutive shock state.
- long-liquidation shock -> reversal LONG; short-liquidation shock -> reversal SHORT.
- entry at shock 5m close; stop at shock bar extreme; target=1R.
- tracking begins next 5m bar; same-child TP+SL ambiguous excluded; 72h horizon.
- 120 fully resolvable UTC days; no S/R, EMA, OI, funding, Fib, or parameter sweep.

Gate: WR>=70%, resolved>=20, >=3/4 pairs each n>=5 and WR>50,
LONG+SHORT each n>=10 and WR>50, both 60d halves each n>=10 and WR>50.
Only a pass earns frozen 971d validation.
"""
import csv, gzip, io, json, os, statistics, urllib.request, urllib.error, zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone

PAIRS=["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
KEY=os.environ.get("TARDIS_API_KEY","").strip()
TBASE="https://datasets.tardis.dev/v1/binance-futures/liquidations"
KBASE="https://data.binance.vision/data/futures/um/daily/klines"
UA="bababot-v6-continuous/1.0"
BASE_BARS=7*24*12
HORIZON=72*12
Q=0.99


def request(url, key=None, timeout=60):
    h={"User-Agent":UA}
    if key: h["Authorization"]=f"Bearer {key}"
    return urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=timeout)


def days(lo,hi):
    d=lo.date()
    while d < hi.date():
        yield d
        d+=timedelta(days=1)


def load_liq(symbol,d):
    ds=d.isoformat(); y,m,dd=ds.split("-")
    url=f"{TBASE}/{y}/{m}/{dd}/{symbol}.csv.gz"
    out=[]
    with request(url,KEY) as r:
        txt=io.TextIOWrapper(gzip.GzipFile(fileobj=r),encoding="utf-8-sig",newline="")
        for x in csv.DictReader(txt):
            try:
                ts=datetime.fromtimestamp(int(x["timestamp"])/1_000_000.0,tz=timezone.utc)
                side=str(x["side"]).lower(); px=float(x["price"]); amt=float(x["amount"])
            except Exception: continue
            if side in ("buy","sell") and px>0 and amt>0:
                out.append((ts,side,px*amt))
    return out


def load_k(symbol,d):
    ds=d.isoformat(); url=f"{KBASE}/{symbol}/5m/{symbol}-5m-{ds}.zip"
    with request(url,timeout=30) as r: raw=r.read()
    z=zipfile.ZipFile(io.BytesIO(raw)); txt=z.read(z.namelist()[0]).decode("utf-8-sig")
    out=[]
    for r in csv.reader(io.StringIO(txt)):
        try:
            t=datetime.fromtimestamp(int(float(r[0]))/1000.0,tz=timezone.utc)
            o,h,l,c=map(float,(r[1],r[2],r[3],r[4]))
        except Exception: continue
        out.append({"t":t,"open":o,"high":h,"low":l,"close":c})
    return out


def floor5(t): return t.replace(minute=(t.minute//5)*5,second=0,microsecond=0)


def load_pair(symbol,lo,hi):
    rows=[]; missing=[]
    for d in days(lo,hi):
        try: kl=load_k(symbol,d)
        except Exception as e:
            missing.append({"date":d.isoformat(),"type":"klines","error":str(e)}); continue
        try: liq=load_liq(symbol,d)
        except Exception as e:
            missing.append({"date":d.isoformat(),"type":"liquidations","error":str(e)}); continue
        a=defaultdict(lambda:[0.0,0.0])
        for t,s,n in liq:
            b=floor5(t)
            if s=="sell": a[b][0]+=n
            else: a[b][1]+=n
        for k in kl:
            x=a[k["t"]]
            rows.append({**k,"long_liq":x[0],"short_liq":x[1]})
    rows.sort(key=lambda x:x["t"])
    return rows,missing


def quantile(xs,q):
    ys=sorted(xs); n=len(ys)
    if not n:return None
    p=(n-1)*q; lo=int(p); hi=min(n-1,lo+1); f=p-lo
    return ys[lo]*(1-f)+ys[hi]*f


def resolve(rows,i,e):
    d=e["dir"]; sl=e["stop"]; tp=e["target"]
    for b in rows[i+1:min(len(rows),i+1+HORIZON)]:
        ht=(b["high"]>=tp) if d>0 else (b["low"]<=tp)
        hs=(b["low"]<=sl) if d>0 else (b["high"]>=sl)
        if ht and hs:return "AMBIGUOUS",b["t"]
        if ht:return "WIN",b["t"]
        if hs:return "LOSS",b["t"]
    return "CENSORED",None


def detect(symbol,rows,sample_start,sample_end):
    ev=[]; prev=None
    for i in range(BASE_BARS,len(rows)):
        b=rows[i]
        hist=rows[i-BASE_BARS:i]
        ln=[x["long_liq"] for x in hist if x["long_liq"]>0]
        sn=[x["short_liq"] for x in hist if x["short_liq"]>0]
        candidates=[]
        if len(ln)>=50:
            ql=quantile(ln,Q)
            if b["long_liq"]>0 and b["long_liq"]>=ql and b["long_liq"]>b["short_liq"]:
                candidates.append(("LONG_LIQ",b["long_liq"]/ql if ql else None,1,ql))
        if len(sn)>=50:
            qs=quantile(sn,Q)
            if b["short_liq"]>0 and b["short_liq"]>=qs and b["short_liq"]>b["long_liq"]:
                candidates.append(("SHORT_LIQ",b["short_liq"]/qs if qs else None,-1,qs))
        active=max(candidates,key=lambda x:(x[1] or 0)) if candidates else None
        name=active[0] if active else None
        if active and name!=prev and sample_start<=b["t"]<sample_end:
            name,mult,d,qv=active; entry=b["close"]; stop=b["low"] if d>0 else b["high"]
            risk=(entry-stop) if d>0 else (stop-entry)
            if risk>0:
                e={"symbol":symbol,"signal_time":b["t"],"shock":name,
                   "trade_direction":"LONG" if d>0 else "SHORT","dir":d,
                   "entry":entry,"stop":stop,"target":entry+d*risk,
                   "risk_pct":100*risk/entry,"shock_notional":b["long_liq"] if d>0 else b["short_liq"],
                   "rolling_q99":qv,"shock_multiple_q99":mult}
                out,ot=resolve(rows,i,e); e["outcome"]=out;e["outcome_time"]=ot;e.pop("dir")
                ev.append(e)
        prev=name
    return ev


def stat(es):
    r=[e for e in es if e["outcome"] in ("WIN","LOSS")]; w=sum(e["outcome"]=="WIN" for e in r)
    return {"events":len(es),"resolved":len(r),"wins":w,"losses":len(r)-w,
            "wr_pct":round(100*w/len(r),2) if r else None,
            "ambiguous":sum(e["outcome"]=="AMBIGUOUS" for e in es),
            "censored":sum(e["outcome"]=="CENSORED" for e in es)}


def main():
    if not KEY:
        print("V6_B_CONTINUOUS_RESULT",json.dumps({"phase":"V6-B","status":"BLOCKED_NO_TARDIS_API_KEY",
              "scientific_definition_frozen":True,"required_secret":"TARDIS_API_KEY"},separators=(",",":")))
        return
    today=datetime.combine(datetime.now(timezone.utc).date(),datetime.min.time(),tzinfo=timezone.utc)
    sample_end=today-timedelta(days=3); sample_start=sample_end-timedelta(days=120)
    load_start=sample_start-timedelta(days=7); load_end=today
    all_ev=[]; coverage={}; errors={}
    for p in PAIRS:
        rows,miss=load_pair(p,load_start,load_end)
        coverage[p]={"rows_5m":len(rows),"missing":miss,"events":0}
        if miss:
            errors[p]=f"continuous coverage incomplete: {len(miss)} missing day/data items"
            continue
        ev=detect(p,rows,sample_start,sample_end); coverage[p]["events"]=len(ev); all_ev+=ev
    if errors:
        print("V6_B_CONTINUOUS_RESULT",json.dumps({"phase":"V6-B","status":"FAIL_INCOMPLETE_CONTINUOUS_COVERAGE",
              "sample_start":sample_start.isoformat(),"sample_end":sample_end.isoformat(),"coverage":coverage,"errors":errors},default=str,separators=(",",":")))
        return
    overall=stat(all_ev); by_pair={p:stat([e for e in all_ev if e["symbol"]==p]) for p in PAIRS}
    by_dir={d:stat([e for e in all_ev if e["trade_direction"]==d]) for d in ("LONG","SHORT")}
    cut=sample_start+timedelta(days=60)
    by_time={"first_60d":stat([e for e in all_ev if e["signal_time"]<cut]),"last_60d":stat([e for e in all_ev if e["signal_time"]>=cut])}
    pair_ok=sum(1 for z in by_pair.values() if z["resolved"]>=5 and (z["wr_pct"] or 0)>50)
    dir_ok=all(z["resolved"]>=10 and (z["wr_pct"] or 0)>50 for z in by_dir.values())
    time_ok=all(z["resolved"]>=10 and (z["wr_pct"] or 0)>50 for z in by_time.values())
    earns=overall["resolved"]>=20 and (overall["wr_pct"] or 0)>=70 and pair_ok>=3 and dir_ok and time_ok
    out={"phase":"V6-B","status":"CONTINUOUS_ACTUAL_LIQUIDATION_120D_SCREEN",
         "frozen_definition":{"baseline":"previous 7d, nonzero same-side 5m liquidation bins","shock":"current >= rolling 99th percentile and dominates opposite side","entry":"reversal at shock close","stop":"shock extreme","target":"1R","horizon":"72h","sweep":False},
         "sample_start":sample_start.isoformat(),"sample_end":sample_end.isoformat(),"coverage":coverage,
         "overall":overall,"by_pair":by_pair,"by_direction":by_dir,"by_time":by_time,
         "gate":{"pairs_passing":pair_ok,"direction_check":dir_ok,"time_check":time_ok,"earns_971d_validation":earns},"errors":errors}
    print("V6_B_CONTINUOUS_RESULT",json.dumps(out,default=str,separators=(",",":")))

if __name__=="__main__": main()
