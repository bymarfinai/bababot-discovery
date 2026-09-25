"""Moving Coin Detector V1 for Binance USD-M perpetual futures.

Purpose
-------
Find liquid USDT perpetual pairs that are *starting* to move, then assign
independent LONG_SCORE and SHORT_SCORE values. The detector is intentionally
an upstream market scanner: it does not place trades and it does not replace
BabaBot's downstream regime/entry logic.

Design constraints
------------------
* Closed 5m candles only (no in-progress candle leakage).
* Public Binance endpoints only; no API key required.
* Symmetric long/short scoring.
* Fresh-position confirmation via open-interest change.
* Aggressive-flow confirmation via taker buy/sell ratio.
* Already-extended moves are penalized to reduce chase risk.
* Outputs are deterministic given the same exchange snapshot.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional

import requests

UM_BASE = "https://fapi.binance.com"


@dataclass(frozen=True)
class DetectorConfig:
    interval: str = "5m"
    kline_limit: int = 80
    universe_size: int = 40
    min_quote_volume_24h: float = 5_000_000.0
    signal_threshold: float = 68.0
    ignition_threshold: float = 60.0
    edge_margin: float = 10.0
    max_spread_bps: float = 18.0
    request_timeout: float = 8.0
    workers: int = 8
    extended_24h_pct: float = 30.0
    severely_extended_24h_pct: float = 60.0


@dataclass
class Features:
    symbol: str
    price: float
    ret_5m_pct: float
    ret_15m_pct: float
    ret_1h_pct: float
    ret_24h_pct: float
    quote_volume_24h: float
    volume_ratio: float
    range_ratio: float
    close_location: float
    prev_20_high: float
    prev_20_low: float
    distance_to_high_pct: float
    distance_to_low_pct: float
    breakout_up_pct: float
    breakdown_down_pct: float
    ema20: float
    ema50: float
    ema_gap_pct: float
    taker_buy_sell_ratio: float
    oi_change_30m_pct: float
    funding_rate: float
    spread_bps: float


@dataclass
class ScoreResult:
    symbol: str
    direction: str
    stage: str
    score: float
    opposite_score: float
    edge: float
    price: float
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)


class BinancePublicClient:
    def __init__(self, timeout: float = 8.0, retries: int = 2) -> None:
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BabaBot-MovingCoinDetector/1.0"})

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{UM_BASE}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.35 * (attempt + 1))
        raise RuntimeError(f"GET {path} failed: {last_error}")

    def exchange_info(self) -> Any:
        return self.get("/fapi/v1/exchangeInfo")

    def ticker_24h(self) -> Any:
        return self.get("/fapi/v1/ticker/24hr")

    def klines(self, symbol: str, interval: str, limit: int) -> Any:
        return self.get("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})

    def open_interest_hist(self, symbol: str, period: str = "5m", limit: int = 7) -> Any:
        return self.get(
            "/futures/data/openInterestHist",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    def taker_volume(self, symbol: str, period: str = "5m", limit: int = 1) -> Any:
        return self.get(
            "/futures/data/takerlongshortRatio",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    def premium_index(self, symbol: str) -> Any:
        return self.get("/fapi/v1/premiumIndex", {"symbol": symbol})

    def book_ticker(self, symbol: str) -> Any:
        return self.get("/fapi/v1/ticker/bookTicker", {"symbol": symbol})


def _f(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    out = values[0]
    for v in values[1:]:
        out = alpha * v + (1.0 - alpha) * out
    return out


def _ret(closes: list[float], bars: int) -> float:
    if len(closes) <= bars or closes[-1 - bars] <= 0:
        return 0.0
    return 100.0 * (closes[-1] / closes[-1 - bars] - 1.0)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _scale_positive(x: float, full_at: float, points: float) -> float:
    if x <= 0 or full_at <= 0:
        return 0.0
    return points * _clip(x / full_at, 0.0, 1.0)


def _closed_klines(raw: Iterable[list[Any]], now_ms: Optional[int] = None) -> list[list[Any]]:
    """Drop any still-open candle. Binance kline close-time is element 6."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    rows = list(raw)
    return [row for row in rows if len(row) > 6 and int(row[6]) < now_ms]


def extract_features(
    symbol: str,
    ticker: dict[str, Any],
    klines: list[list[Any]],
    oi_hist: list[dict[str, Any]],
    taker_hist: list[dict[str, Any]],
    premium: dict[str, Any],
    book: dict[str, Any],
) -> Features:
    rows = _closed_klines(klines)
    if len(rows) < 55:
        raise ValueError(f"{symbol}: need >=55 closed 5m candles, got {len(rows)}")

    closes = [_f(r[4]) for r in rows]
    highs = [_f(r[2]) for r in rows]
    lows = [_f(r[3]) for r in rows]
    quote_volumes = [_f(r[7]) if len(r) > 7 else _f(r[5]) * _f(r[4]) for r in rows]

    price = closes[-1]
    prev_qv = quote_volumes[-21:-1]
    med_qv = statistics.median(prev_qv) if prev_qv else 0.0
    volume_ratio = quote_volumes[-1] / med_qv if med_qv > 0 else 0.0

    def tr_pct(i: int) -> float:
        prev_c = closes[i - 1] if i > 0 else closes[i]
        tr = max(highs[i] - lows[i], abs(highs[i] - prev_c), abs(lows[i] - prev_c))
        return 100.0 * tr / prev_c if prev_c > 0 else 0.0

    ranges = [tr_pct(i) for i in range(max(1, len(rows) - 21), len(rows) - 1)]
    med_range = statistics.median(ranges) if ranges else 0.0
    range_ratio = tr_pct(len(rows) - 1) / med_range if med_range > 0 else 0.0

    candle_range = highs[-1] - lows[-1]
    close_location = (price - lows[-1]) / candle_range if candle_range > 0 else 0.5

    prev_20_high = max(highs[-21:-1])
    prev_20_low = min(lows[-21:-1])
    distance_to_high_pct = 100.0 * (price / prev_20_high - 1.0) if prev_20_high > 0 else 0.0
    distance_to_low_pct = 100.0 * (price / prev_20_low - 1.0) if prev_20_low > 0 else 0.0
    breakout_up_pct = max(0.0, distance_to_high_pct)
    breakdown_down_pct = max(0.0, -distance_to_low_pct)

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema_gap_pct = 100.0 * (ema20 / ema50 - 1.0) if ema50 > 0 else 0.0

    taker = taker_hist[-1] if taker_hist else {}
    buy_sell_ratio = _f(taker.get("buySellRatio"), 1.0)
    if buy_sell_ratio <= 0:
        buy = _f(taker.get("buyVol"))
        sell = _f(taker.get("sellVol"))
        buy_sell_ratio = buy / sell if sell > 0 else 1.0

    oi_change = 0.0
    if len(oi_hist) >= 2:
        first = _f(oi_hist[0].get("sumOpenInterestValue") or oi_hist[0].get("sumOpenInterest"))
        last_oi = _f(oi_hist[-1].get("sumOpenInterestValue") or oi_hist[-1].get("sumOpenInterest"))
        if first > 0:
            oi_change = 100.0 * (last_oi / first - 1.0)

    bid = _f(book.get("bidPrice"))
    ask = _f(book.get("askPrice"))
    mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else price
    spread_bps = 10_000.0 * (ask - bid) / mid if mid > 0 and ask >= bid > 0 else 0.0

    return Features(
        symbol=symbol,
        price=price,
        ret_5m_pct=_ret(closes, 1),
        ret_15m_pct=_ret(closes, 3),
        ret_1h_pct=_ret(closes, 12),
        ret_24h_pct=_f(ticker.get("priceChangePercent")),
        quote_volume_24h=_f(ticker.get("quoteVolume")),
        volume_ratio=volume_ratio,
        range_ratio=range_ratio,
        close_location=close_location,
        prev_20_high=prev_20_high,
        prev_20_low=prev_20_low,
        distance_to_high_pct=distance_to_high_pct,
        distance_to_low_pct=distance_to_low_pct,
        breakout_up_pct=breakout_up_pct,
        breakdown_down_pct=breakdown_down_pct,
        ema20=ema20,
        ema50=ema50,
        ema_gap_pct=ema_gap_pct,
        taker_buy_sell_ratio=buy_sell_ratio,
        oi_change_30m_pct=oi_change,
        funding_rate=_f(premium.get("lastFundingRate")),
        spread_bps=spread_bps,
    )


def _direction_score(f: Features, side: str, cfg: DetectorConfig) -> tuple[float, dict[str, float], list[str]]:
    sign = 1.0 if side == "LONG" else -1.0
    r5 = sign * f.ret_5m_pct
    r15 = sign * f.ret_15m_pct
    r60 = sign * f.ret_1h_pct
    accel = r5 - r15 / 3.0

    momentum = (
        _scale_positive(r5, 0.80, 10.0)
        + _scale_positive(r15, 1.80, 8.0)
        + _scale_positive(r60, 3.50, 5.0)
        + _scale_positive(accel, 0.35, 7.0)
    )

    directional_close = f.close_location if side == "LONG" else (1.0 - f.close_location)
    activity = _scale_positive(f.volume_ratio - 1.0, 1.5, 15.0)
    activity += _scale_positive(f.range_ratio - 1.0, 1.0, 5.0) * _clip(directional_close, 0.0, 1.0)

    if side == "LONG":
        if f.breakout_up_pct > 0:
            structure = 10.0 + _scale_positive(f.breakout_up_pct, 0.60, 10.0)
        else:
            dist = abs(min(0.0, f.distance_to_high_pct))
            structure = 10.0 * _clip((0.60 - dist) / 0.60, 0.0, 1.0)
        flow_ratio = f.taker_buy_sell_ratio
        trend_align = f.ema20 > f.ema50 and f.price > f.ema20
    else:
        if f.breakdown_down_pct > 0:
            structure = 10.0 + _scale_positive(f.breakdown_down_pct, 0.60, 10.0)
        else:
            dist = max(0.0, f.distance_to_low_pct)
            structure = 10.0 * _clip((0.60 - dist) / 0.60, 0.0, 1.0)
        flow_ratio = (1.0 / f.taker_buy_sell_ratio) if f.taker_buy_sell_ratio > 0 else 1.0
        trend_align = f.ema20 < f.ema50 and f.price < f.ema20

    flow = _scale_positive(flow_ratio - 1.0, 1.0, 15.0)
    oi = _scale_positive(f.oi_change_30m_pct, 1.5, 10.0) if r15 > 0 else 0.0
    trend = 5.0 if trend_align else 0.0

    raw = momentum + activity + structure + flow + oi + trend
    penalty = 0.0
    same_dir_24h = sign * f.ret_24h_pct
    same_dir_1h = sign * f.ret_1h_pct
    if same_dir_24h >= cfg.extended_24h_pct:
        penalty += 8.0
    if same_dir_24h >= cfg.severely_extended_24h_pct:
        penalty += 10.0
    if same_dir_1h >= 8.0:
        penalty += 5.0
    if f.spread_bps > cfg.max_spread_bps:
        penalty += min(12.0, (f.spread_bps - cfg.max_spread_bps) / 2.0)
    if r15 > 0 and f.oi_change_30m_pct < -0.50:
        penalty += 5.0

    score = _clip(raw - penalty, 0.0, 100.0)
    components = {
        "momentum": round(momentum, 2),
        "activity": round(activity, 2),
        "structure": round(structure, 2),
        "taker_flow": round(flow, 2),
        "open_interest": round(oi, 2),
        "trend_alignment": round(trend, 2),
        "penalty": round(penalty, 2),
    }

    reasons: list[str] = []
    if r5 > 0.25 and accel > 0:
        reasons.append(f"{side.lower()} acceleration {r5:.2f}%/5m")
    if f.volume_ratio >= 1.5:
        reasons.append(f"volume {f.volume_ratio:.2f}x median")
    if f.range_ratio >= 1.5:
        reasons.append(f"range {f.range_ratio:.2f}x normal")
    if side == "LONG" and f.breakout_up_pct > 0:
        reasons.append(f"20-bar high broken +{f.breakout_up_pct:.2f}%")
    if side == "SHORT" and f.breakdown_down_pct > 0:
        reasons.append(f"20-bar low broken -{f.breakdown_down_pct:.2f}%")
    if flow_ratio >= 1.25:
        reasons.append(f"aggressive {side.lower()} flow {flow_ratio:.2f}x")
    if f.oi_change_30m_pct >= 0.5 and r15 > 0:
        reasons.append(f"OI +{f.oi_change_30m_pct:.2f}%/30m")
    if penalty >= 8:
        reasons.append(f"extended/chase penalty -{penalty:.1f}")
    return score, components, reasons


def classify(f: Features, cfg: DetectorConfig) -> ScoreResult:
    long_score, long_components, long_reasons = _direction_score(f, "LONG", cfg)
    short_score, short_components, short_reasons = _direction_score(f, "SHORT", cfg)

    if long_score >= short_score:
        direction = "LONG"
        score, opposite = long_score, short_score
        components, reasons = long_components, long_reasons
        breakout = f.breakout_up_pct > 0
        same_dir_24h = f.ret_24h_pct
        same_dir_1h = f.ret_1h_pct
        contradict_flow = f.taker_buy_sell_ratio < 0.90
    else:
        direction = "SHORT"
        score, opposite = short_score, long_score
        components, reasons = short_components, short_reasons
        breakout = f.breakdown_down_pct > 0
        same_dir_24h = -f.ret_24h_pct
        same_dir_1h = -f.ret_1h_pct
        contradict_flow = f.taker_buy_sell_ratio > 1.11

    edge = score - opposite
    extended = same_dir_24h >= cfg.extended_24h_pct or same_dir_1h >= 8.0
    if extended and (f.volume_ratio < 1.20 or contradict_flow):
        stage = "EXHAUSTION"
    elif score >= cfg.signal_threshold and edge >= cfg.edge_margin and breakout:
        stage = "EXPANSION"
    elif score >= cfg.ignition_threshold and edge >= cfg.edge_margin and f.volume_ratio >= 1.30:
        stage = "IGNITION"
    elif score >= 55.0 and edge >= cfg.edge_margin:
        stage = "MOVING"
    else:
        stage = "NO_TRADE"

    return ScoreResult(
        symbol=f.symbol,
        direction=direction,
        stage=stage,
        score=round(score, 2),
        opposite_score=round(opposite, 2),
        edge=round(edge, 2),
        price=f.price,
        components=components,
        reasons=reasons,
        features={
            "ret_5m_pct": round(f.ret_5m_pct, 4),
            "ret_15m_pct": round(f.ret_15m_pct, 4),
            "ret_1h_pct": round(f.ret_1h_pct, 4),
            "ret_24h_pct": round(f.ret_24h_pct, 4),
            "volume_ratio": round(f.volume_ratio, 3),
            "range_ratio": round(f.range_ratio, 3),
            "taker_buy_sell_ratio": round(f.taker_buy_sell_ratio, 3),
            "oi_change_30m_pct": round(f.oi_change_30m_pct, 4),
            "funding_rate": round(f.funding_rate, 8),
            "spread_bps": round(f.spread_bps, 3),
            "distance_to_high_pct": round(f.distance_to_high_pct, 4),
            "distance_to_low_pct": round(f.distance_to_low_pct, 4),
            "ema_gap_pct": round(f.ema_gap_pct, 4),
        },
    )


def build_universe(client: BinancePublicClient, cfg: DetectorConfig) -> tuple[list[str], dict[str, dict[str, Any]]]:
    exchange = client.exchange_info()
    tickers_raw = client.ticker_24h()
    tickers = {x.get("symbol"): x for x in tickers_raw if isinstance(x, dict)}

    symbols: list[str] = []
    for s in exchange.get("symbols", []):
        symbol = s.get("symbol")
        if not symbol or s.get("status") != "TRADING":
            continue
        if s.get("quoteAsset") != "USDT" or s.get("contractType") != "PERPETUAL":
            continue
        t = tickers.get(symbol)
        if not t:
            continue
        if _f(t.get("quoteVolume")) < cfg.min_quote_volume_24h:
            continue
        symbols.append(symbol)

    # Liquidity only: do not select by momentum, otherwise discovery is systematically late.
    symbols.sort(key=lambda sym: _f(tickers[sym].get("quoteVolume")), reverse=True)
    return symbols[: cfg.universe_size], tickers


def scan_symbol(
    client: BinancePublicClient,
    symbol: str,
    ticker: dict[str, Any],
    cfg: DetectorConfig,
) -> ScoreResult:
    klines = client.klines(symbol, cfg.interval, cfg.kline_limit)
    oi = client.open_interest_hist(symbol, "5m", 7)
    taker = client.taker_volume(symbol, "5m", 1)
    premium = client.premium_index(symbol)
    book = client.book_ticker(symbol)
    features = extract_features(symbol, ticker, klines, oi, taker, premium, book)
    return classify(features, cfg)


def scan_market(client: BinancePublicClient, cfg: DetectorConfig) -> tuple[list[ScoreResult], list[str]]:
    symbols, tickers = build_universe(client, cfg)
    results: list[ScoreResult] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=cfg.workers) as pool:
        futs = {pool.submit(scan_symbol, client, sym, tickers[sym], cfg): sym for sym in symbols}
        for fut in as_completed(futs):
            sym = futs[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                errors.append(f"{sym}: {exc}")

    stage_rank = {"EXPANSION": 4, "IGNITION": 3, "MOVING": 2, "EXHAUSTION": 1, "NO_TRADE": 0}
    results.sort(key=lambda r: (stage_rank.get(r.stage, 0), r.score, r.edge), reverse=True)
    return results, errors


def _print_table(results: list[ScoreResult], limit: int) -> None:
    cols = ("SYMBOL", "DIR", "STAGE", "SCORE", "EDGE", "5M", "15M", "1H", "VOLx", "TAKER", "OI30")
    print(" ".join(f"{c:>10}" for c in cols))
    print("-" * 120)
    for r in results[:limit]:
        f = r.features
        vals = (
            r.symbol,
            r.direction,
            r.stage,
            f"{r.score:.1f}",
            f"{r.edge:.1f}",
            f"{f['ret_5m_pct']:+.2f}",
            f"{f['ret_15m_pct']:+.2f}",
            f"{f['ret_1h_pct']:+.2f}",
            f"{f['volume_ratio']:.2f}",
            f"{f['taker_buy_sell_ratio']:.2f}",
            f"{f['oi_change_30m_pct']:+.2f}",
        )
        print(" ".join(f"{str(v):>10}" for v in vals))
        if r.reasons:
            print("   -> " + "; ".join(r.reasons[:5]))


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="BabaBot Moving Coin Detector V1")
    p.add_argument("--universe", type=int, default=40, help="top liquid USDT perpetuals to inspect")
    p.add_argument("--min-volume", type=float, default=5_000_000.0, help="minimum 24h quote volume in USDT")
    p.add_argument("--threshold", type=float, default=68.0, help="actionable score threshold")
    p.add_argument("--edge", type=float, default=10.0, help="minimum winning score margin vs opposite side")
    p.add_argument("--top", type=int, default=15, help="rows to print")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = p.parse_args(argv)

    cfg = DetectorConfig(
        universe_size=max(1, args.universe),
        min_quote_volume_24h=max(0.0, args.min_volume),
        signal_threshold=_clip(args.threshold, 0.0, 100.0),
        edge_margin=max(0.0, args.edge),
    )
    client = BinancePublicClient(timeout=cfg.request_timeout)
    results, errors = scan_market(client, cfg)

    if args.json:
        payload = {
            "generated_at_ms": int(time.time() * 1000),
            "config": asdict(cfg),
            "results": [asdict(r) for r in results],
            "errors": errors,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_table(results, max(1, args.top))
        if errors:
            print(f"\nWarnings: {len(errors)} symbol(s) failed", file=sys.stderr)
            for err in errors[:5]:
                print(f"  {err}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
