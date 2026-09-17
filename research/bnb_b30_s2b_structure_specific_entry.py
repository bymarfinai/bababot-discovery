#!/usr/bin/env python3
from __future__ import annotations

import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import bnb_b30_s1_structure_library as s1

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B30_S2B_STRUCTURE_SPECIFIC_ENTRY"
SYMBOL = "BNBUSDT"
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12
DEV_YEARS = [2022, 2023, 2024]
REF_YEARS = [2025, 2026]
HORIZONS = [30, 60, 120]
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
EXPECTED = {"S01": 8092, "S02": 797, "S03": 1577, "S04": 5109, "S05": 8542, "S06": 637, "S07": 1207, "S08": 5553}

POLICY_NAMES = {
    "S01": {"E0":"STRUCTURE_CLOSE","E1":"SWEEP_LEVEL_RETEST_HOLD","E2":"RECLAIM_CANDLE_HIGH_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S05": {"E0":"STRUCTURE_CLOSE","E1":"SWEEP_LEVEL_RETEST_REJECT","E2":"REJECT_CANDLE_LOW_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S04": {"E0":"STRUCTURE_CLOSE","E1":"BROKEN_LOW_RETEST_HOLD","E2":"RECLAIM_CANDLE_HIGH_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S08": {"E0":"STRUCTURE_CLOSE","E1":"BROKEN_HIGH_RETEST_REJECT","E2":"REJECT_CANDLE_LOW_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S02": {"E0":"STRUCTURE_CLOSE","E1":"HL_MID_RETEST_HOLD","E2":"CONTINUATION_HIGH_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S06": {"E0":"STRUCTURE_CLOSE","E1":"LH_MID_RETEST_REJECT","E2":"CONTINUATION_LOW_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S03": {"E0":"STRUCTURE_CLOSE","E1":"BREAKOUT_LEVEL_RETEST_HOLD","E2":"SECOND_EXPANSION_HIGH_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
    "S07": {"E0":"STRUCTURE_CLOSE","E1":"BREAKDOWN_LEVEL_RETEST_REJECT","E2":"SECOND_EXPANSION_LOW_BREAK","E3":"MICRO_BOS_3BAR","E4":"PULLBACK_RECLAIM"},
}


def wilson_lcb(hits: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0: return np.nan
    p = hits / n
    den = 1.0 + z*z/n
    center = p + z*z/(2*n)
    margin = z * sqrt((p*(1-p) + z*z/(4*n))/n)
    return (center - margin) / den


def month_urls(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    m = pd.Timestamp(start.year, start.month, 1, tz="UTC")
    em = pd.Timestamp(end.year, end.month, 1, tz="UTC")
    out = []
    while m <= em:
        ym = m.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return out


def fetch_month(url: str) -> pd.DataFrame:
    last = None
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=90, headers={"User-Agent":"bababot-b30-s2b/1.0"})
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names: raise RuntimeError(f"no csv in {url}")
                with zf.open(names[0]) as fh:
                    return pd.read_csv(fh, header=None, usecols=[0,1,2,3,4], names=["ts","open","high","low","close"])
        except Exception as exc:
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"failed {url}: {last}")


def load_raw(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    urls = month_urls(start, end)
    frames = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_month,u):u for u in urls}
        for fut in as_completed(futs):
            frames.append(fut.result())
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t/1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open","high","low","close"]: x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts", keep="last").sort_values("ts")
    x = x[(x.ts >= start.floor("D")) & (x.ts <= end.ceil("D"))].copy()
    x["ts"] = x["ts"] + BAR
    x = x.set_index("ts")[["open","high","low","close"]].astype(float)
    if x.empty or x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise RuntimeError("invalid raw index")
    expected = int((x.index[-1]-x.index[0])/BAR)+1
    coverage = len(x)/expected
    norm_hash = sha256(pd.util.hash_pandas_object(x.reset_index(), index=False).values.tobytes()).hexdigest()
    return x, {"files":len(urls),"rows":len(x),"coverage":coverage,"first":x.index[0],"last":x.index[-1],"normalized_sha256":norm_hash}


def integrity(fp: pd.DataFrame, raw: pd.DataFrame, events: pd.DataFrame) -> dict:
    idx = fp.index[(fp.index >= s1.START) & (fp.index <= s1.END)]
    idx = idx[idx.isin(raw.index) & (idx-BAR*3).isin(raw.index)]
    raw_ret = raw["close"].reindex(idx).to_numpy()/raw["close"].reindex(idx-BAR*3).to_numpy()-1.0
    imm = fp["ret_15"].reindex(idx).to_numpy(float)
    ret_diff = np.abs(raw_ret-imm)
    max_ret = float(np.nanmax(ret_diff)) if len(ret_diff) else np.inf

    eidx = pd.DatetimeIndex(events.event_ts.unique())
    eidx = eidx[eidx.isin(raw.index)]
    q = raw.reindex(eidx)
    rng = q.high-q.low
    raw_cl = ((q.close-q.low)-(q.high-q.close))/rng.replace(0.0,np.nan)
    imm_cl = fp["close_location"].reindex(eidx)
    dif = (raw_cl-imm_cl).abs().dropna()
    max_cl = float(dif.max()) if len(dif) else np.inf
    return {"ret15_n":len(idx),"max_ret15_diff":max_ret,"event_close_location_n":len(dif),"max_close_location_diff":max_cl}


def level_prior(raw_arrays, pos: int, side: str) -> float:
    high, low = raw_arrays[1], raw_arrays[2]
    if pos-12 < 0: return np.nan
    return float(np.max(high[pos-12:pos])) if side == "HIGH" else float(np.min(low[pos-12:pos]))


def entry_positions_for_event(sid: str, direction: str, pos: int, idx, o, h, l, c, seg) -> dict[str,int|None]:
    long = direction == "LONG"
    out = {"E0": pos, "E1": None, "E2": None, "E3": None, "E4": None}
    if pos < 15 or pos+12 >= len(idx): return out

    sh = float(np.max(h[pos-2:pos+1])); sl = float(np.min(l[pos-2:pos+1])); mid = (sh+sl)/2.0
    if sid in ("S01","S05"):
        lvl = level_prior((o,h,l,c), pos, "LOW" if long else "HIGH")
    elif sid in ("S03","S04","S07","S08"):
        p0 = pos-3
        lvl = level_prior((o,h,l,c), p0, "HIGH" if sid in ("S03","S08") else "LOW")
    else:
        lvl = mid

    adverse_extreme = None
    prev_close = c[pos]
    for j in range(pos+1, min(pos+13, len(idx))):
        if idx[j]-idx[j-1] != BAR: break
        if out["E1"] is None and np.isfinite(lvl):
            if long:
                if l[j] <= lvl and c[j] > lvl: out["E1"] = j
            else:
                if h[j] >= lvl and c[j] < lvl: out["E1"] = j
        if out["E2"] is None:
            if (long and c[j] > sh) or ((not long) and c[j] < sl): out["E2"] = j
        if out["E3"] is None and j >= 3:
            if long and c[j] > np.max(h[j-3:j]): out["E3"] = j
            if (not long) and c[j] < np.min(l[j-3:j]): out["E3"] = j
        adverse_now = (c[j] < prev_close-EPS) if long else (c[j] > prev_close+EPS)
        if adverse_now:
            adverse_extreme = h[j] if long else l[j]
        elif out["E4"] is None and adverse_extreme is not None:
            if long and c[j] > adverse_extreme: out["E4"] = j
            if (not long) and c[j] < adverse_extreme: out["E4"] = j
        prev_close = c[j]
    return out


def signed_forward(entry_pos: int|None, side: float, steps: int, idx, c, seg) -> float:
    if entry_pos is None: return np.nan
    end = entry_pos + steps
    if end >= len(idx) or seg[end] != seg[entry_pos] or idx[end]-idx[entry_pos] != steps*BAR: return np.nan
    r = side*(float(c[end])/float(c[entry_pos])-1.0)
    return 0.0 if abs(r) <= EPS else r


def build_entry_ledger(raw: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    idx = raw.index.to_numpy()
    o = raw.open.to_numpy(float); h=raw.high.to_numpy(float); l=raw.low.to_numpy(float); c=raw.close.to_numpy(float)
    # Tooling fix: compare actual timedeltas directly. In pandas 3.x, asi8 resolution
    # may differ from Timedelta.value resolution, which falsely marked every 5m bar as a gap.
    diffs = raw.index[1:] - raw.index[:-1]
    gaps = np.r_[True, np.asarray(diffs != BAR, dtype=bool)]
    seg = np.cumsum(gaps)
    posmap = {ts:i for i,ts in enumerate(raw.index)}
    rows=[]
    for ev in events.itertuples(index=False):
        pos = posmap.get(ev.event_ts)
        if pos is None: continue
        ep = entry_positions_for_event(ev.structure_id, ev.direction, pos, idx, o,h,l,c,seg)
        side = 1.0 if ev.direction=="LONG" else -1.0
        for pid,pname in POLICY_NAMES[ev.structure_id].items():
            p = ep[pid]
            rec={"structure_ts":ev.event_ts,"structure_id":ev.structure_id,"structure":ev.structure,"direction":ev.direction,"structure_year":ev.year,"policy_id":pid,"policy":pname,"entry_ts":pd.NaT if p is None else pd.Timestamp(idx[p])}
            for H in HORIZONS:
                sr=signed_forward(p,side,H//5,idx,c,seg)
                rec[f"signed_{H}"]=sr
                rec[f"hit_{H}"]=bool(np.isfinite(sr) and sr>EPS)
            rows.append(rec)
    return pd.DataFrame(rows)


def metric(z: pd.DataFrame, parent_n: int, years:list[int]) -> dict:
    v=z[z.signed_60.notna()].copy(); n=len(v); hits=int(v.hit_60.sum())
    out={"n":n,"parent_n":parent_n,"participation":n/parent_n if parent_n else np.nan,"hit_60":hits/n if n else np.nan,"wilson_60":wilson_lcb(hits,n),"median_signed_60":float(v.signed_60.median()) if n else np.nan,"hit_30":float(v.hit_30.mean()) if n else np.nan,"hit_120":float(v.hit_120.mean()) if n else np.nan}
    for y in years:
        q=v[v.structure_year==y]; out[f"n_{y}"]=len(q); out[f"hit_{y}"]=float(q.hit_60.mean()) if len(q) else np.nan
    return out


def development(ledger:pd.DataFrame, events:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for sid,name,direction,_ in [(a,b,c,EXPECTED[a]) for a,b,c in s1.DETECTORS]:
        parent=events[(events.structure_id==sid)&events.year.isin(DEV_YEARS)]
        for pid,pname in POLICY_NAMES[sid].items():
            z=ledger[(ledger.structure_id==sid)&(ledger.policy_id==pid)&ledger.structure_year.isin(DEV_YEARS)]
            m=metric(z,len(parent),DEV_YEARS); wh=min(m[f"hit_{y}"] for y in DEV_YEARS); aux=sum(m[f"hit_{H}"]>=.53 for H in (30,120))
            gate=(m["n"]>=100 and min(m[f"n_{y}"] for y in DEV_YEARS)>=20 and m["participation"]>=.25 and m["hit_60"]>=.55 and m["wilson_60"]>.50 and wh>=.52 and m["median_signed_60"]>0 and aux>=1)
            rows.append({"structure_id":sid,"structure":name,"direction":direction,"policy_id":pid,"policy":pname,**m,"worst_dev_hit":wh,"aux_ge53":aux,"dev_gate":gate})
    return pd.DataFrame(rows)


def select(dev:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for sid,name,direction in s1.DETECTORS:
        z=dev[(dev.structure_id==sid)&dev.dev_gate].copy()
        if not len(z): rows.append({"structure_id":sid,"structure":name,"direction":direction,"selection_status":"NO_STRUCTURE_SPECIFIC_ENTRY_FOUND"}); continue
        z=z.sort_values(["worst_dev_hit","wilson_60","hit_60","participation","policy_id"],ascending=[False,False,False,False,True]); r=z.iloc[0].to_dict(); r["selection_status"]="SELECTED_FOR_REFERENCE"; rows.append(r)
    return pd.DataFrame(rows)


def reference(ledger,events,sel)->pd.DataFrame:
    rows=[]
    for s in sel.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE": rows.append({"structure_id":s.structure_id,"structure":s.structure,"direction":s.direction,"status":"NO_STRUCTURE_SPECIFIC_ENTRY_FOUND"}); continue
        parent=events[(events.structure_id==s.structure_id)&events.year.isin(REF_YEARS)]
        z=ledger[(ledger.structure_id==s.structure_id)&(ledger.policy_id==s.policy_id)&ledger.structure_year.isin(REF_YEARS)]
        m=metric(z,len(parent),REF_YEARS); aux=sum(m[f"hit_{H}"]>=.52 for H in (30,120))
        gate=(m["n_2025"]>=15 and m["n_2026"]>=10 and m["participation"]>=.25 and m["hit_60"]>=.53 and m["hit_2025"]>.50 and m["hit_2026"]>.50 and m["median_signed_60"]>0 and aux>=1)
        rows.append({"structure_id":s.structure_id,"structure":s.structure,"direction":s.direction,"policy_id":s.policy_id,"policy":s.policy,**m,"aux_ge52":aux,"status":"STRUCTURE_ENTRY_PASS" if gate else "STRUCTURE_ENTRY_REJECT"})
    return pd.DataFrame(rows)


def pct(x): return "—" if pd.isna(x) else f"{100*x:.2f}%"

def render(rawdiag,integ,sel,ref):
    n=int((ref.status=="STRUCTURE_ENTRY_PASS").sum()); status="BNB_B30_S2B_STRUCTURE_SPECIFIC_ENTRIES_FOUND" if n else "BNB_B30_S2B_NO_STRUCTURE_ENTRY_PASSED"
    L=["# BNB B30-S2B — Structure-Specific 5m Entry Discovery Result","",f"**Status: {status}**","","S1 structures remain frozen. Each structure is evaluated only with its preregistered structure-specific 5m entry mechanisms. No TP/SL or economics is simulated.","","## Data integrity",f"- Raw 5m files: **{rawdiag['files']}**; rows: **{rawdiag['rows']:,}**; coverage: **{rawdiag['coverage']:.6%}**",f"- Normalized raw OHLC SHA256: `{rawdiag['normalized_sha256']}`",f"- Max raw-vs-A1 ret15 difference: **{integ['max_ret15_diff']:.12g}**",f"- Max event close-location difference: **{integ['max_close_location_diff']:.12g}**","","## Development-selected entry per structure","","| Structure | Selected entry | Dev N | Part. | +60 hit | Wilson | Worst dev era | Status |","|---|---|---:|---:|---:|---:|---:|---|"]
    for s in sel.itertuples(index=False):
        if s.selection_status!="SELECTED_FOR_REFERENCE": L.append(f"| {s.structure_id} {s.structure} | — | — | — | — | — | — | {s.selection_status} |")
        else: L.append(f"| {s.structure_id} {s.structure} | {s.policy_id} {s.policy} | {int(s.n)} | {pct(s.participation)} | {pct(s.hit_60)} | {pct(s.wilson_60)} | {pct(s.worst_dev_hit)} | SELECTED |")
    L += ["","## One-shot 2025–2026 reference","","| Structure | Frozen entry | Ref N | Part. | +60 hit | 2025 | 2026 | +30 | +120 | Status |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in ref.itertuples(index=False):
        if r.status=="NO_STRUCTURE_SPECIFIC_ENTRY_FOUND": L.append(f"| {r.structure_id} {r.structure} | — | — | — | — | — | — | — | — | {r.status} |")
        else: L.append(f"| {r.structure_id} {r.structure} | {r.policy_id} {r.policy} | {int(r.n)} | {pct(r.participation)} | {pct(r.hit_60)} | {pct(r.hit_2025)} | {pct(r.hit_2026)} | {pct(r.hit_30)} | {pct(r.hit_120)} | {r.status} |")
    L += ["","## Decision",f"**{status}**","",f"Frozen structure+entry pairs eligible for S3 economics: **{n}/8**.","S2B directional hit is not trading win rate. No live orders were placed."]
    return "\n".join(L)+"\n"


def main():
    fp, _ = s1.load_fp(); events=s1.build_events(fp)
    counts=events.structure_id.value_counts().to_dict()
    if any(counts.get(k,0)!=v for k,v in EXPECTED.items()): raise RuntimeError(f"S1 parent mismatch {counts}")
    raw_start=events.event_ts.min()-pd.Timedelta(hours=2); raw_end=events.event_ts.max()+pd.Timedelta(hours=3)
    raw,rawdiag=load_raw(raw_start,raw_end)
    if rawdiag["coverage"]<.995: raise RuntimeError(f"raw coverage too low {rawdiag}")
    integ=integrity(fp,raw,events)
    if integ["max_ret15_diff"]>5e-8 or integ["max_close_location_diff"]>5e-8: raise RuntimeError(f"raw/A1 identity mismatch {integ}")
    ledger=build_entry_ledger(raw,events); dev=development(ledger,events); sel=select(dev); ref=reference(ledger,events,sel); result=render(rawdiag,integ,sel,ref)
    dev.to_csv(ROOT/f"{PFX}_Development.csv",index=False); sel.to_csv(ROOT/f"{PFX}_Selected.csv",index=False); ref.to_csv(ROOT/f"{PFX}_Reference.csv",index=False); ledger.to_csv(ROOT/f"{PFX}_Entries.csv.gz",index=False,compression="gzip")
    (ROOT/f"{PFX}_Integrity.txt").write_text(str({**rawdiag,**integ})+"\n",encoding="utf-8"); (ROOT/f"{PFX}_Result.md").write_text(result,encoding="utf-8")
    status="BNB_B30_S2B_STRUCTURE_SPECIFIC_ENTRIES_FOUND" if (ref.status=="STRUCTURE_ENTRY_PASS").any() else "BNB_B30_S2B_NO_STRUCTURE_ENTRY_PASSED"; (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8"); print(result,flush=True)

if __name__=="__main__": main()
