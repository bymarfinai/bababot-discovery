#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B30_S2_ENTRY_ARCHETYPE"
FP = ROOT / "frozen_a1" / "BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz"
FP_SHA256 = "eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa"
FP_ROWS = 229_267
STEP = pd.Timedelta(minutes=15)
COOLDOWN = pd.Timedelta(minutes=60)
START = pd.Timestamp("2022-01-01T00:00:00Z")
END = pd.Timestamp("2026-08-26T00:00:00Z")
DEV_YEARS = [2022, 2023, 2024]
REF_YEARS = [2025, 2026]
EPS = 1e-12

DETECTORS = [
    ("S01", "SWEEP_LOW_RECLAIM", "LONG", 8092),
    ("S02", "HL_CONTINUATION", "LONG", 797),
    ("S03", "BREAK_HIGH_HOLD", "LONG", 1577),
    ("S04", "FAILED_BREAKDOWN_RECLAIM", "LONG", 5109),
    ("S05", "SWEEP_HIGH_REJECT", "SHORT", 8542),
    ("S06", "LH_CONTINUATION", "SHORT", 637),
    ("S07", "BREAK_LOW_HOLD", "SHORT", 1207),
    ("S08", "FAILED_BREAKOUT_REJECT", "SHORT", 5553),
]
POLICIES = [
    ("E0", "STRUCTURE_CLOSE"),
    ("E1", "DELAY_15"),
    ("E2", "ONE_BAR_DIRECTION_CONFIRM"),
    ("E3", "FIRST_PATH_CONTINUATION_30"),
    ("E4", "FIRST_LIQUIDITY_BREAK_30"),
]
HORIZONS = [30, 60, 120]


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_lcb(hits: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return np.nan
    p = hits / n
    den = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (center - margin) / den


def load_fp() -> pd.DataFrame:
    if not FP.exists():
        raise FileNotFoundError(FP)
    digest = file_sha(FP)
    x = pd.read_csv(FP, compression="gzip", low_memory=False)
    x["decision_ts"] = pd.to_datetime(x["decision_ts"], utc=True, errors="raise")
    x = x.set_index("decision_ts").sort_index()
    for c in ["ret_15", "sweep_low_60", "sweep_high_60", "break_low_60", "break_high_60", "close_location"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    if digest != FP_SHA256 or len(x) != FP_ROWS or x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise RuntimeError(f"immutable A1 integrity failure hash={digest} rows={len(x)}")
    return x


def predecessor(x: pd.DataFrame) -> pd.DataFrame:
    p = x.reindex(x.index - STEP).copy()
    p.index = x.index
    return p


def raw_masks(x: pd.DataFrame) -> dict[str, pd.Series]:
    pre = predecessor(x)
    exact = pd.Series((x.index - STEP).isin(x.index), index=x.index)
    return {
        "S01": x["sweep_low_60"].eq(1.0),
        "S02": exact & pre["path_state"].eq("PULLBACK_FROM_UP") & x["path_state"].eq("CONT_UP") & x["structure_state"].eq("HH_HL"),
        "S03": exact & pre["break_high_60"].eq(1.0) & x["break_high_60"].eq(1.0),
        "S04": exact & pre["break_low_60"].eq(1.0) & x["break_low_60"].eq(0.0) & x["close_location"].gt(0.0),
        "S05": x["sweep_high_60"].eq(1.0),
        "S06": exact & pre["path_state"].eq("PULLBACK_FROM_DOWN") & x["path_state"].eq("CONT_DOWN") & x["structure_state"].eq("LH_LL"),
        "S07": exact & pre["break_low_60"].eq(1.0) & x["break_low_60"].eq(1.0),
        "S08": exact & pre["break_high_60"].eq(1.0) & x["break_high_60"].eq(0.0) & x["close_location"].lt(0.0),
    }


def cooldown(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    out = []
    last = None
    for ts in idx.sort_values():
        if last is None or ts - last >= COOLDOWN:
            out.append(ts)
            last = ts
    return pd.DatetimeIndex(out)


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    masks = raw_masks(x)
    rows = []
    for sid, name, direction, expected in DETECTORS:
        idx = pd.DatetimeIndex(x.index[masks[sid]])
        idx = idx[(idx >= START) & (idx <= END)]
        idx = cooldown(idx)
        if len(idx) != expected:
            raise RuntimeError(f"parent identity mismatch {sid}: expected {expected}, got {len(idx)}")
        for ts in idx:
            rows.append({"structure_ts": ts, "structure_id": sid, "structure": name, "direction": direction, "structure_year": ts.year})
    return pd.DataFrame(rows).sort_values(["structure_id", "structure_ts"]).reset_index(drop=True)


def build_forward(x: pd.DataFrame) -> dict[int, pd.Series]:
    r = x["ret_15"].astype(float)
    out = {}
    for h in HORIZONS:
        steps = h // 15
        growth = pd.Series(1.0, index=x.index, dtype=float)
        valid = pd.Series(True, index=x.index, dtype=bool)
        for i in range(1, steps + 1):
            rr = r.reindex(x.index + i * STEP)
            rr.index = x.index
            valid &= rr.notna()
            growth *= 1.0 + rr.fillna(0.0)
        f = (growth - 1.0).where(valid)
        f = f.mask(f.abs() <= EPS, 0.0)
        out[h] = f
    return out


def choose_entry(x: pd.DataFrame, ts: pd.Timestamp, direction: str, pid: str) -> pd.Timestamp | pd.NaT:
    sign = 1.0 if direction == "LONG" else -1.0
    if pid == "E0":
        return ts if ts in x.index else pd.NaT
    t15 = ts + STEP
    if t15 not in x.index:
        return pd.NaT
    if pid == "E1":
        return t15
    if pid == "E2":
        v = float(x.at[t15, "ret_15"])
        return t15 if sign * v > EPS else pd.NaT
    if pid == "E3":
        target = "CONT_UP" if direction == "LONG" else "CONT_DOWN"
        for k in (1, 2):
            q = ts + k * STEP
            if q not in x.index:
                return pd.NaT if k == 1 else pd.NaT
            if str(x.at[q, "path_state"]) == target:
                return q
        return pd.NaT
    if pid == "E4":
        col = "break_high_60" if direction == "LONG" else "break_low_60"
        for k in (1, 2):
            q = ts + k * STEP
            if q not in x.index:
                return pd.NaT if k == 1 else pd.NaT
            if float(x.at[q, col]) == 1.0:
                return q
        return pd.NaT
    raise KeyError(pid)


def build_entries(x: pd.DataFrame, events: pd.DataFrame, fwds: dict[int, pd.Series]) -> pd.DataFrame:
    rows = []
    for ev in events.itertuples(index=False):
        side = 1.0 if ev.direction == "LONG" else -1.0
        for pid, pname in POLICIES:
            ets = choose_entry(x, ev.structure_ts, ev.direction, pid)
            row = {
                "structure_ts": ev.structure_ts,
                "structure_id": ev.structure_id,
                "structure": ev.structure,
                "direction": ev.direction,
                "structure_year": ev.structure_year,
                "policy_id": pid,
                "policy": pname,
                "entry_ts": ets,
            }
            if pd.isna(ets):
                for h in HORIZONS:
                    row[f"signed_{h}"] = np.nan
                    row[f"hit_{h}"] = False
            else:
                for h in HORIZONS:
                    raw = fwds[h].get(ets, np.nan)
                    signed = side * raw if pd.notna(raw) else np.nan
                    if pd.notna(signed) and abs(signed) <= EPS:
                        signed = 0.0
                    row[f"signed_{h}"] = signed
                    row[f"hit_{h}"] = bool(pd.notna(signed) and signed > EPS)
            rows.append(row)
    return pd.DataFrame(rows)


def metric_row(z: pd.DataFrame, parent_n: int, years: list[int]) -> dict:
    valid = z[z["signed_60"].notna()].copy()
    n = len(valid)
    hits = int(valid["hit_60"].sum())
    by_n, by_hit = {}, {}
    for y in years:
        yy = valid[valid.structure_year == y]
        by_n[y] = len(yy)
        by_hit[y] = float(yy.hit_60.mean()) if len(yy) else np.nan
    return {
        "n": n,
        "parent_n": parent_n,
        "participation": n / parent_n if parent_n else np.nan,
        "hit_60": hits / n if n else np.nan,
        "wilson_60": wilson_lcb(hits, n),
        "median_signed_60": float(valid.signed_60.median()) if n else np.nan,
        "hit_30": float(valid.hit_30.mean()) if n else np.nan,
        "hit_120": float(valid.hit_120.mean()) if n else np.nan,
        **{f"n_{y}": by_n[y] for y in years},
        **{f"hit_{y}": by_hit[y] for y in years},
    }


def dev_table(entries: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, name, direction, _ in DETECTORS:
        parent = events[(events.structure_id == sid) & events.structure_year.isin(DEV_YEARS)]
        for pid, pname in POLICIES:
            z = entries[(entries.structure_id == sid) & entries.policy_id.eq(pid) & entries.structure_year.isin(DEV_YEARS)]
            m = metric_row(z, len(parent), DEV_YEARS)
            hits_year = [m[f"hit_{y}"] for y in DEV_YEARS]
            aux_ge53 = sum(pd.notna(m[f"hit_{h}"]) and m[f"hit_{h}"] >= 0.53 for h in (30, 120))
            gate = (
                m["n"] >= 120
                and min(m[f"n_{y}"] for y in DEV_YEARS) >= 25
                and m["participation"] >= 0.35
                and m["hit_60"] >= 0.55
                and m["wilson_60"] > 0.50
                and min(hits_year) >= 0.52
                and m["median_signed_60"] > 0.0
                and aux_ge53 >= 1
            )
            rows.append({
                "structure_id": sid, "structure": name, "direction": direction,
                "policy_id": pid, "policy": pname,
                **m,
                "worst_dev_hit": min(hits_year),
                "aux_ge53": aux_ge53,
                "dev_gate": gate,
            })
    return pd.DataFrame(rows)


def select_winners(dev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, name, direction, _ in DETECTORS:
        z = dev[(dev.structure_id == sid) & dev.dev_gate].copy()
        if not len(z):
            rows.append({"structure_id": sid, "structure": name, "direction": direction, "selection_status": "NO_ENTRY_ARCHETYPE_FOUND"})
            continue
        z = z.sort_values(["worst_dev_hit", "wilson_60", "hit_60", "participation", "policy_id"], ascending=[False, False, False, False, True])
        r = z.iloc[0].to_dict()
        r["selection_status"] = "SELECTED_FOR_REFERENCE"
        rows.append(r)
    return pd.DataFrame(rows)


def evaluate_reference(entries: pd.DataFrame, events: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in selected.itertuples(index=False):
        if s.selection_status != "SELECTED_FOR_REFERENCE":
            rows.append({
                "structure_id": s.structure_id, "structure": s.structure, "direction": s.direction,
                "policy_id": None, "policy": None, "status": "NO_ENTRY_ARCHETYPE_FOUND",
            })
            continue
        parent = events[(events.structure_id == s.structure_id) & events.structure_year.isin(REF_YEARS)]
        z = entries[(entries.structure_id == s.structure_id) & entries.policy_id.eq(s.policy_id) & entries.structure_year.isin(REF_YEARS)]
        m = metric_row(z, len(parent), REF_YEARS)
        aux_ge52 = sum(pd.notna(m[f"hit_{h}"]) and m[f"hit_{h}"] >= 0.52 for h in (30, 120))
        gate = (
            m["n_2025"] >= 20 and m["n_2026"] >= 15
            and m["participation"] >= 0.35
            and m["hit_60"] >= 0.53
            and m["hit_2025"] > 0.50
            and m["hit_2026"] > 0.50
            and m["median_signed_60"] > 0.0
            and aux_ge52 >= 1
        )
        rows.append({
            "structure_id": s.structure_id, "structure": s.structure, "direction": s.direction,
            "policy_id": s.policy_id, "policy": s.policy,
            **m, "aux_ge52": aux_ge52,
            "status": "ENTRY_ARCHETYPE_PASS" if gate else "ENTRY_ARCHETYPE_REJECT",
        })
    return pd.DataFrame(rows)


def pct(v) -> str:
    return "—" if pd.isna(v) else f"{100*v:.2f}%"


def render(dev: pd.DataFrame, selected: pd.DataFrame, ref: pd.DataFrame) -> str:
    n_pass = int((ref.status == "ENTRY_ARCHETYPE_PASS").sum())
    status = "BNB_B30_S2_ENTRY_ARCHETYPES_FOUND" if n_pass else "BNB_B30_S2_NO_ENTRY_ARCHETYPE_PASSED"
    lines = [
        "# BNB B30-S2 — Per-Structure Entry Archetype Discovery Result", "",
        f"**Status: {status}**", "",
        "S1 structure definitions are unchanged. S2 tests only preregistered causal entry archetypes and directional close-to-close behavior. No TP/SL, excursion, PnL or other economics is evaluated.", "",
        "## Development winners", "",
        "| Structure | Selected policy | Dev N | Participation | +60 hit | Wilson LCB | Worst dev era | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in selected.itertuples(index=False):
        if s.selection_status != "SELECTED_FOR_REFERENCE":
            lines.append(f"| {s.structure_id} {s.structure} | — | — | — | — | — | — | {s.selection_status} |")
        else:
            lines.append(f"| {s.structure_id} {s.structure} | {s.policy_id} {s.policy} | {int(s.n)} | {pct(s.participation)} | {pct(s.hit_60)} | {pct(s.wilson_60)} | {pct(s.worst_dev_hit)} | SELECTED |")
    lines += ["", "## One-shot 2025–2026 reference", "", "| Structure | Frozen entry | Ref N | Part. | +60 hit | 2025 | 2026 | +30 | +120 | Status |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in ref.itertuples(index=False):
        if r.status == "NO_ENTRY_ARCHETYPE_FOUND":
            lines.append(f"| {r.structure_id} {r.structure} | — | — | — | — | — | — | — | — | {r.status} |")
        else:
            lines.append(f"| {r.structure_id} {r.structure} | {r.policy_id} {r.policy} | {int(r.n)} | {pct(r.participation)} | {pct(r.hit_60)} | {pct(r.hit_2025)} | {pct(r.hit_2026)} | {pct(r.hit_30)} | {pct(r.hit_120)} | {r.status} |")
    lines += ["", "## Decision", f"**{status}**", "", f"Structures with a frozen entry archetype passing one-shot reference: **{n_pass}/8**.", "Only PASS pairs may advance to S3 economics. A PASS here is directional entry evidence, not a trading win rate and not authorization for live orders.", "", "No live orders were placed."]
    return "\n".join(lines) + "\n"


def main() -> None:
    x = load_fp()
    events = build_events(x)
    fwds = build_forward(x)
    entries = build_entries(x, events, fwds)
    dev = dev_table(entries, events)
    selected = select_winners(dev)
    ref = evaluate_reference(entries, events, selected)
    result = render(dev, selected, ref)

    dev.to_csv(ROOT / f"{PFX}_Development.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_Selected.csv", index=False)
    ref.to_csv(ROOT / f"{PFX}_Reference.csv", index=False)
    # Compact entry ledger has no economics; keep only causal timestamps and directional endpoint fields.
    entries.to_csv(ROOT / f"{PFX}_Entries.csv.gz", index=False, compression="gzip")
    (ROOT / f"{PFX}_Result.md").write_text(result, encoding="utf-8")
    status = "BNB_B30_S2_ENTRY_ARCHETYPES_FOUND" if (ref.status == "ENTRY_ARCHETYPE_PASS").any() else "BNB_B30_S2_NO_ENTRY_ARCHETYPE_PASSED"
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print(result, flush=True)


if __name__ == "__main__":
    main()
