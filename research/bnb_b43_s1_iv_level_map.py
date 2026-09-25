#!/usr/bin/env python3
from __future__ import annotations
import json, math
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/"results/bnb_b43_s1/BNB_B43_S1_LIVE_IV_SNAPSHOT.json"
PFX="BNB_B43_S1_IV_LEVEL_MAP"

def main():
    d=json.loads(SRC.read_text())
    s=float(d["index_price"])
    now=int(d["observation_server_time_ms"])
    rows=[]
    for r in d["expiries"]:
        exp=int(r["expiry_ms"])
        t=max(exp-now,0)/(365*86400000)
        iv=(float(r["call_askIV"])+float(r["put_askIV"]))/2
        em=s*iv*math.sqrt(t)
        calc={
          "expiry_iso":r["expiry_iso"],
          "atm_strike":float(r["atm_strike"]),
          "avg_askIV":iv,
          "days_to_expiry":max(exp-now,0)/86400000,
          "lower_0_5sigma":s-.5*em,
          "upper_0_5sigma":s+.5*em,
          "lower_1sigma":s-em,
          "upper_1sigma":s+em,
          "expected_move":em,
        }
        # deterministic parity against connector-side snapshot calculation
        for k,src in [
          ("lower_0_5sigma","lower_ask_0_5sigma"),("upper_0_5sigma","upper_ask_0_5sigma"),
          ("lower_1sigma","lower_ask_1sigma"),("upper_1sigma","upper_ask_1sigma"),
          ("expected_move","expected_move_ask_1sigma")]:
            if abs(calc[k]-float(r[src]))>1e-9:
                raise RuntimeError(f"parity mismatch {r['expiry_iso']} {k}")
        if not (calc["lower_1sigma"]<calc["lower_0_5sigma"]<s<calc["upper_0_5sigma"]<calc["upper_1sigma"]):
            raise RuntimeError("band ordering failure")
        rows.append(calc)
    status="BNB_B43_S1_LIVE_IV_LEVEL_MAP_READY" if len(rows)>=3 else "BNB_B43_S1_LIVE_IV_LEVEL_MAP_NOT_READY"
    sig=sha256(json.dumps({
      "source_observation":d["observation_server_time_ms"],
      "underlying":d["underlying"],
      "formula":"S*avg(callAskIV,putAskIV)*sqrt(T_years)",
      "atm_rule":"nearest strike with finite positive call+put askIV",
      "levels":["0.5sigma","1sigma"]
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()
    lines=[
      "# BNB B43-S1 — Live Options-IV HOD/LOD Level Map Result","",
      f"**Status: {status}**","",
      f"Observation: **{d['observation_server_time_iso']}**",
      f"BNB index: **{s:.4f}**",
      f"Signature: `{sig}`","",
      "| Expiry | DTE | ATM | Avg Ask IV | -0.5σ | +0.5σ | -1σ | +1σ |",
      "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in rows:
        lines.append(f"| {r['expiry_iso']} | {r['days_to_expiry']:.3f}d | {r['atm_strike']:.0f} | {r['avg_askIV']:.4f} | {r['lower_0_5sigma']:.2f} | {r['upper_0_5sigma']:.2f} | {r['lower_1sigma']:.2f} | {r['upper_1sigma']:.2f} |")
    lines += ["","## Interpretation",
      "This validates deterministic construction of a live IV-derived projected level map.",
      "It does not validate HOD/LOD prediction or trading edge yet.",
      "Exact historical Binance askIV replay was not available from the tested official expired-contract paths.",
      "The next legitimate test is forward evaluation of already-frozen snapshots, or a new independent historical options source."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n")
    (ROOT/f"{PFX}_Freeze.txt").write_text(f"S1_SIGNATURE_SHA256={sig}\nOBSERVATION={d['observation_server_time_iso']}\n")
    print("\n".join(lines))

if __name__=="__main__":
    main()
