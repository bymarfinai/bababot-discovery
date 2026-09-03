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
OUT_MD = ROOT / "SOL_LONG_VISIT_BREAK_A1_Result.md"
OUT_ATLAS = ROOT / "SOL_LONG_VISIT_BREAK_A1_ATLAS.csv"
OUT_VISITS = ROOT / "SOL_LONG_VISIT_BREAK_A1_VISITS.csv"
OUT_SELECTED = ROOT / "SOL_LONG_VISIT_BREAK_A1_SELECTED.csv"
OUT_EVENTS = ROOT / "SOL_LONG_VISIT_BREAK_A1_EVENTS.csv"
OUT_STATUS = ROOT / "SOL_LONG_VISIT_BREAK_A1_Status.txt"

SYMBOL = "SOLUSDT"
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
FETCH_START = pd.Timestamp("2020-08-01T00:00:00Z")
END = pd.Timestamp("2026-08-01T00:00:00Z")
PARTS = {
    "external": (pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2022-01-01", tz="UTC")),
    "development": (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
    "reference_validation": (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-07-30", tz="UTC")),
}
REFS = (60, 120, 180, 240, 300, 360, 420, 480, 600)
HOURS = tuple(range(24))
VISITS = (1, 2, 3, 4, 5)
XMIN = 720
BAR_MIN = 5
X_BARS = XMIN // BAR_MIN
EXT_LEVELS = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40)


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
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-sol-long-a1/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4],
                names=["ts", "open", "high", "low", "close"],
            )


def load5():
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
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= FETCH_START) & (x.ts < END)].set_index("ts")
    idx = x.index
    expected = int((idx[-1] - idx[0]) / pd.Timedelta(minutes=5)) + 1
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"5m coverage too low: {coverage:.6f}")
    return x, coverage


def dev_block(ts: pd.Timestamp):
    if not (pd.Timestamp("2022-01-01", tz="UTC") <= ts < pd.Timestamp("2025-01-01", tz="UTC")):
        return None
    return (ts.year - 2022) * 2 + (0 if ts.month <= 6 else 1)


def market(x: pd.DataFrame):
    return {
        "idx": x.index,
        "high": x.high.to_numpy(dtype=float, copy=False),
        "low": x.low.to_numpy(dtype=float, copy=False),
        "close": x.close.to_numpy(dtype=float, copy=False),
        "start": x.index[0],
        "end": x.index[-1] + pd.Timedelta(minutes=5),
    }


def fixed_extension(hi, break_i, endpos, H, R, minutes):
    n = minutes // BAR_MIN
    a = break_i + 1
    b = min(endpos, a + n)
    if a >= b:
        return 0.0
    return max(0.0, (float(np.max(hi[a:b])) - H) / R)


def scan_session(m, pos, endpos, H, L):
    hi = m["high"]
    cl = m["close"]
    R = H - L
    in_visit = False
    visit_count = 0
    visit_starts = []
    break_i = -1
    first_break_visit = 0

    for i in range(pos, endpos):
        at_high = float(hi[i]) >= H
        if at_high and not in_visit:
            visit_count += 1
            if visit_count <= 5:
                visit_starts.append(i)
            in_visit = True
        elif not at_high and in_visit:
            in_visit = False

        if in_visit and float(cl[i]) > H:
            break_i = i
            first_break_visit = visit_count
            break

    row = {
        "visits_reached": min(visit_count, 5),
        "first_break_visit": first_break_visit if 1 <= first_break_visit <= 5 else 0,
        "break_i": break_i,
        "first_visit_delay_min": (visit_starts[0] - pos) * BAR_MIN if visit_starts else np.nan,
        "h1_h2_min": (visit_starts[1] - visit_starts[0]) * BAR_MIN if len(visit_starts) >= 2 else np.nan,
        "h2_h3_min": (visit_starts[2] - visit_starts[1]) * BAR_MIN if len(visit_starts) >= 3 else np.nan,
        "h3_h4_min": (visit_starts[3] - visit_starts[2]) * BAR_MIN if len(visit_starts) >= 4 else np.nan,
        "h4_h5_min": (visit_starts[4] - visit_starts[3]) * BAR_MIN if len(visit_starts) >= 5 else np.nan,
        "break_delay_min": (break_i - pos + 1) * BAR_MIN if break_i >= 0 else np.nan,
        "break_close_excess_R": np.nan,
        "extension_before_reclaim_R": np.nan,
        "ext15_R": np.nan,
        "ext30_R": np.nan,
        "ext60_R": np.nan,
        "ext120_R": np.nan,
        "reclaim_min": np.nan,
        "reclaim15": False,
        "reclaim30": False,
        "reclaim60": False,
    }
    for level in EXT_LEVELS:
        row[f"reach_E{int(level*100):02d}"] = False

    if break_i < 0 or not (1 <= first_break_visit <= 5):
        return row

    row["break_close_excess_R"] = (float(cl[break_i]) - H) / R
    reclaim_i = -1
    for i in range(break_i + 1, endpos):
        if float(cl[i]) <= H:
            reclaim_i = i
            break

    a = break_i + 1
    b = reclaim_i if reclaim_i >= 0 else endpos
    if a < b:
        row["extension_before_reclaim_R"] = max(0.0, (float(np.max(hi[a:b])) - H) / R)
    else:
        row["extension_before_reclaim_R"] = 0.0

    row["ext15_R"] = fixed_extension(hi, break_i, endpos, H, R, 15)
    row["ext30_R"] = fixed_extension(hi, break_i, endpos, H, R, 30)
    row["ext60_R"] = fixed_extension(hi, break_i, endpos, H, R, 60)
    row["ext120_R"] = fixed_extension(hi, break_i, endpos, H, R, 120)

    if reclaim_i >= 0:
        mins = (reclaim_i - break_i) * BAR_MIN
        row["reclaim_min"] = mins
        row["reclaim15"] = mins <= 15
        row["reclaim30"] = mins <= 30
        row["reclaim60"] = mins <= 60

    ext = row["extension_before_reclaim_R"]
    for level in EXT_LEVELS:
        row[f"reach_E{int(level*100):02d}"] = bool(ext >= level)
    return row


def cell_events(m, partition, ref_min, hour):
    pa, pz = PARTS[partition]
    a = max(pa, m["start"])
    z = min(pz, m["end"])
    idx = m["idx"]
    hi = m["high"]
    lo = m["low"]
    rows = []
    if a >= z:
        return pd.DataFrame()

    day0 = a.normalize()
    day1 = (z - pd.Timedelta(minutes=5)).normalize()
    for day in pd.date_range(day0, day1, freq="D", tz="UTC"):
        es = day + pd.Timedelta(hours=hour)
        rs = es - pd.Timedelta(minutes=ref_min)
        ee = es + pd.Timedelta(minutes=XMIN)
        if rs < a or ee > z or rs < m["start"] or ee > m["end"]:
            continue
        ra = int(idx.searchsorted(rs, "left"))
        pos = int(idx.searchsorted(es, "left"))
        endpos = int(idx.searchsorted(ee, "left"))
        if ra >= len(idx) or pos >= len(idx) or endpos <= pos:
            continue
        if idx[ra] != rs or idx[pos] != es:
            continue
        if pos - ra != ref_min // BAR_MIN or endpos - pos != X_BARS:
            continue
        if idx[endpos - 1] != ee - pd.Timedelta(minutes=BAR_MIN):
            continue
        H = float(np.max(hi[ra:pos]))
        L = float(np.min(lo[ra:pos]))
        if not H > L:
            continue
        s = scan_session(m, pos, endpos, H, L)
        s.update({
            "partition": partition,
            "ref_min": ref_min,
            "hour": hour,
            "execution_start": es,
            "dev_block": dev_block(es),
            "H": H,
            "L": L,
            "R": H - L,
        })
        rows.append(s)
    return pd.DataFrame(rows)


def visit_stats(events: pd.DataFrame, partition: str, ref_min: int, hour: int):
    rows = []
    for j in VISITS:
        opp = events[events.visits_reached >= j]
        br = events[events.first_break_visit == j]
        row = {
            "partition": partition,
            "ref_min": ref_min,
            "hour": hour,
            "visit": j,
            "opportunity_n": len(opp),
            "break_n": len(br),
            "break_conversion": len(br) / len(opp) if len(opp) else np.nan,
            "median_extension_R": float(br.extension_before_reclaim_R.median()) if len(br) else np.nan,
            "median_ext30_R": float(br.ext30_R.median()) if len(br) else np.nan,
            "median_ext60_R": float(br.ext60_R.median()) if len(br) else np.nan,
            "median_break_delay_min": float(br.break_delay_min.median()) if len(br) else np.nan,
            "reclaim30_rate": float(br.reclaim30.mean()) if len(br) else np.nan,
        }
        for level in EXT_LEVELS:
            c = f"reach_E{int(level*100):02d}"
            row[f"{c}_rate"] = float(br[c].mean()) if len(br) else np.nan

        adequate = 0
        pass_blocks = 0
        convs = []
        for bi in range(6):
            b = events[events.dev_block == bi] if partition == "development" else pd.DataFrame()
            bo = b[b.visits_reached >= j] if len(b) else pd.DataFrame()
            bb = b[b.first_break_visit == j] if len(b) else pd.DataFrame()
            conv = len(bb) / len(bo) if len(bo) else np.nan
            row[f"b{bi+1}_opp_n"] = len(bo)
            row[f"b{bi+1}_break_conversion"] = conv
            if len(bo) >= 6:
                adequate += 1
                convs.append(conv)
                if conv >= 0.15:
                    pass_blocks += 1
        row["adequate_blocks"] = adequate
        row["pass_blocks"] = pass_blocks
        row["min_adequate_block_conversion"] = min(convs) if convs else np.nan
        row["eligible"] = bool(
            partition == "development"
            and len(opp) >= 60
            and adequate >= 5
            and row["break_conversion"] >= 0.20
            and pd.notna(row["median_extension_R"])
            and row["median_extension_R"] >= 0.10
            and pass_blocks >= 4
        )
        rows.append(row)
    return pd.DataFrame(rows)


def block_dominance(events: pd.DataFrame):
    out = {}
    for bi in range(6):
        b = events[events.dev_block == bi]
        vals = []
        for j in VISITS:
            opp = b[b.visits_reached >= j]
            br = b[b.first_break_visit == j]
            if len(opp) >= 6:
                vals.append((len(br) / len(opp), -j, j))
        out[bi] = max(vals)[2] if vals else 0
    return out


def summarize_dev_cell(events, ref_min, hour):
    vs = visit_stats(events, "development", ref_min, hour)
    q = vs[vs.eligible].copy()
    dom = 0
    if not q.empty:
        q["tie_bucket"] = (q.break_conversion / 0.01).round().astype(int)
        q = q.sort_values(
            ["break_conversion", "median_extension_R", "visit"],
            ascending=[False, False, True],
        )
        top = q.iloc[0]
        near = q[(top.break_conversion - q.break_conversion).abs() <= 0.01].copy()
        if not near.empty:
            top = near.sort_values(["median_extension_R", "visit"], ascending=[False, True]).iloc[0]
        dom = int(top.visit)

    bd = block_dominance(events)
    same_blocks = sum(1 for v in bd.values() if dom and v == dom)
    drow = vs[vs.visit == dom].iloc[0] if dom else None
    return vs, {
        "ref_min": ref_min,
        "hour": hour,
        "sessions_n": len(events),
        "dominant_visit": dom,
        "same_dom_blocks": same_blocks,
        "dominant_opportunity_n": int(drow.opportunity_n) if drow is not None else 0,
        "dominant_break_n": int(drow.break_n) if drow is not None else 0,
        "dominant_break_conversion": float(drow.break_conversion) if drow is not None else np.nan,
        "dominant_median_extension_R": float(drow.median_extension_R) if drow is not None else np.nan,
        "dominant_min_block_conversion": float(drow.min_adequate_block_conversion) if drow is not None else np.nan,
    }


def ref_neighbors(ref_min):
    i = REFS.index(ref_min)
    out = []
    if i > 0:
        out.append(REFS[i - 1])
    if i < len(REFS) - 1:
        out.append(REFS[i + 1])
    return out


def add_topology(atlas: pd.DataFrame):
    atlas = atlas.copy()
    clock_supports = []
    ref_supports = []
    topo = []
    for _, r in atlas.iterrows():
        dom = int(r.dominant_visit)
        if dom == 0:
            clock_supports.append("")
            ref_supports.append("")
            topo.append(False)
            continue
        hs = {(int(r.hour) - 1) % 24, (int(r.hour) + 1) % 24}
        cs = atlas[(atlas.ref_min == int(r.ref_min)) & atlas.hour.isin(hs) & (atlas.dominant_visit == dom)]
        rs = atlas[(atlas.hour == int(r.hour)) & atlas.ref_min.isin(ref_neighbors(int(r.ref_min))) & (atlas.dominant_visit == dom)]
        ctext = ",".join(str(int(x)) for x in sorted(cs.hour.unique()))
        rtext = ",".join(str(int(x)) for x in sorted(rs.ref_min.unique()))
        clock_supports.append(ctext)
        ref_supports.append(rtext)
        topo.append(bool(ctext and rtext))
    atlas["clock_support_hours"] = clock_supports
    atlas["ref_support_mins"] = ref_supports
    atlas["topology_supported"] = topo
    return atlas


def choose_central(atlas: pd.DataFrame):
    q = atlas[(atlas.topology_supported) & (atlas.same_dom_blocks >= 4)].copy()
    if q.empty:
        return None
    q = q.sort_values(
        [
            "same_dom_blocks",
            "dominant_min_block_conversion",
            "dominant_break_conversion",
            "dominant_median_extension_R",
            "dominant_opportunity_n",
            "ref_min",
            "hour",
        ],
        ascending=[False, False, False, False, False, True, True],
    )
    return q.iloc[0]


def choose_support(atlas, central, kind):
    dom = int(central.dominant_visit)
    if kind == "clock":
        vals = [int(x) for x in str(central.clock_support_hours).split(",") if x]
        q = atlas[(atlas.ref_min == int(central.ref_min)) & atlas.hour.isin(vals) & (atlas.dominant_visit == dom)].copy()
    else:
        vals = [int(x) for x in str(central.ref_support_mins).split(",") if x]
        q = atlas[(atlas.hour == int(central.hour)) & atlas.ref_min.isin(vals) & (atlas.dominant_visit == dom)].copy()
    if q.empty:
        return None
    return q.sort_values(
        ["same_dom_blocks", "dominant_break_conversion", "dominant_median_extension_R", "dominant_opportunity_n"],
        ascending=[False, False, False, False],
    ).iloc[0]


def oos_cell(m, partition, ref_min, hour, selected_visit):
    e = cell_events(m, partition, ref_min, hour)
    vs = visit_stats(e, partition, ref_min, hour)
    eligible_dom = vs[vs.opportunity_n >= 20].copy()
    oos_dom = 0
    if not eligible_dom.empty:
        oos_dom = int(eligible_dom.sort_values(["break_conversion", "visit"], ascending=[False, True]).iloc[0].visit)
    s = vs[vs.visit == selected_visit].iloc[0]
    return e, vs, {
        "partition": partition,
        "ref_min": ref_min,
        "hour": hour,
        "selected_visit": selected_visit,
        "oos_dominant_visit": oos_dom,
        "opportunity_n": int(s.opportunity_n),
        "break_n": int(s.break_n),
        "break_conversion": float(s.break_conversion) if pd.notna(s.break_conversion) else np.nan,
        "median_extension_R": float(s.median_extension_R) if pd.notna(s.median_extension_R) else np.nan,
        "reclaim30_rate": float(s.reclaim30_rate) if pd.notna(s.reclaim30_rate) else np.nan,
    }


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def num(v, d=3):
    return "-" if pd.isna(v) else f"{float(v):.{d}f}"


def main():
    x, coverage = load5()
    m = market(x)

    atlas_rows = []
    visit_frames = []
    dev_event_cache = {}
    for ref_min in REFS:
        for hour in HOURS:
            e = cell_events(m, "development", ref_min, hour)
            dev_event_cache[(ref_min, hour)] = e
            vs, ar = summarize_dev_cell(e, ref_min, hour)
            visit_frames.append(vs)
            atlas_rows.append(ar)

    visits = pd.concat(visit_frames, ignore_index=True)
    atlas = add_topology(pd.DataFrame(atlas_rows))
    visits.to_csv(OUT_VISITS, index=False)
    atlas.to_csv(OUT_ATLAS, index=False)

    central = choose_central(atlas)
    selected_rows = []
    event_frames = []
    all_oos_visit_frames = []

    if central is None:
        status = "SOL_LONG_VISIT_BREAK_A1_NO_STABLE_VISIT_STRUCTURE"
        pd.DataFrame().to_csv(OUT_SELECTED, index=False)
        pd.DataFrame().to_csv(OUT_EVENTS, index=False)
        lines = [
            "# SOL LONG Visit-Break Anatomy — A1 Result",
            "",
            f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
            "",
            f"Development habitat cells scanned: **{len(atlas)}**.",
            f"Topology-supported cells: **{int(atlas.topology_supported.sum())}**.",
            "",
            "## Decision",
            "",
            f"**Status: {status}**",
            "",
            "No Development cell produced a stable, topology-supported dominant H1-H5 breakout visit under the preregistered anatomy gates. Entry research is not authorized from A1.",
        ]
        OUT_MD.write_text("\n".join(lines) + "\n")
        OUT_STATUS.write_text(status + "\n")
        return

    dom = int(central.dominant_visit)
    clock_support = choose_support(atlas, central, "clock")
    ref_support = choose_support(atlas, central, "ref")
    chosen = [("CENTRAL", central), ("CLOCK_SUPPORT", clock_support), ("REF_SUPPORT", ref_support)]

    for role, r in chosen:
        if r is None:
            continue
        ref_min = int(r.ref_min)
        hour = int(r.hour)
        e = dev_event_cache[(ref_min, hour)].copy()
        e["role"] = role
        event_frames.append(e)
        v = visits[(visits.partition == "development") & (visits.ref_min == ref_min) & (visits.hour == hour) & (visits.visit == dom)].iloc[0]
        selected_rows.append({
            "role": role,
            "partition": "development",
            "ref_min": ref_min,
            "hour": hour,
            "selected_visit": dom,
            "oos_dominant_visit": dom,
            "opportunity_n": int(v.opportunity_n),
            "break_n": int(v.break_n),
            "break_conversion": float(v.break_conversion),
            "median_extension_R": float(v.median_extension_R),
            "reclaim30_rate": float(v.reclaim30_rate) if pd.notna(v.reclaim30_rate) else np.nan,
        })

    central_oos_ok = True
    support_role_ok = {"CLOCK_SUPPORT": True, "REF_SUPPORT": True}
    for role, r in chosen:
        if r is None:
            if role != "CENTRAL":
                support_role_ok[role] = False
            continue
        ref_min = int(r.ref_min)
        hour = int(r.hour)
        for partition in ("external", "reference_validation"):
            e, ovs, row = oos_cell(m, partition, ref_min, hour, dom)
            e["role"] = role
            event_frames.append(e)
            ovs["role"] = role
            all_oos_visit_frames.append(ovs)
            row["role"] = role
            selected_rows.append(row)
            same_dom = int(row["oos_dominant_visit"]) == dom
            if role == "CENTRAL":
                gate = bool(
                    row["opportunity_n"] >= 20
                    and row["break_conversion"] >= 0.15
                    and row["median_extension_R"] >= 0.08
                    and same_dom
                )
                central_oos_ok = central_oos_ok and gate
            else:
                support_role_ok[role] = support_role_ok[role] and bool(row["opportunity_n"] >= 20 and same_dom)

    selected = pd.DataFrame(selected_rows)
    selected.to_csv(OUT_SELECTED, index=False)
    events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame()
    events.to_csv(OUT_EVENTS, index=False)

    supported = bool(central_oos_ok and support_role_ok["CLOCK_SUPPORT"] and support_role_ok["REF_SUPPORT"])
    status = "SOL_LONG_VISIT_BREAK_A1_SUPPORTED" if supported else "SOL_LONG_VISIT_BREAK_A1_FAILED_OOS"

    central_dev = selected[(selected.role == "CENTRAL") & (selected.partition == "development")].iloc[0]
    c_ext = selected[(selected.role == "CENTRAL") & (selected.partition == "external")].iloc[0]
    c_val = selected[(selected.role == "CENTRAL") & (selected.partition == "reference_validation")].iloc[0]

    dev_cell_visits = visits[(visits.partition == "development") & (visits.ref_min == int(central.ref_min)) & (visits.hour == int(central.hour))].copy()
    lines = [
        "# SOL LONG Visit-Break Anatomy — A1 Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "",
        "A1 asks only: **which distinct High visit becomes the upside breakout?** No entry, stop, TP, PnL, leverage, or fees are used.",
        "",
        f"Development habitat cells scanned: **{len(atlas)}** = {len(REFS)} references × 24 UTC clocks.",
        f"Topology-supported cells: **{int(atlas.topology_supported.sum())}**.",
        "",
        "## Frozen Development structure",
        "",
        f"- Reference: **R{int(central.ref_min)}**.",
        f"- Execution start: **{int(central.hour):02d}:00 UTC**.",
        f"- Dominant breakout visit: **H{dom}**.",
        f"- Same H{dom} dominant in **{int(central.same_dom_blocks)}/6** Development half-year blocks.",
        f"- H{dom} opportunity N: **{int(central_dev.opportunity_n)}**.",
        f"- H{dom} breakout conversion: **{pct(central_dev.break_conversion)}**.",
        f"- Median post-break extension before reclaim: **{num(central_dev.median_extension_R)}R**.",
        "",
        "## H1-H5 anatomy at the frozen Development habitat",
        "",
        "| Visit | Opportunity N | First-break N | Break conversion | Median extension | Reclaim <=30m |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in dev_cell_visits.iterrows():
        lines.append(
            f"| H{int(r.visit)} | {int(r.opportunity_n)} | {int(r.break_n)} | {pct(r.break_conversion)} | {num(r.median_extension_R)}R | {pct(r.reclaim30_rate)} |"
        )

    lines += [
        "",
        "## OOS central confirmation",
        "",
        "| Partition | Dominant visit | H-selected opportunity | Break conversion | Median extension |",
        "|---|---:|---:|---:|---:|",
        f"| External | H{int(c_ext.oos_dominant_visit) if int(c_ext.oos_dominant_visit) else '-'} | {int(c_ext.opportunity_n)} | {pct(c_ext.break_conversion)} | {num(c_ext.median_extension_R)}R |",
        f"| Reference Validation | H{int(c_val.oos_dominant_visit) if int(c_val.oos_dominant_visit) else '-'} | {int(c_val.opportunity_n)} | {pct(c_val.break_conversion)} | {num(c_val.median_extension_R)}R |",
        "",
        "## Topology support",
        "",
        f"- Frozen clock support: **{int(clock_support.hour):02d}:00 UTC / R{int(clock_support.ref_min)}**." if clock_support is not None else "- Frozen clock support: none.",
        f"- Frozen reference support: **R{int(ref_support.ref_min)} / {int(ref_support.hour):02d}:00 UTC**." if ref_support is not None else "- Frozen reference support: none.",
        f"- Clock support preserves H{dom} in both OOS partitions: **{'YES' if support_role_ok['CLOCK_SUPPORT'] else 'NO'}**.",
        f"- Reference support preserves H{dom} in both OOS partitions: **{'YES' if support_role_ok['REF_SUPPORT'] else 'NO'}**.",
        "",
        "## Decision",
        "",
        f"**Status: {status}**",
        "",
    ]
    if supported:
        lines += [
            f"The preregistered evidence supports **H{dom} as the stable SOL LONG breakout visit** for the frozen habitat/topology. H{dom} is a structural breakout location, not an entry rule.",
            "",
            "A2 is authorized to ask the next question: **where should the entry occur relative to the path leading into that breakout visit?**",
        ]
    else:
        lines += [
            f"Development identified H{dom}, but the exact visit-order structure did not survive every frozen OOS/topology gate. Do not proceed to entry optimization from this candidate without a new preregistered structural hypothesis.",
        ]
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(status + "\n")


if __name__ == "__main__":
    main()
