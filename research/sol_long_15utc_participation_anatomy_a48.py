#!/usr/bin/env python3
from __future__ import annotations

import io
import importlib.util
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
A45_PATH = Path(__file__).resolve().parent / "sol_long_15utc_parent_prerange_anatomy_a45.py"
spec = importlib.util.spec_from_file_location("sol_a45", A45_PATH)
a45 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a45)

INFILE = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_TRADES.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_PARTICIPATION_A48_TRADES.csv"
OUT_FEATURES = ROOT / "SOL_LONG_15UTC_PARTICIPATION_A48_FEATURES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_PARTICIPATION_A48_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_PARTICIPATION_A48_Status.txt"

SYMBOL = "SOLUSDT"
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START = pd.Timestamp("2020-08-01T00:00:00Z")
END = pd.Timestamp("2026-08-01T00:00:00Z")
PARTS = ["development", "external", "reference_validation"]
EXPECTED_COUNTS = {"development": 601, "external": 281, "reference_validation": 337}
BAR = pd.Timedelta(minutes=5)
EPS = 1e-12

FEATURE_FAMILY = {
    "ref_quotevol_perbar_vs_pre6": "REF_VS_PRE6",
    "ref_basevol_perbar_vs_pre6": "REF_VS_PRE6",
    "ref_trades_perbar_vs_pre6": "REF_VS_PRE6",
    "ref_taker_buy_ratio": "REF_VS_PRE6",
    "pre6_taker_buy_ratio": "REF_VS_PRE6",
    "ref_minus_pre6_taker_buy_ratio": "REF_VS_PRE6",
    "ref_last60_quotevol_vs_prior300": "LATE_REF",
    "ref_last60_trades_vs_prior300": "LATE_REF",
    "ref_last60_taker_buy_ratio": "LATE_REF",
    "ref_last30_quotevol_vs_prior330": "LATE_REF",
    "ref_last30_trades_vs_prior330": "LATE_REF",
    "ref_last30_taker_buy_ratio": "LATE_REF",
    "upper80_quotevol_share": "UPPER_PARTICIPATION",
    "upper90_quotevol_share": "UPPER_PARTICIPATION",
    "nearH10_quotevol_share": "UPPER_PARTICIPATION",
    "nearH05_quotevol_share": "UPPER_PARTICIPATION",
    "nearH10_trades_share": "UPPER_PARTICIPATION",
    "nearH05_trades_share": "UPPER_PARTICIPATION",
    "prefill_quotevol_perbar_vs_ref": "PREFILL_PARTICIPATION",
    "prefill_trades_perbar_vs_ref": "PREFILL_PARTICIPATION",
    "prefill_taker_buy_ratio": "PREFILL_PARTICIPATION",
    "prefill_lastbar_quotevol_vs_refavg": "PREFILL_PARTICIPATION",
    "prefill_lastbar_trades_vs_refavg": "PREFILL_PARTICIPATION",
    "prefill_last30_quotevol_vs_refavg": "PREFILL_PARTICIPATION",
    "prefill_last30_trades_vs_refavg": "PREFILL_PARTICIPATION",
    "prefill_last30_taker_buy_ratio": "PREFILL_PARTICIPATION",
}
FEATURES = list(FEATURE_FAMILY)


def month_urls():
    out = []
    cur = pd.Timestamp(FETCH_START.year, FETCH_START.month, 1, tz="UTC")
    end = pd.Timestamp(END.year, END.month, 1, tz="UTC")
    while cur < end:
        ym = cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-sol-a48/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh, header=None,
                usecols=[0,1,2,3,4,5,7,8,9],
                names=["ts","open","high","low","close","base_volume","quote_volume","trades","taker_buy_base"]
            )


def load_extended():
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_one, u) for u in month_urls()]
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError("No SOLUSDT 5m data")
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open","high","low","close","base_volume","quote_volume","trades","taker_buy_base"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= FETCH_START) & (x.ts < END)].set_index("ts")
    expected = int((x.index[-1] - x.index[0]) / BAR) + 1
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low {coverage:.6f}")
    return x, coverage


def exact_window(x, start, end, n):
    q = x[(x.index >= start) & (x.index < end)].copy()
    if len(q) != n or q.index[0] != start or q.index[-1] != end - BAR:
        raise ValueError(f"incomplete window {start}..{end}: {len(q)}/{n}")
    return q


def ratio(a, b):
    return float(a / b) if pd.notna(a) and pd.notna(b) and abs(float(b)) > EPS else np.nan


def taker_ratio(q):
    return ratio(q.taker_buy_base.sum(), q.base_volume.sum())


def mean_ratio(a, b, col):
    return ratio(pd.to_numeric(a[col], errors="coerce").mean(), pd.to_numeric(b[col], errors="coerce").mean())


def weighted_share(q, mask, col):
    total = float(pd.to_numeric(q[col], errors="coerce").sum())
    if total <= EPS:
        return np.nan
    return float(pd.to_numeric(q.loc[mask, col], errors="coerce").sum()) / total


def enrich_row(x, r):
    es = pd.Timestamp(r.execution_start)
    et = pd.Timestamp(r.entry_ts)
    rs = es - pd.Timedelta(hours=6)
    ref = exact_window(x, rs, es, 72)
    pre6 = exact_window(x, rs - pd.Timedelta(hours=6), rs, 72)
    H, L, R = float(r.H), float(r.L), float(r.R)
    tol = max(1e-8, abs(R) * 1e-9)
    if not (
        np.isclose(float(ref.high.max()), H, rtol=1e-10, atol=tol)
        and np.isclose(float(ref.low.min()), L, rtol=1e-10, atol=tol)
    ):
        raise ValueError("H/L reconciliation failed")

    out = {
        "ref_quotevol_perbar_vs_pre6": mean_ratio(ref, pre6, "quote_volume"),
        "ref_basevol_perbar_vs_pre6": mean_ratio(ref, pre6, "base_volume"),
        "ref_trades_perbar_vs_pre6": mean_ratio(ref, pre6, "trades"),
        "ref_taker_buy_ratio": taker_ratio(ref),
        "pre6_taker_buy_ratio": taker_ratio(pre6),
    }
    out["ref_minus_pre6_taker_buy_ratio"] = out["ref_taker_buy_ratio"] - out["pre6_taker_buy_ratio"]

    last60, prior300 = ref.iloc[-12:], ref.iloc[:-12]
    last30, prior330 = ref.iloc[-6:], ref.iloc[:-6]
    out.update({
        "ref_last60_quotevol_vs_prior300": mean_ratio(last60, prior300, "quote_volume"),
        "ref_last60_trades_vs_prior300": mean_ratio(last60, prior300, "trades"),
        "ref_last60_taker_buy_ratio": taker_ratio(last60),
        "ref_last30_quotevol_vs_prior330": mean_ratio(last30, prior330, "quote_volume"),
        "ref_last30_trades_vs_prior330": mean_ratio(last30, prior330, "trades"),
        "ref_last30_taker_buy_ratio": taker_ratio(last30),
    })

    upper80 = L + 0.80 * R
    upper90 = L + 0.90 * R
    near10 = H - 0.10 * R
    near05 = H - 0.05 * R
    out.update({
        "upper80_quotevol_share": weighted_share(ref, ref.close >= upper80, "quote_volume"),
        "upper90_quotevol_share": weighted_share(ref, ref.close >= upper90, "quote_volume"),
        "nearH10_quotevol_share": weighted_share(ref, ref.high >= near10, "quote_volume"),
        "nearH05_quotevol_share": weighted_share(ref, ref.high >= near05, "quote_volume"),
        "nearH10_trades_share": weighted_share(ref, ref.high >= near10, "trades"),
        "nearH05_trades_share": weighted_share(ref, ref.high >= near05, "trades"),
    })

    prefill = x[(x.index >= es) & (x.index < et)].copy()
    ref_qavg = float(ref.quote_volume.mean())
    ref_tavg = float(ref.trades.mean())
    if len(prefill):
        out.update({
            "prefill_quotevol_perbar_vs_ref": ratio(prefill.quote_volume.mean(), ref_qavg),
            "prefill_trades_perbar_vs_ref": ratio(prefill.trades.mean(), ref_tavg),
            "prefill_taker_buy_ratio": taker_ratio(prefill),
            "prefill_lastbar_quotevol_vs_refavg": ratio(float(prefill.quote_volume.iloc[-1]), ref_qavg),
            "prefill_lastbar_trades_vs_refavg": ratio(float(prefill.trades.iloc[-1]), ref_tavg),
        })
    else:
        for f in ["prefill_quotevol_perbar_vs_ref","prefill_trades_perbar_vs_ref","prefill_taker_buy_ratio","prefill_lastbar_quotevol_vs_refavg","prefill_lastbar_trades_vs_refavg"]:
            out[f] = np.nan

    if len(prefill) >= 6:
        z = prefill.iloc[-6:]
        out.update({
            "prefill_last30_quotevol_vs_refavg": ratio(float(z.quote_volume.mean()), ref_qavg),
            "prefill_last30_trades_vs_refavg": ratio(float(z.trades.mean()), ref_tavg),
            "prefill_last30_taker_buy_ratio": taker_ratio(z),
        })
    else:
        out["prefill_last30_quotevol_vs_refavg"] = np.nan
        out["prefill_last30_trades_vs_refavg"] = np.nan
        out["prefill_last30_taker_buy_ratio"] = np.nan
    return out


def main():
    parent = pd.read_csv(INFILE)
    for c in ["execution_start","entry_ts","exit_ts"]:
        parent[c] = pd.to_datetime(parent[c], utc=True, errors="coerce")
    for c in ["H","L","R","pnl","pnl_5bps","dev_block"]:
        parent[c] = pd.to_numeric(parent[c], errors="coerce")
    counts = parent.groupby("partition").size().to_dict()
    count_ok = all(int(counts.get(k,0)) == v for k,v in EXPECTED_COUNTS.items())

    x, coverage = load_extended()
    enriched, errors = [], []
    for idx, r in parent.iterrows():
        try:
            z = r.to_dict()
            z.update(enrich_row(x, r))
            z["stress_outcome"] = "WIN" if float(r.pnl_5bps) > 0 else "FAIL"
            enriched.append(z)
        except Exception as exc:
            errors.append((int(idx), str(exc)))

    trades = pd.DataFrame(enriched)
    full_recon = bool(count_ok and not errors and len(trades) == sum(EXPECTED_COUNTS.values()))
    rows = []
    if full_recon:
        for feature in FEATURES:
            dev = a45.effect_stats(trades[trades.partition == "development"], feature)
            ext = a45.effect_stats(trades[trades.partition == "external"], feature)
            refv = a45.effect_stats(trades[trades.partition == "reference_validation"], feature)
            sign = int(np.sign(dev["gap"])) if pd.notna(dev["gap"]) else 0
            adequate = same = 0
            row = {"family": FEATURE_FAMILY[feature], "feature": feature}
            for bi in range(6):
                b = trades[(trades.partition == "development") & (pd.to_numeric(trades.dev_block, errors="coerce") == bi)]
                bs = a45.effect_stats(b, feature)
                ok = bool(bs["win_n"] >= 20 and bs["fail_n"] >= 20)
                if ok:
                    adequate += 1
                    if sign != 0 and pd.notna(bs["gap"]) and int(np.sign(bs["gap"])) == sign:
                        same += 1
                row[f"b{bi+1}_gap"] = bs["gap"]
                row[f"b{bi+1}_effect_IQR"] = bs["effect"]
            counts_ok = bool(dev["win_n"]>=100 and dev["fail_n"]>=100 and ext["win_n"]>=50 and ext["fail_n"]>=50 and refv["win_n"]>=50 and refv["fail_n"]>=50)
            rep = bool(
                counts_ok and pd.notna(dev["effect"]) and dev["effect"] >= 0.25
                and adequate >= 4 and same >= 4 and sign != 0
                and pd.notna(ext["gap"]) and int(np.sign(ext["gap"])) == sign
                and pd.notna(refv["gap"]) and int(np.sign(refv["gap"])) == sign
                and pd.notna(ext["effect"]) and ext["effect"] >= 0.10
                and pd.notna(refv["effect"]) and refv["effect"] >= 0.10
            )
            strong = bool(rep and dev["effect"] >= 0.35 and same >= 5)
            row.update({
                "dev_win_n":dev["win_n"],"dev_fail_n":dev["fail_n"],"dev_win_median":dev["win_median"],"dev_fail_median":dev["fail_median"],"dev_gap":dev["gap"],"dev_effect_IQR":dev["effect"],
                "adequate_dev_blocks":adequate,"same_sign_dev_blocks":same,
                "external_gap":ext["gap"],"external_effect_IQR":ext["effect"],"reference_gap":refv["gap"],"reference_effect_IQR":refv["effect"],
                "replicated_directional":rep,"strong_replicated":strong
            })
            rows.append(row)

    features = pd.DataFrame(rows)
    if len(features):
        features = features.sort_values(["strong_replicated","replicated_directional","dev_effect_IQR"], ascending=[False,False,False], na_position="last").reset_index(drop=True)
    trades.to_csv(OUT_TRADES,index=False)
    features.to_csv(OUT_FEATURES,index=False)

    if not full_recon:
        status = "SOL_LONG_15UTC_PARTICIPATION_A48_RECONCILIATION_FAIL"
    elif bool(features.replicated_directional.any()):
        status = "SOL_LONG_15UTC_PARTICIPATION_A48_SUPPORTED_FOR_A49"
    else:
        status = "SOL_LONG_15UTC_PARTICIPATION_A48_INCONCLUSIVE"
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC Participation Anatomy — A48 Result","",
        "A48 keeps the A20 E0/E40 parent frozen and studies only volume/trade/taker-buy participation available before the H fill.","",
        f"Extended 5m coverage: **{100*coverage:.4f}%**. Count reconciliation: **{count_ok}**. Enriched rows: **{len(trades)}/{sum(EXPECTED_COUNTS.values())}**. Errors: **{len(errors)}**.","",
        "## Replicated participation separators","",
        "| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    if len(features) and bool(features.replicated_directional.any()):
        for _,r in features[features.replicated_directional==True].iterrows():
            lines.append(f"| {r.family} | {r.feature} | {a45.fmt(r.dev_win_median)} | {a45.fmt(r.dev_fail_median)} | {a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_effect_IQR)} | {'YES' if bool(r.strong_replicated) else 'NO'} |")
    else:
        lines.append("| - | none | - | - | - | - | - | - | - |")
    lines += ["","## Strongest diagnostics","",
              "| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |",
              "|---|---|---:|---:|---|---|---:|"]
    if len(features):
        for _,r in features.head(12).iterrows():
            lines.append(f"| {r.family} | {r.feature} | {a45.fmt(r.dev_effect_IQR)} | {int(r.same_sign_dev_blocks)}/{int(r.adequate_dev_blocks)} | {a45.fmt(r.external_gap)}/{a45.fmt(r.external_effect_IQR)} | {a45.fmt(r.reference_gap)}/{a45.fmt(r.reference_effect_IQR)} | {'YES' if bool(r.replicated_directional) else 'NO'} |")
    repn = int(features.replicated_directional.sum()) if len(features) else 0
    strongn = int(features.strong_replicated.sum()) if len(features) else 0
    lines += ["","## Decision","",f"Replicated features: **{repn}**. Strong replicated: **{strongn}**.","",f"**Status: {status}**","","Research only. Live Baba Bot remains unchanged."]
    if errors:
        lines += ["","First errors:"] + [f"- {i}: {e}" for i,e in errors[:10]]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
