#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, requests

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_VIDEO_IV_LIVE_FEASIBILITY"
BASE="https://eapi.binance.com"

def get(path,params=None):
    r=requests.get(BASE+path,params=params or {},timeout=20)
    r.raise_for_status()
    return r.json()

def main():
    ex=get("/eapi/v1/exchangeInfo")
    out={"as_of":datetime.now(timezone.utc).isoformat(),"underlyings":{}}
    for u in ["BNBUSDT","SOLUSDT"]:
        syms=[x for x in ex.get("optionSymbols",[]) if x.get("underlying")==u and x.get("status")=="TRADING"]
        if not syms:
            out["underlyings"][u]={"available":False}; continue
        idx=get("/eapi/v1/index",{"underlying":u})
        spot=float(idx["indexPrice"])
        minexp=min(int(x["expiryDate"]) for x in syms)
        near=[x for x in syms if int(x["expiryDate"])==minexp]
        near.sort(key=lambda x:abs(float(x["strikePrice"])-spot))
        atm=near[0]
        marks=get("/eapi/v1/mark",{"symbol":atm["symbol"]})
        mark=marks[0] if isinstance(marks,list) else marks
        out["underlyings"][u]={
          "available":True,
          "trading_symbol_count":len(syms),
          "index_price":spot,
          "nearest_expiry_ms":minexp,
          "atm_symbol":atm["symbol"],
          "strike":float(atm["strikePrice"]),
          "side":atm["side"],
          "bidIV":float(mark["bidIV"]),
          "askIV":float(mark["askIV"]),
          "markIV":float(mark["markIV"]),
          "delta":float(mark["delta"]),
          "gamma":float(mark["gamma"]),
          "vega":float(mark["vega"]),
        }
    (ROOT/f"{PFX}_Snapshot.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    ok=all(v.get("available") for v in out["underlyings"].values())
    status="BNB_B41_VIDEO_IV_LIVE_LAYER_AVAILABLE" if ok else "BNB_B41_VIDEO_IV_LIVE_LAYER_INCOMPLETE"
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    lines=["# BNB B41 — Video IV Live Feasibility","",f"**Status: {status}**",""]
    for u,v in out["underlyings"].items():
        lines += [f"## {u}",f"- trading options: {v.get('trading_symbol_count','—')}",
                  f"- index: {v.get('index_price','—')}",f"- ATM example: `{v.get('atm_symbol','—')}`",
                  f"- bidIV: {v.get('bidIV','—')}",f"- askIV: {v.get('askIV','—')}",f"- markIV: {v.get('markIV','—')}",""]
    lines += ["This proves only current data availability. It does not prove historical IV-surface coverage or a HOD/LOD edge."]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
