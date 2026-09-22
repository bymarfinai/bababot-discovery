#!/usr/bin/env python3
"""Deterministic fixture validation for SOL Options Liquidity Map V1."""

from pathlib import Path
import json
import math

from sol_options_liquidity_map import build_map, MAP_VERSION

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "research/data/sol_options_v1/2026-09-22T02-29-31-999Z.json"


def close(a, b, tol=1e-9):
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol)


def main():
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw = saved["raw_chain"]
    spot = saved["spot"]
    snap_ms = int(saved["snapshot_time_ms"] if "snapshot_time_ms" in saved else 1790044171999)

    # Reconstruct exactly the public API input shapes needed by build_map.
    option_symbols = []
    marks = []
    oi_by_expiry = {}

    for x in raw:
        option_symbols.append({
            "symbol": x["symbol"],
            "underlying": "SOLUSDT",
            "status": "TRADING",
            "expiryDate": int(x["expiry_time_ms"]),
            "side": x["side"],
            "strikePrice": str(x["strike"]),
        })
        marks.append({
            "symbol": x["symbol"],
            "markPrice": str(x["markPrice"]),
            "bidIV": str(x["bidIV"]),
            "askIV": str(x["askIV"]),
            "markIV": str(x["markIV"]),
            "delta": str(x["delta"]),
            "gamma": str(x["gamma"]),
            "vega": str(x["vega"]),
            "theta": str(x["theta"]),
        })
        oi_by_expiry.setdefault(x["expiry_code"], []).append({
            "symbol": x["symbol"],
            "sumOpenInterest": str(x["open_interest"]),
            "sumOpenInterestUsd": str(x["open_interest_usd"]),
            "timestamp": str(snap_ms),
        })

    inputs = {
        "exchange_info": {"optionSymbols": option_symbols},
        "marks": marks,
        "index": {"indexPrice": str(spot), "time": snap_ms},
        "oi_by_expiry": oi_by_expiry,
    }

    rebuilt = build_map(inputs)

    assert rebuilt["map_version"] == MAP_VERSION
    assert rebuilt["status"] == saved["status"]
    assert close(rebuilt["spot"], saved["spot"])
    assert [e["code"] for e in rebuilt["expiries"]] == [e["code"] for e in saved["expiries"]]
    assert rebuilt["counts"]["chain_rows"] == saved["counts"]["chain_rows"]

    for key in ("iv_bands", "lower_put_concentration", "upper_call_concentration"):
        assert len(rebuilt[key]) == len(saved[key]), (key, len(rebuilt[key]), len(saved[key]))

    for a, b in zip(rebuilt["iv_bands"], saved["iv_bands"]):
        assert a["expiry"] == b["expiry"]
        for k in ("atm_strike", "atm_mark_iv", "expected_move", "iv_floor", "iv_ceiling"):
            assert close(a[k], b[k], 1e-8), (k, a[k], b[k])

    for key in ("lower_put_concentration", "upper_call_concentration"):
        for a, b in zip(rebuilt[key], saved[key]):
            assert close(a["strike"], b["strike"])
            assert close(a["concentration_score"], b["concentration_score"], 1e-10)
            assert a["confluence_label"] == b["confluence_label"]

    print("SOL_OPTIONS_LIQUIDITY_MAP_V1_FIXTURE_PASS")
    print("spot", rebuilt["spot"])
    print("lower", [(x["strike"], round(x["concentration_score"], 6), x["confluence_label"]) for x in rebuilt["lower_put_concentration"]])
    print("upper", [(x["strike"], round(x["concentration_score"], 6), x["confluence_label"]) for x in rebuilt["upper_call_concentration"]])


if __name__ == "__main__":
    main()
