#!/usr/bin/env python3
"""Hourly append-only capture for SOL Options Liquidity Map V1."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sol_options_liquidity_map import build_map, fetch_live_inputs

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "research" / "data" / "sol_options_v1"


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    payload = build_map(fetch_live_inputs())
    ts = datetime.fromtimestamp(
        int(payload["snapshot_time_ms"]) / 1000,
        tz=timezone.utc,
    )
    filename = ts.isoformat(timespec="milliseconds").replace(":", "-").replace("+00-00", "Z") + ".json"
    out = OUTDIR / filename

    if out.exists():
        print("SNAPSHOT_ALREADY_EXISTS", out.relative_to(ROOT))
        return 0

    out.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print("SOL_OPTIONS_HOURLY_CAPTURE_OK")
    print("snapshot_id", payload["snapshot_id"])
    print("snapshot_time_utc", payload["snapshot_time_utc"])
    print("spot", payload["spot"])
    print("status", payload["status"])
    print("path", out.relative_to(ROOT))
    print(
        "lower",
        [(x["strike"], round(x["concentration_score"], 6)) for x in payload["lower_put_concentration"]],
    )
    print(
        "upper",
        [(x["strike"], round(x["concentration_score"], 6)) for x in payload["upper_call_concentration"]],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
