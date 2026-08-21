#!/usr/bin/env python3
"""Access/coverage preflight for W1_VAH_MICRO_R1.

This script deliberately does NOT inspect candidate labels. It probes temporal
coverage and data entitlement before any winner/loser microstructure analysis.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import traceback

import pandas as pd

from coindesk_microstructure import (
    CoinDeskAccessError,
    CoinDeskCoverageError,
    CoinDeskMicrostructureClient,
)

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Candidates.csv"
OUT_JSON = ROOT / "BTC_WEEKLY_W1_VAH_MICROSTRUCTURE_R1_Preflight.json"
OUT_MD = ROOT / "BTC_WEEKLY_W1_VAH_MICROSTRUCTURE_R1_Preflight.md"
PARTITIONS = ("external", "development", "reference_validation")
PROBE_MINUTES = int(os.getenv("R1_PREFLIGHT_MINUTES", "5"))
DEPTH = int(os.getenv("R1_L2_DEPTH", "1000"))


def pick_probes(df: pd.DataFrame) -> list[dict]:
    probes = []
    for part in PARTITIONS:
        q = df[df.partition == part].sort_values("entry_ts").reset_index(drop=True)
        if q.empty:
            continue
        idx = sorted(set([0, len(q) // 2, len(q) - 1]))
        for i in idx:
            r = q.iloc[i]
            probes.append({
                "partition": part,
                "week": str(r.week),
                "entry_ts": str(r.entry_ts),
                "level": float(r.level),
            })
    return probes


def write_result(out: dict) -> None:
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    lines = [
        "# BTC Weekly W1 VAH True Microstructure R1 — Preflight",
        "",
        f"**Status: {out['status']}**",
        "",
        f"Market: `{out.get('market', '-')}`  ",
        f"Instrument: `{out.get('instrument', '-')}`  ",
        f"Probe window: **{PROBE_MINUTES} minutes** before entry  ",
        f"Requested L2 depth: **{DEPTH}**",
        "",
        "This is an access/coverage probe only. Candidate outcomes were not inspected.",
        "",
    ]
    if out.get("message"):
        lines += ["## Message", "", str(out["message"]), ""]
    rows = out.get("probes", [])
    if rows:
        lines += [
            "## Temporal probes",
            "",
            "| Partition | Week | Entry | L2 | Updates | Trades | OI updates | Error |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r.get('partition')} | {r.get('week')} | {r.get('entry_ts')} | "
                f"{1 if r.get('l2_ok') else 0} | {r.get('l2_updates', 0)} | "
                f"{r.get('trade_count', 0)} | {r.get('oi_count', 0)} | {str(r.get('error', '')).replace('|', '/')} |"
            )
        lines += [""]
    lines += [
        "## Interpretation",
        "",
        "- `PREFLIGHT_PASS` means the configured account/instrument returned usable L2 replay and tick trades across the sampled historical dates. It is **not** a strategy result.",
        "- `BLOCKED_DATA_ACCESS` means credentials, role, instrument mapping, or entitlement must be fixed before research can run.",
        "- `BLOCKED_DATA_COVERAGE` means the source did not return required L2/trade data for at least one sampled historical period.",
        "- Full >=90% per-partition coverage is still required by the preregistration before label analysis.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    base = {
        "protocol": "W1_VAH_MICRO_R1_PREFLIGHT",
        "status": "BLOCKED_DATA_ACCESS",
        "market": os.getenv("COINDESK_FUTURES_MARKET", "binance"),
        "instrument": os.getenv("COINDESK_FUTURES_INSTRUMENT", "BTC-USDT-VANILLA-PERPETUAL"),
        "probe_minutes": PROBE_MINUTES,
        "depth": DEPTH,
        "probes": [],
        "labels_inspected": False,
    }
    if not CANDIDATES.exists():
        base["message"] = f"Missing frozen candidate file: {CANDIDATES.name}"
        write_result(base)
        return 0
    try:
        client = CoinDeskMicrostructureClient.from_env()
        base["market"] = client.market
        base["instrument"] = client.instrument
        metadata = client.instrument_metadata()
        base["metadata_resolved"] = bool(metadata)
    except CoinDeskAccessError as e:
        base["message"] = str(e)
        write_result(base)
        return 0
    except Exception as e:
        base["message"] = f"Metadata preflight failed: {type(e).__name__}: {e}"
        write_result(base)
        return 0

    df = pd.read_csv(CANDIDATES, usecols=["week", "entry_ts", "level", "partition"])
    probes = pick_probes(df)
    if len(probes) < len(PARTITIONS):
        base["status"] = "BLOCKED_DATA_COVERAGE"
        base["message"] = "Frozen candidate file did not contain all required partitions"
        write_result(base)
        return 0

    access_errors = 0
    coverage_errors = 0
    for p in probes:
        row = dict(p)
        end = pd.Timestamp(p["entry_ts"])
        start = end - pd.Timedelta(minutes=PROBE_MINUTES)
        try:
            l2 = client.replay_l2_features(start, end, p["level"], depth=DEPTH)
            row["l2_ok"] = bool(l2.get("l2_snapshots", 0) >= 1 and l2.get("l2_updates", 0) > 0)
            row["l2_updates"] = int(l2.get("l2_updates", 0))
            row["l2_ccseq_gaps"] = int(l2.get("l2_ccseq_gaps", 0))
            trades = client.trades(start, end)
            row["trade_count"] = len(trades)
            oi = client.open_interest(start, end)
            row["oi_count"] = len(oi)
            if not row["l2_ok"] or row["trade_count"] <= 0:
                coverage_errors += 1
                row["error"] = "required L2/trade layer empty"
        except CoinDeskAccessError as e:
            access_errors += 1
            row["l2_ok"] = False
            row["error"] = f"ACCESS: {e}"
        except CoinDeskCoverageError as e:
            coverage_errors += 1
            row["l2_ok"] = False
            row["error"] = f"COVERAGE: {e}"
        except Exception as e:
            coverage_errors += 1
            row["l2_ok"] = False
            row["error"] = f"TECHNICAL: {type(e).__name__}: {e}"
            row["trace_tail"] = traceback.format_exc().splitlines()[-3:]
        base["probes"].append(row)

    if access_errors:
        base["status"] = "BLOCKED_DATA_ACCESS"
        base["message"] = f"{access_errors} temporal probes hit access/entitlement errors"
    elif coverage_errors:
        base["status"] = "BLOCKED_DATA_COVERAGE"
        base["message"] = f"{coverage_errors} temporal probes lacked required historical L2/trade data"
    else:
        base["status"] = "PREFLIGHT_PASS"
        base["message"] = "Temporal entitlement/coverage probes passed; full coverage scan is authorized next"
    write_result(base)
    print(json.dumps(base, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
