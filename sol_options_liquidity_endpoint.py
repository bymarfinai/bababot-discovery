"""FastAPI endpoints for SOL Options Liquidity Map V1."""

import os
import threading
import time
from fastapi import APIRouter, HTTPException, Query

from sol_options_liquidity_map import (
    build_map,
    capture_live_snapshot,
    fetch_live_inputs,
    latest_snapshot_before,
    list_snapshots,
)

router = APIRouter(prefix="/v5/sol-options", tags=["sol_options_liquidity_v1"])

DB_PATH = os.environ.get("DB_PATH", "market_data.db")
_CAPTURE_THREAD = None
_CAPTURE_LOCK = threading.Lock()


@router.get("/map")
def current_map():
    """Fetch and calculate the current V1 map without persisting it."""
    try:
        return build_map(fetch_live_inputs())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OPTIONS_MAP_FETCH_ERROR: {exc}")


@router.post("/capture")
def capture_map():
    """Fetch current chain, build map and append it to snapshot storage."""
    try:
        return capture_live_snapshot(DB_PATH)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OPTIONS_MAP_FETCH_ERROR: {exc}")


@router.get("/snapshots")
def snapshots(limit: int = Query(100, ge=1, le=1000)):
    return {
        "map_version": "SOL_OPTIONS_LIQUIDITY_MAP_V1",
        "db_path": DB_PATH,
        "snapshots": list_snapshots(DB_PATH, limit),
    }


@router.get("/snapshot-before")
def snapshot_before(decision_time_ms: int):
    """Causal lookup: latest snapshot at or before a detector decision timestamp."""
    payload = latest_snapshot_before(DB_PATH, decision_time_ms)
    return {
        "decision_time_ms": int(decision_time_ms),
        "found": payload is not None,
        "snapshot": payload,
    }


def _capture_loop(interval_seconds: int):
    while True:
        try:
            result = capture_live_snapshot(DB_PATH)
            meta = result.get("storage", {})
            print(
                "[SOL_OPTIONS_V1] capture",
                meta.get("snapshot_id"),
                "inserted=" + str(meta.get("inserted")),
            )
        except Exception as exc:
            print("[SOL_OPTIONS_V1] capture error:", exc)
        time.sleep(interval_seconds)


def start_sol_options_capture():
    """Optional prospective logger.

    Enable with SOL_OPTIONS_CAPTURE_ENABLED=true.
    Default interval is 300 seconds and cannot be configured below 60 seconds.
    """
    global _CAPTURE_THREAD
    enabled = os.environ.get("SOL_OPTIONS_CAPTURE_ENABLED", "false").lower() == "true"
    if not enabled:
        print("[SOL_OPTIONS_V1] background capture disabled")
        return

    interval = max(60, int(os.environ.get("SOL_OPTIONS_CAPTURE_SECONDS", "300")))

    with _CAPTURE_LOCK:
        if _CAPTURE_THREAD is not None and _CAPTURE_THREAD.is_alive():
            return
        _CAPTURE_THREAD = threading.Thread(
            target=_capture_loop,
            args=(interval,),
            name="sol-options-v1-capture",
            daemon=True,
        )
        _CAPTURE_THREAD.start()
        print(f"[SOL_OPTIONS_V1] background capture started every {interval}s")
