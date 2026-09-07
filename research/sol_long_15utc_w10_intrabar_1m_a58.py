#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_A57 = ROOT / "SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_EVENTS.csv"
OUT_WINDOWS = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_WINDOWS.csv"
OUT_STATES = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_STATES.csv"
OUT_MOTIFS = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_MOTIFS.csv"
OUT_CONT = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_CONTINUOUS.csv"
OUT_COVERAGE = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_COVERAGE.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_Status.txt"

BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
SYMBOL = "SOLUSDT"
PARTS = ("development", "external", "reference_validation")
EXPECTED = {
    "development": {"total": 300, "FAILED_BREAK": 233, "RECOVER_E40": 63, "UNRESOLVED_TIME": 4},
    "external": {"total": 192, "FAILED_BREAK": 133, "RECOVER_E40": 54, "UNRESOLVED_TIME": 5},
    "reference_validation": {"total": 184, "FAILED_BREAK": 134, "RECOVER_E40": 48, "UNRESOLVED_TIME": 2},
}
KS = (1, 2, 3, 4)
EPS = 1e-12

ALWAYS_MOTIFS = (
    "ANY_CLOSE_LE_H_BY_K",
    "CURRENT_CLOSE_LE_H",
    "NO_CLOSE_ABOVE_H10_BY_K",
    "NO_HIGH_ABOVE_H10_BY_K",
    "REJECT_H10_TO_H05_BY_K",
    "CURRENT_BEARISH",
)
K2_MOTIFS = (
    "TWO_PLUS_NEAR_H10_BY_K",
    "TWO_PLUS_NEAR_H05_BY_K",
    "H_LOSS_THEN_RECLAIM_BY_K",
    "LAST2_LOWER_CLOSES",
    "LAST2_LOWER_HIGHS",
)
CONT = (
    "latest_close_H_R",
    "cum_max_high_H_R",
    "cum_min_low_H_R",
    "cum_rejection_R",
    "cum_path_range_R",
    "latest_body_R",
    "latest_range_R",
    "count_close_le_H",
    "count_close_H05",
    "count_close_H10",
)


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def fmt(v, d=3):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def ratio(a, b):
    if pd.isna(a) or pd.isna(b): return np.nan
    if b <= EPS: return np.inf if a > EPS else np.nan
    return float(a / b)


def parse_dt_cols(e):
    for c in ["execution_start", "entry_ts", "warning_ts", "warning_known_ts", "terminal_event_ts", "parent_exit_ts"]:
        if c in e.columns:
            e[c] = pd.to_datetime(e[c], utc=True, errors="coerce")
    return e


def load_a57():
    e = pd.read_csv(IN_A57)
    e = parse_dt_cols(e)
    q = e[e.warning_family.astype(str) == "W10"].copy().sort_values(["partition", "warning_ts", "entry_ts"]).reset_index(drop=True)
    errors = []
    for p in PARTS:
        z = q[q.partition == p]
        exp = EXPECTED[p]
        if len(z) != exp["total"]:
            errors.append(f"{p} W10 total {len(z)} != {exp['total']}")
        for lab in ("FAILED_BREAK", "RECOVER_E40", "UNRESOLVED_TIME"):
            n = int((z.terminal_label == lab).sum())
            if n != exp[lab]:
                errors.append(f"{p} {lab} {n} != {exp[lab]}")
    if len(q) != 676:
        errors.append(f"pooled W10 {len(q)} != 676")
    if q.warning_ts.isna().any():
        errors.append("missing warning_ts")
    return q, errors


def month_key(ts):
    t = pd.Timestamp(ts)
    return t.strftime("%Y-%m")


def needed_by_month(events):
    out = {}
    for ts in events.warning_ts:
        t = pd.Timestamp(ts)
        ym = month_key(t)
        s = out.setdefault(ym, set())
        for j in range(5):
            s.add(t + pd.Timedelta(minutes=j))
    return out


def fetch_month(ym, needed):
    url = f"{BASE}/{SYMBOL}/1m/{SYMBOL}-1m-{ym}.zip"
    r = requests.get(url, timeout=120, headers={"User-Agent": "bababot-sol-a58/1.0"})
    if r.status_code == 404:
        return ym, pd.DataFrame(columns=["ts", "open", "high", "low", "close"]), f"404 {url}"
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return ym, pd.DataFrame(columns=["ts", "open", "high", "low", "close"]), f"no csv {url}"
        with zf.open(names[0]) as fh:
            x = pd.read_csv(fh, header=None, usecols=[0,1,2,3,4], names=["ts","open","high","low","close"])
    raw = pd.to_numeric(x.ts, errors="coerce")
    raw = np.where(raw > 100_000_000_000_000, raw / 1000.0, raw)
    x["ts"] = pd.to_datetime(raw, unit="ms", utc=True, errors="coerce")
    need_index = pd.DatetimeIndex(sorted(needed))
    x = x[x.ts.isin(need_index)].copy()
    for c in ("open", "high", "low", "close"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    return ym, x.dropna(subset=["ts","open","high","low","close"]), None


def load_needed_1m(events):
    needs = needed_by_month(events)
    frames = []
    fetch_errors = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_month, ym, needed): ym for ym, needed in needs.items()}
        for fut in as_completed(futs):
            ym = futs[fut]
            try:
                _, x, err = fut.result()
                if err: fetch_errors.append(err)
                if len(x): frames.append(x)
            except Exception as exc:
                fetch_errors.append(f"{ym}: {type(exc).__name__}: {exc}")
    if frames:
        x = pd.concat(frames, ignore_index=True)
    else:
        x = pd.DataFrame(columns=["ts","open","high","low","close"])
    dup_n = int(x.duplicated("ts", keep=False).sum()) if len(x) else 0
    x = x.sort_values("ts").set_index("ts") if len(x) else pd.DataFrame(columns=["open","high","low","close"], index=pd.DatetimeIndex([], tz="UTC"))
    return x, dup_n, fetch_errors, len(needs)


def load_needed_5m(events):
    # Reuse frozen SOL loader implementation dynamically without changing parent mechanics.
    import importlib.util
    p = Path(__file__).resolve().parent / "sol_long_visit_break_a1.py"
    spec = importlib.util.spec_from_file_location("sol_a1_a58", p)
    a1 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a1)
    x5, coverage = a1.load5()
    needed = pd.DatetimeIndex(sorted(set(pd.to_datetime(events.warning_ts, utc=True))))
    return x5.reindex(needed), coverage


def tol(v):
    return max(1e-8, 1e-10 * abs(float(v)))


def same(a, b):
    if pd.isna(a) or pd.isna(b): return False
    return abs(float(a) - float(b)) <= tol(b)


def build_windows(events, x1, x5):
    rows = []
    for _, r in events.iterrows():
        t = pd.Timestamp(r.warning_ts)
        times = pd.date_range(t, periods=5, freq="1min", tz="UTC")
        available = bool(all(ts in x1.index for ts in times))
        parity = False
        agg = {"agg_open":np.nan,"agg_high":np.nan,"agg_low":np.nan,"agg_close":np.nan}
        five = x5.loc[t] if t in x5.index else pd.Series(dtype=float)
        if available and len(five):
            z = x1.loc[times]
            agg = {
                "agg_open": float(z.open.iloc[0]),
                "agg_high": float(z.high.max()),
                "agg_low": float(z.low.min()),
                "agg_close": float(z.close.iloc[-1]),
            }
            parity = bool(
                same(agg["agg_open"], five.open) and
                same(agg["agg_high"], five.high) and
                same(agg["agg_low"], five.low) and
                same(agg["agg_close"], five.close)
            )
        rows.append({
            "partition":r.partition,"dev_block":r.dev_block,"entry_ts":r.entry_ts,
            "warning_ts":t,"terminal_label":r.terminal_label,"terminal_event_ts":r.terminal_event_ts,
            "H":float(r.H),"L":float(r.L),"R":float(r.R),
            "available_5x1m":available,"ohlc_parity":parity,
            "five_open":float(five.open) if len(five) else np.nan,
            "five_high":float(five.high) if len(five) else np.nan,
            "five_low":float(five.low) if len(five) else np.nan,
            "five_close":float(five.close) if len(five) else np.nan,
            **agg,
        })
    return pd.DataFrame(rows)


def state_features(z, H, R, k):
    p = z.iloc[:k]
    latest = p.iloc[-1]
    closes = p.close.to_numpy(float)
    highs = p.high.to_numpy(float)
    lows = p.low.to_numpy(float)
    opens = p.open.to_numpy(float)
    h05 = H + 0.05*R
    h10 = H + 0.10*R
    near10 = (closes > H + EPS) & (closes <= h10 + EPS)
    near05 = (closes > H + EPS) & (closes <= h05 + EPS)
    any_le_h = bool((closes <= H + EPS).any())
    current_le_h = bool(closes[-1] <= H + EPS)
    no_close_h10 = bool(not (closes > h10 + EPS).any())
    no_high_h10 = bool(not (highs > h10 + EPS).any())
    reject = bool(float(highs.max()) >= h10 - EPS and closes[-1] <= h05 + EPS)
    reclaim = bool(k >= 2 and (closes[:-1] <= H + EPS).any() and closes[-1] > H + EPS)
    return {
        "minute_k":k,
        "ANY_CLOSE_LE_H_BY_K":any_le_h,
        "CURRENT_CLOSE_LE_H":current_le_h,
        "NO_CLOSE_ABOVE_H10_BY_K":no_close_h10,
        "NO_HIGH_ABOVE_H10_BY_K":no_high_h10,
        "TWO_PLUS_NEAR_H10_BY_K":bool(k >= 2 and int(near10.sum()) >= 2),
        "TWO_PLUS_NEAR_H05_BY_K":bool(k >= 2 and int(near05.sum()) >= 2),
        "REJECT_H10_TO_H05_BY_K":reject,
        "H_LOSS_THEN_RECLAIM_BY_K":reclaim,
        "LAST2_LOWER_CLOSES":bool(k >= 2 and closes[-1] < closes[-2] - EPS),
        "LAST2_LOWER_HIGHS":bool(k >= 2 and highs[-1] < highs[-2] - EPS),
        "CURRENT_BEARISH":bool(closes[-1] < opens[-1] - EPS),
        "latest_close_H_R":(closes[-1]-H)/R,
        "cum_max_high_H_R":(float(highs.max())-H)/R,
        "cum_min_low_H_R":(float(lows.min())-H)/R,
        "cum_rejection_R":(float(highs.max())-closes[-1])/R,
        "cum_path_range_R":(float(highs.max())-float(lows.min()))/R,
        "latest_body_R":(closes[-1]-opens[-1])/R,
        "latest_range_R":(highs[-1]-lows[-1])/R,
        "count_close_le_H":int((closes <= H + EPS).sum()),
        "count_close_H05":int(near05.sum()),
        "count_close_H10":int(near10.sum()),
    }


def build_states(events, windows, x1):
    good = windows[windows.available_5x1m & windows.ohlc_parity].copy()
    rows = []
    keys = set((str(r.partition), pd.Timestamp(r.warning_ts), pd.Timestamp(r.entry_ts)) for _,r in good.iterrows())
    for _, r in events.iterrows():
        key = (str(r.partition), pd.Timestamp(r.warning_ts), pd.Timestamp(r.entry_ts))
        if key not in keys: continue
        t = pd.Timestamp(r.warning_ts)
        times = pd.date_range(t, periods=5, freq="1min", tz="UTC")
        z = x1.loc[times]
        for k in KS:
            f = state_features(z,float(r.H),float(r.R),k)
            rows.append({
                "partition":r.partition,"dev_block":r.dev_block,"entry_ts":r.entry_ts,
                "warning_ts":t,"terminal_label":r.terminal_label,"terminal_event_ts":r.terminal_event_ts,
                "H":float(r.H),"L":float(r.L),"R":float(r.R),**f,
            })
    return pd.DataFrame(rows)


def coverage_table(events, windows, dup_n, fetch_errors, month_n):
    rows=[]
    for p in PARTS:
        e=events[events.partition==p]
        w=windows[windows.partition==p]
        av=int(w.available_5x1m.sum()); par=int(w.ohlc_parity.sum())
        rows.append({
            "partition":p,"w10_n":len(e),"available_n":av,"availability_rate":av/len(e) if len(e) else np.nan,
            "parity_n":par,"parity_rate":par/len(e) if len(e) else np.nan,
            "duplicate_used_rows_pooled":dup_n,"months_requested_pooled":month_n,"fetch_error_count_pooled":len(fetch_errors),
        })
    return pd.DataFrame(rows)


def cohort_stats(q, motif):
    f=q[q.terminal_label=="FAILED_BREAK"]
    t=q[q.terminal_label=="RECOVER_E40"]
    if len(f)==0 or len(t)==0:
        return {"fail_n":len(f),"target_n":len(t),"fail_hit":np.nan,"target_hit":np.nan,"gap":np.nan,"ratio":np.nan}
    fh=float(f[motif].astype(bool).mean()); th=float(t[motif].astype(bool).mean())
    return {"fail_n":len(f),"target_n":len(t),"fail_hit":fh,"target_hit":th,"gap":fh-th,"ratio":ratio(fh,th)}


def motif_list(k):
    return ALWAYS_MOTIFS + (K2_MOTIFS if k >= 2 else tuple())


def analyze_motifs(states):
    rows=[]
    for k in KS:
        dev=states[(states.partition=="development")&(states.minute_k==k)]
        for motif in motif_list(k):
            ds=cohort_stats(dev,motif)
            adequate=same_dir=0
            for bi in range(6):
                b=dev[pd.to_numeric(dev.dev_block,errors="coerce")==bi]
                s=cohort_stats(b,motif)
                ok=s["fail_n"]>=10 and s["target_n"]>=3
                if ok:
                    adequate += 1
                    if pd.notna(s["gap"]) and s["gap"]>0: same_dir += 1
            dev_supported=bool(
                ds["fail_n"]>=200 and ds["target_n"]>=50 and
                pd.notna(ds["fail_hit"]) and ds["fail_hit"]>=0.30-EPS and
                ds["target_hit"]<=0.25+EPS and ds["gap"]>=0.20-EPS and
                ds["ratio"]>=2.0-EPS and adequate>=5 and same_dir>=5
            )
            row={
                "minute_k":k,"motif":motif,
                "dev_fail_n":ds["fail_n"],"dev_target_n":ds["target_n"],"dev_fail_hit":ds["fail_hit"],
                "dev_target_hit":ds["target_hit"],"dev_gap":ds["gap"],"dev_ratio":ds["ratio"],
                "adequate_dev_blocks":adequate,"same_direction_dev_blocks":same_dir,"development_supported":dev_supported,
                "external_fail_n":np.nan,"external_target_n":np.nan,"external_fail_hit":np.nan,"external_target_hit":np.nan,
                "external_gap":np.nan,"external_ratio":np.nan,
                "reference_fail_n":np.nan,"reference_target_n":np.nan,"reference_fail_hit":np.nan,"reference_target_hit":np.nan,
                "reference_gap":np.nan,"reference_ratio":np.nan,"replicated":False,
            }
            if dev_supported:
                oos_ok=True
                for part,prefix in (("external","external"),("reference_validation","reference")):
                    s=cohort_stats(states[(states.partition==part)&(states.minute_k==k)],motif)
                    for name,val in s.items(): row[f"{prefix}_{name}"]=val
                    pp=bool(
                        s["fail_n"]>=100 and s["target_n"]>=35 and
                        pd.notna(s["fail_hit"]) and s["fail_hit"]>s["target_hit"] and
                        s["fail_hit"]>=0.20-EPS and s["target_hit"]<=0.35+EPS and
                        s["gap"]>=0.15-EPS and s["ratio"]>=1.50-EPS
                    )
                    oos_ok = oos_ok and pp
                row["replicated"]=bool(oos_ok)
            rows.append(row)
    return pd.DataFrame(rows)


def analyze_cont(states):
    rows=[]
    for p in PARTS:
        for k in KS:
            q=states[(states.partition==p)&(states.minute_k==k)]
            f=q[q.terminal_label=="FAILED_BREAK"]; t=q[q.terminal_label=="RECOVER_E40"]
            for feat in CONT:
                a=pd.to_numeric(f[feat],errors="coerce").dropna(); b=pd.to_numeric(t[feat],errors="coerce").dropna()
                rows.append({
                    "partition":p,"minute_k":k,"feature":feat,"fail_n":len(a),"target_n":len(b),
                    "fail_median":float(a.median()) if len(a) else np.nan,
                    "target_median":float(b.median()) if len(b) else np.nan,
                    "gap":float(a.median()-b.median()) if len(a) and len(b) else np.nan,
                })
    return pd.DataFrame(rows)


def write_result(events, windows, states, motifs, cont, cov, coverage5, dup_n, fetch_errors, recon_errors):
    data_errors=[]
    for _,r in cov.iterrows():
        if float(r.availability_rate) < .99-EPS: data_errors.append(f"{r.partition} 1m availability {r.availability_rate:.4f} < .99")
        if float(r.parity_rate) < .99-EPS: data_errors.append(f"{r.partition} OHLC parity {r.parity_rate:.4f} < .99")
    if dup_n>0: data_errors.append(f"duplicate used 1m rows: {dup_n}")
    if recon_errors:
        status="SOL_LONG_15UTC_W10_INTRABAR_1M_A58_RECONCILIATION_FAIL"
    elif data_errors:
        status="SOL_LONG_15UTC_W10_INTRABAR_1M_A58_DATA_FAIL"
    else:
        rep=motifs[motifs.replicated==True].copy()
        status="SOL_LONG_15UTC_W10_INTRABAR_1M_A58_SUPPORTED_FOR_A59" if len(rep) else "SOL_LONG_15UTC_W10_INTRABAR_1M_A58_INCONCLUSIVE"

    lines=[
        "# SOL LONG 15:00 UTC W10 Intrabar 1m Decomposition — A58 Result","",
        f"Frozen SOL 5m source coverage: **{100.0*coverage5:.4f}%**.","",
        "A58 conditionally decomposes the first W10 5m warning candle into completed 1m states K1–K4. Cohort membership is future-known within the 5m candle, so any supported motif requires A59 live-opportunity revalidation before execution.","",
        "## Reconciliation and 1m feasibility","",
        f"Frozen W10 rows: **{len(events)}**. 1m state rows: **{len(states)}**. Duplicate used 1m rows: **{dup_n}**. Fetch errors: **{len(fetch_errors)}**.","",
        "| Partition | W10 | 5x1m available | Availability | OHLC parity | Parity rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _,r in cov.iterrows():
        lines.append(f"| {r.partition} | {int(r.w10_n)} | {int(r.available_n)} | {pct(r.availability_rate)} | {int(r.parity_n)} | {pct(r.parity_rate)} |")
    if recon_errors:
        lines += ["","Reconciliation errors:"]+[f"- {x}" for x in recon_errors]
    if data_errors:
        lines += ["","Data feasibility errors:"]+[f"- {x}" for x in data_errors]
    if fetch_errors:
        lines += ["","Fetch diagnostics:"]+[f"- {x}" for x in fetch_errors[:10]]

    if not recon_errors and not data_errors:
        rep=motifs[motifs.replicated==True].copy()
        lines += ["","## Replicated conditional 1m motifs","",
                  "| K | Motif | Dev fail/target | Gap | Ratio | External fail/target | Gap | RefVal fail/target | Gap |",
                  "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
        if len(rep):
            for _,r in rep.sort_values(["minute_k","dev_target_hit","dev_gap"],ascending=[True,True,False]).iterrows():
                lines.append(f"| K{int(r.minute_k)} | {r.motif} | {pct(r.dev_fail_hit)} / {pct(r.dev_target_hit)} | {100*r.dev_gap:.1f}pp | {fmt(r.dev_ratio,2)}x | {pct(r.external_fail_hit)} / {pct(r.external_target_hit)} | {100*r.external_gap:.1f}pp | {pct(r.reference_fail_hit)} / {pct(r.reference_target_hit)} | {100*r.reference_gap:.1f}pp |")
        else:
            lines.append("| - | No motif passed Development + both OOS gates | - | - | - | - | - | - | - |")

        lines += ["","## Strongest Development binary motifs","",
                  "| K | Motif | Fail hit | Target hit | Gap | Ratio | Blocks | Dev supported | Replicated |",
                  "|---:|---|---:|---:|---:|---:|---:|---|---|"]
        show=motifs.sort_values(["development_supported","dev_gap","dev_fail_hit"],ascending=[False,False,False]).head(18)
        for _,r in show.iterrows():
            lines.append(f"| K{int(r.minute_k)} | {r.motif} | {pct(r.dev_fail_hit)} | {pct(r.dev_target_hit)} | {100*r.dev_gap:.1f}pp | {fmt(r.dev_ratio,2)}x | {int(r.same_direction_dev_blocks)}/{int(r.adequate_dev_blocks)} | {bool(r.development_supported)} | {bool(r.replicated)} |")

        lines += ["","## Report-only continuous path anatomy","",
                  "| Partition | K | Feature | Fail median | E40 median | Gap |",
                  "|---|---:|---|---:|---:|---:|"]
        for _,r in cont[cont.feature.isin(["latest_close_H_R","cum_max_high_H_R","cum_rejection_R","cum_min_low_H_R"])].iterrows():
            lines.append(f"| {r.partition} | K{int(r.minute_k)} | {r.feature} | {fmt(r.fail_median)} | {fmt(r.target_median)} | {fmt(r.gap)} |")

        if len(rep):
            s=rep.sort_values(["minute_k","dev_target_hit","dev_gap","dev_fail_hit"],ascending=[True,True,False,False]).iloc[0]
            lines += ["","## Primary conditional motif","",
                      f"Selected by frozen rule: **K{int(s.minute_k)} / `{s.motif}`**.","",
                      "This is not yet executable. A59 must remove future W10 cohort conditioning and evaluate this exact motif on all live post-breakout 1m opportunities before any economics test."]

    lines += ["","## Decision","",f"**Status: {status}**","",
              "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    events,recon_errors=load_a57()
    x1,dup_n,fetch_errors,month_n=load_needed_1m(events)
    x5,coverage5=load_needed_5m(events)
    windows=build_windows(events,x1,x5)
    cov=coverage_table(events,windows,dup_n,fetch_errors,month_n)
    states=build_states(events,windows,x1)
    motifs=analyze_motifs(states) if len(states) else pd.DataFrame()
    cont=analyze_cont(states) if len(states) else pd.DataFrame()

    windows.to_csv(OUT_WINDOWS,index=False)
    states.to_csv(OUT_STATES,index=False)
    motifs.to_csv(OUT_MOTIFS,index=False)
    cont.to_csv(OUT_CONT,index=False)
    cov.to_csv(OUT_COVERAGE,index=False)
    status=write_result(events,windows,states,motifs,cont,cov,coverage5,dup_n,fetch_errors,recon_errors)
    print(status)

if __name__=="__main__":
    main()
