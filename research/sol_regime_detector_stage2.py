#!/usr/bin/env python3
from __future__ import annotations

import io
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Result.md"
OUT_FEATURES = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Features.csv"
OUT_SWINGS_1H = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Swings1H.csv"
OUT_SWINGS_4H = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Swings4H.csv"
OUT_AUDIT = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Audit.csv"
OUT_STATUS = ROOT / "SOL_REGIME_DETECTOR_STAGE2_Status.txt"

SYMBOL = "SOLUSDT"
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START = pd.Timestamp("2022-06-01T00:00:00Z")
OUTPUT_START = pd.Timestamp("2023-01-01T00:00:00Z")
END = pd.Timestamp("2026-09-01T00:00:00Z")

EMA_FAST = 7
EMA_SLOW = 20
ATR_N = 14
ATR_PCTL_N = 168

S1_LEFT = 5
S1_RIGHT = 5
S1_ATR = 0.50
S4_LEFT = 3
S4_RIGHT = 3
S4_ATR = 0.50

ROLLS = (3,6,12,24)
BALANCE_WINDOWS = (12,24)

PREFIX_CHECKPOINTS = [
    pd.Timestamp("2023-06-30T23:00:00Z"),
    pd.Timestamp("2024-06-30T23:00:00Z"),
    pd.Timestamp("2025-06-30T23:00:00Z"),
    pd.Timestamp("2026-06-30T23:00:00Z"),
]


def month_urls():
    cur = pd.Timestamp(FETCH_START.year, FETCH_START.month, 1, tz="UTC")
    end = pd.Timestamp(END.year, END.month, 1, tz="UTC")
    out=[]
    while cur < end:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out


def fetch_one(url: str):
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-sol-regime-stage2/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,header=None,usecols=[0,1,2,3,4,5],
                names=["ts","open","high","low","close","volume"]
            )


def load5():
    frames=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs=[ex.submit(fetch_one,u) for u in month_urls()]
        for fut in as_completed(futs):
            x=fut.result()
            if x is not None and len(x):
                frames.append(x)
    if not frames:
        raise RuntimeError("No SOLUSDT 5m data")
    x=pd.concat(frames,ignore_index=True)
    t=pd.to_numeric(x.ts,errors="coerce")
    t=np.where(t > 100_000_000_000_000, t/1000.0, t)
    x["ts"]=pd.to_datetime(t,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=FETCH_START)&(x.ts<END)].set_index("ts")
    expected=int((x.index[-1]-x.index[0])/pd.Timedelta(minutes=5))+1
    coverage=len(x)/expected
    return x,coverage


def aggregate(x5: pd.DataFrame, rule: str, expected_count: int):
    g=x5.resample(rule,label="left",closed="left")
    out=g.agg(
        open=("open","first"), high=("high","max"), low=("low","min"),
        close=("close","last"), volume=("volume","sum"), n5=("close","count")
    )
    out=out[out.n5==expected_count].copy()
    return out


def ema(s,n):
    return s.ewm(span=n,adjust=False,min_periods=n).mean()


def atr(df,n=14):
    prev=df.close.shift(1)
    tr=pd.concat([
        df.high-df.low,
        (df.high-prev).abs(),
        (df.low-prev).abs(),
    ],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()


def efficiency(close: pd.Series,n:int):
    travel=close.diff().abs().rolling(n).sum()
    net=(close-close.shift(n)).abs()
    return net/travel.replace(0,np.nan)


def signed_close_fracs(close: pd.Series,n:int):
    d=close.diff()
    up=(d>0).astype(float).rolling(n).mean()
    dn=(d<0).astype(float).rolling(n).mean()
    return up,dn


def mean_cross_count(close: pd.Series, mean: pd.Series,n:int):
    side=np.sign(close-mean)
    cross=((side*side.shift(1))<0).astype(float)
    return cross.rolling(n).sum()


def pair_overlap(high: pd.Series,low: pd.Series):
    prev_h=high.shift(1); prev_l=low.shift(1)
    inter=(pd.concat([high,prev_h],axis=1).min(axis=1)-pd.concat([low,prev_l],axis=1).max(axis=1)).clip(lower=0)
    denom=pd.concat([high-low,prev_h-prev_l],axis=1).min(axis=1).replace(0,np.nan)
    return (inter/denom).clip(0,1)


def range_path_ratio(df: pd.DataFrame,n:int):
    rr=df.high.rolling(n).max()-df.low.rolling(n).min()
    path=df.close.diff().abs().rolling(n).sum()
    return rr/path.replace(0,np.nan)


def rolling_percentile_rank(s: pd.Series,n:int):
    def f(v):
        if len(v)<2 or np.isnan(v[-1]):
            return np.nan
        a=v[~np.isnan(v)]
        if len(a)<2:
            return np.nan
        return float(np.mean(a <= v[-1]))
    return s.rolling(n,min_periods=max(24,n//4)).apply(f,raw=True)


@dataclass
class Swing:
    typ: str
    pivot_i: int
    confirm_i: int
    pivot_ts: pd.Timestamp
    confirm_ts: pd.Timestamp
    price: float
    atr_at_pivot: float
    prominence_atr: float


class CausalSwingEngine:
    def __init__(self,left:int,right:int,atr_mult:float):
        self.left=left; self.right=right; self.atr_mult=atr_mult
        self.raw=[]
        self.seq=[]
        self._raw_ids=set()
        self.prot_low=None
        self.prot_low_ts=None
        self.prot_high=None
        self.prot_high_ts=None

    def _record_raw(self,s:Swing):
        key=(s.typ,s.pivot_ts)
        if key in self._raw_ids:
            raise RuntimeError(f"duplicate raw swing identity {key}")
        self._raw_ids.add(key)
        self.raw.append(s)

    def _refresh_protected_from_tail(self):
        if len(self.seq) < 3:
            return
        a,b,c=self.seq[-3],self.seq[-2],self.seq[-1]
        if a.typ=="H" and b.typ=="L" and c.typ=="H" and c.price>a.price:
            self.prot_low=b.price
            self.prot_low_ts=b.pivot_ts
        if a.typ=="L" and b.typ=="H" and c.typ=="L" and c.price<a.price:
            self.prot_high=b.price
            self.prot_high_ts=b.pivot_ts

    def _accept(self,s:Swing):
        changed=False
        if not self.seq:
            self.seq.append(s)
            changed=True
        else:
            last=self.seq[-1]
            if last.typ != s.typ:
                if s.pivot_i > last.pivot_i:
                    self.seq.append(s)
                    changed=True
            else:
                more_extreme = (s.price > last.price) if s.typ=="H" else (s.price < last.price)
                if more_extreme and s.pivot_i > last.pivot_i:
                    self.seq[-1]=s
                    changed=True
        if changed:
            self._refresh_protected_from_tail()

    def update(self,i:int,df:pd.DataFrame,atr_s:pd.Series):
        cand=i-self.right
        if cand < self.left or cand < 0:
            return []
        if cand+self.right != i:
            raise RuntimeError("confirmation index mismatch")
        a=cand-self.left; b=cand+self.right+1
        H=df.high.to_numpy(float); L=df.low.to_numpy(float)
        av=float(atr_s.iloc[cand]) if pd.notna(atr_s.iloc[cand]) else np.nan
        if not np.isfinite(av) or av<=0:
            return []
        wh=H[a:b]; wl=L[a:b]
        hp=H[cand]; lp=L[cand]
        high_prom=(hp-float(np.min(wl)))/av
        low_prom=(float(np.max(wh))-lp)/av
        candidates=[]
        if hp >= float(np.max(wh)) and high_prom >= self.atr_mult:
            candidates.append(Swing("H",cand,i,df.index[cand],df.index[i],hp,av,high_prom))
        if lp <= float(np.min(wl)) and low_prom >= self.atr_mult:
            candidates.append(Swing("L",cand,i,df.index[cand],df.index[i],lp,av,low_prom))
        for s in candidates:
            self._record_raw(s)
        if not candidates:
            return []
        if len(candidates)==1:
            chosen=candidates[0]
        else:
            if self.seq:
                opp="L" if self.seq[-1].typ=="H" else "H"
                chosen=next((x for x in candidates if x.typ==opp),None)
                if chosen is None:
                    chosen=max(candidates,key=lambda x:x.prominence_atr)
            else:
                chosen=max(candidates,key=lambda x:x.prominence_atr)
        self._accept(chosen)
        return candidates

    def state(self,close:float,atr_now:float):
        # Accepted sequence is alternating, so the last four pivots are sufficient
        # for the latest two highs/lows and current structural sequence.
        tail=self.seq[-4:]
        highs=[s for s in tail if s.typ=="H"]
        lows=[s for s in tail if s.typ=="L"]

        hh=np.nan
        hl=np.nan
        if len(highs)>=2 and atr_now>0:
            hh=(highs[-1].price-highs[-2].price)/atr_now
        if len(lows)>=2 and atr_now>0:
            hl=(lows[-1].price-lows[-2].price)/atr_now

        if len(highs)>=2 and len(lows)>=2:
            bull=(highs[-1].price>highs[-2].price and lows[-1].price>lows[-2].price)
            bear=(highs[-1].price<highs[-2].price and lows[-1].price<lows[-2].price)
            st="BULL_SEQ" if bull else ("BEAR_SEQ" if bear else "MIXED")
        else:
            st="INSUFFICIENT"

        if self.seq:
            if self.seq[-1].typ=="H":
                last_h=self.seq[-1].price
                last_l=self.seq[-2].price if len(self.seq)>=2 else np.nan
            else:
                last_l=self.seq[-1].price
                last_h=self.seq[-2].price if len(self.seq)>=2 else np.nan
        else:
            last_h=np.nan
            last_l=np.nan

        return {
            "structure_state":st,
            "seq_len":len(self.seq),
            "last_swing_high":last_h,
            "last_swing_low":last_l,
            "high_delta_atr":hh,
            "low_delta_atr":hl,
            "protected_low":self.prot_low,
            "protected_low_ts":self.prot_low_ts,
            "protected_high":self.prot_high,
            "protected_high_ts":self.prot_high_ts,
            "break_above_last_high":bool(np.isfinite(last_h) and close>last_h),
            "break_below_last_low":bool(np.isfinite(last_l) and close<last_l),
            "protected_low_dist_atr":((close-self.prot_low)/atr_now if self.prot_low is not None and atr_now>0 else np.nan),
            "protected_high_dist_atr":((self.prot_high-close)/atr_now if self.prot_high is not None and atr_now>0 else np.nan),
        }

def base_features(df:pd.DataFrame,left:int,right:int,atr_mult:float,prefix:str):
    z=df.copy()
    z["ema7"]=ema(z.close,EMA_FAST)
    z["ema20"]=ema(z.close,EMA_SLOW)
    z["atr14"]=atr(z,ATR_N)

    eng=CausalSwingEngine(left,right,atr_mult)
    rows=[]
    H=z.high.to_numpy(float); L=z.low.to_numpy(float)
    for i in range(len(z)):
        raw_now=eng.update(i,z,z.atr14)
        av=float(z.atr14.iloc[i]) if pd.notna(z.atr14.iloc[i]) else np.nan
        st=eng.state(float(z.close.iloc[i]),av if np.isfinite(av) else 0.0)
        st["raw_high_confirm"]=any(s.typ=="H" for s in raw_now)
        st["raw_low_confirm"]=any(s.typ=="L" for s in raw_now)
        rows.append(st)
    sf=pd.DataFrame(rows,index=z.index)

    out=pd.DataFrame(index=z.index)
    out[prefix+"ema_spread"]=(z.ema7-z.ema20)/z.close
    out[prefix+"ema7_slope3_price"]=(z.ema7-z.ema7.shift(3))/z.close
    out[prefix+"ema20_slope3_price"]=(z.ema20-z.ema20.shift(3))/z.close
    out[prefix+"ema7_slope3_atr"]=(z.ema7-z.ema7.shift(3))/z.atr14
    out[prefix+"ema20_slope3_atr"]=(z.ema20-z.ema20.shift(3))/z.atr14
    out[prefix+"close_ema7_dist"]=(z.close-z.ema7)/z.close
    out[prefix+"close_ema20_dist"]=(z.close-z.ema20)/z.close
    out[prefix+"atr_norm"]=z.atr14/z.close
    out[prefix+"atr_vs_med72"]=z.atr14/z.atr14.rolling(72).median()
    out[prefix+"atr_pct168"]=rolling_percentile_rank(z.atr14,ATR_PCTL_N)

    for n in ROLLS:
        out[prefix+f"ret_{n}"]=z.close/z.close.shift(n)-1.0
        out[prefix+f"eff_{n}"]=efficiency(z.close,n)
        up,dn=signed_close_fracs(z.close,n)
        out[prefix+f"upfrac_{n}"]=up
        out[prefix+f"dnfrac_{n}"]=dn

    ov=pair_overlap(z.high,z.low)
    for n in BALANCE_WINDOWS:
        out[prefix+f"mean_cross_{n}"]=mean_cross_count(z.close,z.ema20,n)
        out[prefix+f"overlap_{n}"]=ov.rolling(n).mean()
        out[prefix+f"range_path_{n}"]=range_path_ratio(z,n)

    rename={
        "structure_state":prefix+"structure_state",
        "seq_len":prefix+"swing_seq_len",
        "last_swing_high":prefix+"last_swing_high",
        "last_swing_low":prefix+"last_swing_low",
        "high_delta_atr":prefix+"high_delta_atr",
        "low_delta_atr":prefix+"low_delta_atr",
        "protected_low":prefix+"protected_low",
        "protected_low_ts":prefix+"protected_low_ts",
        "protected_high":prefix+"protected_high",
        "protected_high_ts":prefix+"protected_high_ts",
        "break_above_last_high":prefix+"break_above_last_high",
        "break_below_last_low":prefix+"break_below_last_low",
        "protected_low_dist_atr":prefix+"protected_low_dist_atr",
        "protected_high_dist_atr":prefix+"protected_high_dist_atr",
        "raw_high_confirm":prefix+"raw_high_confirm",
        "raw_low_confirm":prefix+"raw_low_confirm",
    }
    out=out.join(sf.rename(columns=rename))

    raw=pd.DataFrame([{
        "type":s.typ,"pivot_i":s.pivot_i,"confirm_i":s.confirm_i,
        "pivot_ts":s.pivot_ts,"confirm_ts":s.confirm_ts,
        "price":s.price,"atr_at_pivot":s.atr_at_pivot,
        "prominence_atr":s.prominence_atr,
    } for s in eng.raw])
    seq=eng.seq
    return out,raw,seq


def build_feature_engine(x5:pd.DataFrame):
    h1=aggregate(x5,"1h",12)
    h4=aggregate(x5,"4h",48)

    f1,raw1,seq1=base_features(h1,S1_LEFT,S1_RIGHT,S1_ATR,"h1_")
    f4,raw4,seq4=base_features(h4,S4_LEFT,S4_RIGHT,S4_ATR,"h4_")

    # Keep only the 4H feature subset reserved by Stage 1.
    h4_keep=[
        "h4_ema_spread","h4_ema7_slope3_price","h4_ema20_slope3_price",
        "h4_close_ema20_dist","h4_ret_3","h4_ret_6","h4_eff_6",
        "h4_structure_state","h4_high_delta_atr","h4_low_delta_atr",
        "h4_protected_low_dist_atr","h4_protected_high_dist_atr",
        "h4_break_above_last_high","h4_break_below_last_low",
    ]
    ctx=f4[h4_keep].copy()
    ctx["h4_source_open_ts"]=ctx.index
    ctx["h4_source_close_ts"]=ctx.index+pd.Timedelta(hours=4)
    ctx=ctx.reset_index(drop=True).sort_values("h4_source_close_ts")

    feats=f1.copy()
    feats["decision_time"]=feats.index+pd.Timedelta(hours=1)
    left=feats.reset_index().rename(columns={"ts":"bar_open_ts","index":"bar_open_ts"}).sort_values("decision_time")
    merged=pd.merge_asof(
        left,ctx,left_on="decision_time",right_on="h4_source_close_ts",
        direction="backward",allow_exact_matches=True
    )
    merged=merged.set_index("bar_open_ts")
    merged["partition"]=np.select(
        [
            merged.index < pd.Timestamp("2025-01-01",tz="UTC"),
            merged.index < pd.Timestamp("2026-01-01",tz="UTC"),
        ],
        ["DEV_2023_24","HOLDOUT_2025"],
        default="FINAL_2026"
    )
    return merged,h1,h4,raw1,raw4,seq1,seq4


def alternating(seq):
    return all(seq[i].typ != seq[i-1].typ for i in range(1,len(seq)))


def prefix_audit(x5,full_feats):
    cols=[
        "h1_ema_spread","h1_ema20_slope3_price","h1_atr_norm",
        "h1_ret_24","h1_eff_24","h1_mean_cross_24","h1_overlap_24",
        "h1_range_path_24","h1_structure_state","h1_high_delta_atr",
        "h1_low_delta_atr","h1_protected_low_dist_atr","h1_protected_high_dist_atr",
        "h4_ema_spread","h4_ret_6","h4_eff_6","h4_structure_state",
        "h4_high_delta_atr","h4_low_delta_atr",
    ]
    rows=[]
    for cp in PREFIX_CHECKPOINTS:
        decision=cp+pd.Timedelta(hours=1)
        px=x5[x5.index < decision].copy()
        pf,*_=build_feature_engine(px)
        if cp not in pf.index or cp not in full_feats.index:
            rows.append({"checkpoint":cp,"pass":False,"max_abs_numeric_diff":np.nan,"string_mismatch":999})
            continue
        a=full_feats.loc[cp]; b=pf.loc[cp]
        maxdiff=0.0; sm=0
        for c in cols:
            av=a.get(c,np.nan); bv=b.get(c,np.nan)
            if isinstance(av,str) or isinstance(bv,str):
                if str(av)!=str(bv): sm+=1
            else:
                if pd.isna(av) and pd.isna(bv): continue
                if pd.isna(av) != pd.isna(bv):
                    maxdiff=np.inf; continue
                maxdiff=max(maxdiff,abs(float(av)-float(bv)))
        rows.append({"checkpoint":cp,"pass":bool(maxdiff<=1e-10 and sm==0),"max_abs_numeric_diff":maxdiff,"string_mismatch":sm})
    return pd.DataFrame(rows)


def main():
    x5,coverage=load5()
    feats,h1,h4,raw1,raw4,seq1,seq4=build_feature_engine(x5)

    # Output feature window only.
    out=feats[(feats.index>=OUTPUT_START)&(feats.index<END)].copy()
    out.to_csv(OUT_FEATURES,index_label="bar_open_ts")
    raw1.to_csv(OUT_SWINGS_1H,index=False)
    raw4.to_csv(OUT_SWINGS_4H,index=False)

    audit=[]
    def add(name,ok,value,detail=""):
        audit.append({"audit":name,"pass":bool(ok),"value":value,"detail":detail})

    add("raw_5m_coverage",coverage>=0.995,coverage,"must be >=0.995")
    add("all_exported_1h_complete",bool((h1.loc[(h1.index>=OUTPUT_START)&(h1.index<END),"n5"]==12).all()),
        int((h1.loc[(h1.index>=OUTPUT_START)&(h1.index<END),"n5"]!=12).sum()),"bad 1H bars")
    used4=pd.to_datetime(out.h4_source_open_ts.dropna().unique(),utc=True)
    h4_used=h4.loc[h4.index.intersection(used4)] if len(used4) else h4.iloc[0:0]
    add("all_used_4h_complete",bool(len(h4_used)>0 and (h4_used.n5==48).all()),
        int((h4_used.n5!=48).sum()) if len(h4_used) else -1,"bad used 4H bars")

    add("1h_accepted_sequence_alternates",alternating(seq1),len(seq1))
    add("4h_accepted_sequence_alternates",alternating(seq4),len(seq4))

    uid1=raw1[["type","pivot_ts"]].astype(str).agg("|".join,axis=1) if len(raw1) else pd.Series(dtype=str)
    uid4=raw4[["type","pivot_ts"]].astype(str).agg("|".join,axis=1) if len(raw4) else pd.Series(dtype=str)
    add("1h_raw_event_identity_unique",not uid1.duplicated().any(),int(uid1.duplicated().sum()))
    add("4h_raw_event_identity_unique",not uid4.duplicated().any(),int(uid4.duplicated().sum()))

    d1=(raw1.confirm_i-raw1.pivot_i) if len(raw1) else pd.Series(dtype=float)
    d4=(raw4.confirm_i-raw4.pivot_i) if len(raw4) else pd.Series(dtype=float)
    add("1h_confirmation_delay_exact",bool(len(d1)>0 and (d1==S1_RIGHT).all()),sorted(d1.unique().tolist()) if len(d1) else [])
    add("4h_confirmation_delay_exact",bool(len(d4)>0 and (d4==S4_RIGHT).all()),sorted(d4.unique().tolist()) if len(d4) else [])

    causal4=(pd.to_datetime(out.h4_source_close_ts,utc=True)<=pd.to_datetime(out.decision_time,utc=True)) | out.h4_source_close_ts.isna()
    add("4h_context_fully_closed",bool(causal4.all()),int((~causal4).sum()),"future/partial 4H rows")

    forbidden=[c for c in out.columns if any(k in c.lower() for k in ["forward","future","tp_","sl_","mfe","mae","outcome","label"])]
    add("no_future_label_fields",len(forbidden)==0,forbidden)

    pa=prefix_audit(x5,feats)
    pa.to_csv(ROOT/"SOL_REGIME_DETECTOR_STAGE2_PrefixAudit.csv",index=False)
    add("prefix_causality_all_checkpoints",bool(pa["pass"].all()),f"{int(pa['pass'].sum())}/{len(pa)} checkpoints")

    adf=pd.DataFrame(audit)
    adf.to_csv(OUT_AUDIT,index=False)
    passed=bool(adf["pass"].all())

    # Descriptive counts only; no future behavior and no regime scoring.
    structure_counts=out.h1_structure_state.value_counts(dropna=False).to_dict()
    h4_structure_counts=out.h4_structure_state.value_counts(dropna=False).to_dict()
    raw1_counts=raw1.type.value_counts().to_dict() if len(raw1) else {}
    raw4_counts=raw4.type.value_counts().to_dict() if len(raw4) else {}

    lines=[
        "# SOL Regime Detector — Stage 2 Feature Engine Result","",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Exported 1H feature rows: **{len(out):,}**.",
        f"Raw confirmed 1H pivots: **{len(raw1):,}** ({raw1_counts}).",
        f"Raw confirmed 4H pivots: **{len(raw4):,}** ({raw4_counts}).","",
        "## Feature-engine descriptive structure only","",
        f"1H causal structure-state counts: **{structure_counts}**.",
        f"4H causal structure-state counts: **{h4_structure_counts}**.",
        "These are structural feature states, **not** Bull/Bear/Sideways regime labels.","",
        "## Mandatory audits","",
        "| Audit | Pass | Value |","|---|---|---|"
    ]
    for _,r in adf.iterrows():
        lines.append(f"| {r['audit']} | {'PASS' if r['pass'] else 'FAIL'} | {str(r['value']).replace('|','/')} |")
    lines += ["","## Prefix causality checkpoints","",
              "| Checkpoint | Pass | Max numeric diff | String mismatch |",
              "|---|---|---:|---:|"]
    for _,r in pa.iterrows():
        lines.append(f"| {r.checkpoint} | {'PASS' if r['pass'] else 'FAIL'} | {r.max_abs_numeric_diff} | {int(r.string_mismatch)} |")

    lines += ["","## Decision",""]
    if passed:
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_VALID**","",
            "Stage 2 feature engine passed every frozen causality / completeness / swing-sequence audit.",
            "No Bull/Bear/Sideways threshold or score has been selected yet.",
            "Stage 3 is authorized to build competing BullScore / BearScore / SidewaysScore using Development data only."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_VALID\nNEXT=STAGE3_SCORING\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_REJECTED**","",
            f"Failed audits: **{failed}**.",
            "Stage 3 is not authorized until Stage 2 passes without changing the frozen audit standards."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_REJECTED\n")

    OUT_MD.write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
