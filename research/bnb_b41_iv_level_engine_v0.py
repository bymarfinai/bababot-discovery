#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, math, statistics

ROOT=Path(__file__).resolve().parent.parent
DEFAULT_SNAPSHOT=ROOT/"results/bnb_b41_iv_level_v0/BNB_B41_IV_LEVEL_V0_ConnectorSnapshot.json"
PFX="BNB_B41_IV_LEVEL_V0"

CONFIG={
  "version":"IV_LEVEL_ENGINE_V0",
  "daily_history_n":60,
  "weekly_history_n":26,
  "target_expiry_days":[1,7,30],
  "min_expiry_hours":6,
  "surface_moneyness_abs_pct":0.10,
  "surface_abs_delta_min":0.15,
  "surface_abs_delta_max":0.85,
  "surface_askiv_min":0.05,
  "surface_askiv_max":5.0,
  "expected_move":"spot*askIV*sqrt(days/365)",
  "confluence_tolerance_pct":0.0075,
  "confluence_min_levels":2,
}

def q(a,p):
    x=sorted(float(v) for v in a if v is not None and math.isfinite(float(v)))
    if not x:return None
    pos=(len(x)-1)*p; lo=math.floor(pos); hi=math.ceil(pos)
    return x[lo] if lo==hi else x[lo]+(x[hi]-x[lo])*(pos-lo)

def mean(a):
    x=[float(v) for v in a if v is not None and math.isfinite(float(v))]
    return statistics.mean(x) if x else None

def rows(x):
    return list(x or [])

def range_stats(candles,now,n):
    cur=candles[-1]
    complete=[r for r in candles if int(r[6])<now][-n:]
    up=[(float(r[2])-float(r[1]))/float(r[1]) for r in complete]
    dn=[(float(r[1])-float(r[3]))/float(r[1]) for r in complete]
    return {
      "n":len(complete),"current_open":float(cur[1]),
      "median_up":q(up,.5),"median_down":q(dn,.5),
      "q75_up":q(up,.75),"q75_down":q(dn,.75),
    }

def expiry_choice(opts,target_days,now):
    exps=sorted(set(int(x["expiryDate"]) for x in opts if int(x["expiryDate"])>now+CONFIG["min_expiry_hours"]*3600_000))
    if not exps:
        exps=sorted(set(int(x["expiryDate"]) for x in opts if int(x["expiryDate"])>now))
    return min(exps,key=lambda t:abs((t-now)/86_400_000-target_days))

def iv_for_expiry(opts,marks,u,expiry,spot,now):
    z=[x for x in opts if x["underlying"]==u and int(x["expiryDate"])==expiry and x["symbol"] in marks]
    by={}
    for x in z: by.setdefault(float(x["strikePrice"]),[]).append(x)
    atm=None
    for k in sorted(by,key=lambda k:abs(k-spot)):
        c=next((x for x in by[k] if x["side"]=="CALL"),None)
        p=next((x for x in by[k] if x["side"]=="PUT"),None)
        if c and p:
            civ=float(marks[c["symbol"]]["askIV"]); piv=float(marks[p["symbol"]]["askIV"])
            if civ>0 and piv>0:
                atm={"strike":k,"call":c["symbol"],"put":p["symbol"],"callAskIV":civ,"putAskIV":piv,"avgAskIV":(civ+piv)/2}
                break
    surf=[]
    for x in z:
        m=marks[x["symbol"]]; k=float(x["strikePrice"]); iv=float(m["askIV"]); d=abs(float(m["delta"]))
        if abs(k/spot-1)<=CONFIG["surface_moneyness_abs_pct"] and CONFIG["surface_askiv_min"]<iv<CONFIG["surface_askiv_max"] and CONFIG["surface_abs_delta_min"]<=d<=CONFIG["surface_abs_delta_max"]:
            surf.append({"symbol":x["symbol"],"strike":k,"side":x["side"],"askIV":iv,"delta":float(m["delta"])})
    return {"expiry":expiry,"dte_days":(expiry-now)/86_400_000,"atmPair":atm,
            "surface_count":len(surf),"surface_avg_ask_iv":mean([x["askIV"] for x in surf]),"surface_symbols":surf}

def band(anchor,iv,days):
    move=anchor*iv*math.sqrt(days/365.0)
    return {"move":move,"lower":anchor-move,"upper":anchor+move}

def cluster(levels,spot):
    out=[]
    for l in sorted(levels,key=lambda x:x["price"]):
        hit=None
        for c in out:
            center=mean([m["price"] for m in c["members"]])
            if abs(l["price"]-center)/spot<=CONFIG["confluence_tolerance_pct"]:
                hit=c;break
        if hit: hit["members"].append(l)
        else: out.append({"members":[l]})
    ans=[]
    for c in out:
        center=mean([m["price"] for m in c["members"]])
        if len(c["members"])>=CONFIG["confluence_min_levels"]:
            ans.append({"center":center,"distance_pct":(center/spot-1)*100,"count":len(c["members"]),
                        "members":[m["name"] for m in c["members"]]})
    return sorted(ans,key=lambda x:(-x["count"],abs(x["distance_pct"])))

def build(s):
    now=int(s["as_of_ms"])
    opts=s["symbols"]; marks={x["symbol"]:x for x in s["marks"]}
    result={"as_of":s["as_of"],"method_version":CONFIG["version"],"config":CONFIG,"assets":{}}
    for u in ["BNBUSDT","SOLUSDT"]:
        spot=float(s["indices"][u]["indexPrice"])
        uopts=[x for x in opts if x["underlying"]==u and x["status"]=="TRADING"]
        ivs={}
        for d in CONFIG["target_expiry_days"]:
            e=expiry_choice(uopts,d,now)
            ivs[d]=iv_for_expiry(opts,marks,u,e,spot,now)
        ds=range_stats(s["daily"][u],now,CONFIG["daily_history_n"])
        ws=range_stats(s["weekly"][u],now,CONFIG["weekly_history_n"])
        daily=band(spot,ivs[1]["atmPair"]["avgAskIV"],1)
        weekly=band(spot,ivs[7]["atmPair"]["avgAskIV"],7)
        surface=band(spot,ivs[7]["surface_avg_ask_iv"],7)
        hd={"lower":ds["current_open"]*(1-ds["median_down"]),"upper":ds["current_open"]*(1+ds["median_up"]),
            "q75_lower":ds["current_open"]*(1-ds["q75_down"]),"q75_upper":ds["current_open"]*(1+ds["q75_up"])}
        hw={"lower":ws["current_open"]*(1-ws["median_down"]),"upper":ws["current_open"]*(1+ws["median_up"]),
            "q75_lower":ws["current_open"]*(1-ws["q75_down"]),"q75_upper":ws["current_open"]*(1+ws["q75_up"])}
        levels=[
          {"name":"IV_DAILY_LOWER","price":daily["lower"]},{"name":"IV_DAILY_UPPER","price":daily["upper"]},
          {"name":"IV_WEEKLY_LOWER","price":weekly["lower"]},{"name":"IV_WEEKLY_UPPER","price":weekly["upper"]},
          {"name":"SURFACE_WEEKLY_LOWER","price":surface["lower"]},{"name":"SURFACE_WEEKLY_UPPER","price":surface["upper"]},
          {"name":"HIST_DAILY_NORMAL_LOWER","price":hd["lower"]},{"name":"HIST_DAILY_NORMAL_UPPER","price":hd["upper"]},
          {"name":"HIST_WEEKLY_NORMAL_LOWER","price":hw["lower"]},{"name":"HIST_WEEKLY_NORMAL_UPPER","price":hw["upper"]},
          {"name":"HIST_WEEKLY_Q75_LOWER","price":hw["q75_lower"]},{"name":"HIST_WEEKLY_Q75_UPPER","price":hw["q75_upper"]},
        ]
        result["assets"][u]={"spot":spot,"iv":{"target_1d":ivs[1],"target_7d":ivs[7],"target_30d":ivs[30]},
          "range_stats":{"daily_60":ds,"weekly_26":ws},
          "bands":{"daily_atm_askiv":daily,"weekly_atm_askiv":weekly,"weekly_surface_askiv":surface,
                   "historical_daily":hd,"historical_weekly":hw},
          "levels":levels,"confluence_clusters_0_75pct":cluster(levels,spot)}
    sig=hashlib.sha256(json.dumps(CONFIG,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    result["engine_signature_sha256"]=sig
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",default=str(DEFAULT_SNAPSHOT))
    ap.add_argument("--out",default=str(ROOT/"results/bnb_b41_iv_level_v0/BNB_B41_IV_LEVEL_V0_OfflineReplay.json"))
    args=ap.parse_args()
    s=json.loads(Path(args.snapshot).read_text())
    r=build(s)
    Path(args.out).write_text(json.dumps(r,indent=2)+"\n")
    print("STATUS=BNB_B41_IV_LEVEL_V0_OFFLINE_REPLAY_COMPLETE")
    print("ENGINE_SIGNATURE_SHA256="+r["engine_signature_sha256"])
    for u,a in r["assets"].items():
        print(u,"spot",round(a["spot"],6),"clusters",json.dumps(a["confluence_clusters_0_75pct"]))

if __name__=="__main__":
    main()
