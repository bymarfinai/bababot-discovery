#!/usr/bin/env python3
"""V7-B — frozen regime-aligned 5m breakout -> retest continuation.

Research-only. Independent second entry family after V7-A failed-breakout rejection.
No parameter tuning from V7-A is used here.

Frozen definition:
- Same existing trade-independent 1H mode3_regime classifier.
- Only BULL_MARKUP/Bear_MARKDOWN are tradable.
- Breakout reference = previous 12 completed 5m bars (1h), current breakout excluded.
- BULL: 5m close strictly above prior-12 high while BULL_MARKUP.
- BEAR: 5m close strictly below prior-12 low while BEAR_MARKDOWN.
- After breakout, wait at most next 12 completed 5m bars (1h) for FIRST valid retest.
- LONG retest: low <= breakout level, close > breakout level, close > open, and regime still BULL_MARKUP.
- SHORT retest: high >= breakout level, close < breakout level, close < open, and regime still BEAR_MARKDOWN.
- Enter at retest close; stop at retest candle extreme; target 1R.
- Track from next 5m bar, <=72h; same-child TP+SL ambiguity excluded.
- One pending breakout per pair and one active position per pair.

No Fib/OI/funding/taker/body threshold/EMA gate/RR sweep/pair filter/side filter.
"""

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import v7_regime_failed_breakout as base
from mode3_regime.regime import Regime

PAIRS = base.PAIRS
DAYS = 120
LOOKBACK_5M = 12
RETEST_WINDOW = 12
RR = 1.0


def breakout_at(rows5, i):
    if i < LOOKBACK_5M:
        return None
    b = rows5[i]
    hist = rows5[i-LOOKBACK_5M:i]
    hi = max(x["high"] for x in hist)
    lo = min(x["low"] for x in hist)
    bull = b["close"] > hi
    bear = b["close"] < lo
    if bull and bear:
        return None
    if bull:
        return {"direction":"LONG", "level":hi}
    if bear:
        return {"direction":"SHORT", "level":lo}
    return None


def valid_retest(b, direction, level):
    if direction == "LONG":
        return b["low"] <= level and b["close"] > level and b["close"] > b["open"]
    return b["high"] >= level and b["close"] < level and b["close"] < b["open"]


def process_pair(symbol, rows1, rows5, sample_start, sample_end):
    close_times, states = base.build_regime_map(rows1)
    events=[]; all_retests=[]; pending=None; release_time=sample_start
    diag=Counter()

    for i in range(LOOKBACK_5M, len(rows5)):
        b=rows5[i]
        sig_close=b["t"]+timedelta(minutes=5)
        if sig_close < sample_start or sig_close >= sample_end:
            continue

        # Expire pending breakout causally after 12 future 5m bars.
        if pending is not None and i > pending["breakout_idx"] + RETEST_WINDOW:
            diag["pending_expired"] += 1
            pending=None

        # First, allow a pending breakout to retest on this bar (never same breakout bar).
        if pending is not None and i > pending["breakout_idx"]:
            d=pending["direction"]; level=pending["level"]
            if valid_retest(b,d,level):
                rg=base.regime_at(sig_close, close_times, states)
                still_aligned=(d=="LONG" and rg==Regime.BULL_MARKUP) or (d=="SHORT" and rg==Regime.BEAR_MARKDOWN)
                entry=b["close"]; stop=b["low"] if d=="LONG" else b["high"]
                risk=entry-stop if d=="LONG" else stop-entry
                if risk>0:
                    target=entry+risk*RR if d=="LONG" else entry-risk*RR
                    outcome,ot=base.resolve(rows5,i,d,entry,stop,target)
                    e={
                        "symbol":symbol,"signal_time":sig_close,"direction":d,"regime":rg.value,
                        "breakout_time":pending["breakout_time"],"breakout_level":level,
                        "retest_bars":i-pending["breakout_idx"],"aligned":still_aligned,
                        "entry":entry,"stop":stop,"target":target,"risk_pct":100.0*risk/entry,
                        "outcome":outcome,"outcome_time":ot,
                    }
                    all_retests.append(e)
                    if still_aligned:
                        if sig_close >= release_time:
                            events.append(e); release_time=ot if ot else sig_close+timedelta(hours=72)
                        else:
                            diag["aligned_retest_blocked_active_position"] += 1
                    else:
                        diag["retest_regime_no_longer_aligned"] += 1
                pending=None
                # A retest bar is consumed; do not also create a fresh breakout on same bar.
                continue

        # Only create a pending breakout if none exists.
        if pending is None:
            br=breakout_at(rows5,i)
            if br:
                rg=base.regime_at(sig_close,close_times,states)
                aligned=(br["direction"]=="LONG" and rg==Regime.BULL_MARKUP) or (br["direction"]=="SHORT" and rg==Regime.BEAR_MARKDOWN)
                diag[f"breakout_{br['direction'].lower()}_{rg.value}"] += 1
                if aligned:
                    pending={
                        "direction":br["direction"],"level":br["level"],"breakout_idx":i,
                        "breakout_time":sig_close,"breakout_regime":rg.value,
                    }
                else:
                    diag["breakout_not_regime_aligned"] += 1

    return events, all_retests, dict(diag)


def main():
    now=datetime.now(timezone.utc)
    today0=datetime.combine(now.date(),datetime.min.time(),tzinfo=timezone.utc)
    sample_end=today0-timedelta(days=3)
    sample_start=sample_end-timedelta(days=DAYS)
    load_start=sample_start-timedelta(days=8)
    load_end=today0

    all_events=[]; retest_pool=[]; coverage={}; mechanics={}; errors={}
    for p in PAIRS:
        try:
            r1=base.load_klines(p,"1h",load_start,load_end)
            r5=base.load_klines(p,"5m",load_start,load_end)
            ev,pool,diag=process_pair(p,r1,r5,sample_start,sample_end)
            all_events.extend(ev); retest_pool.extend(pool); mechanics[p]=diag
            coverage[p]={"bars_1h":len(r1),"bars_5m":len(r5),"executed_events":len(ev),"valid_retests":len(pool)}
        except Exception as ex:
            errors[p]=str(ex)

    overall=base.stat(all_events)
    by_pair={p:base.stat([e for e in all_events if e["symbol"]==p]) for p in PAIRS}
    by_direction={d:base.stat([e for e in all_events if e["direction"]==d]) for d in ("LONG","SHORT")}
    cut=sample_start+timedelta(days=60)
    by_time={
        "first_60d":base.stat([e for e in all_events if e["signal_time"]<cut]),
        "last_60d":base.stat([e for e in all_events if e["signal_time"]>=cut]),
        "cut":cut.isoformat(),
    }

    aligned_pool=[e for e in retest_pool if e["aligned"]]
    lost_regime_pool=[e for e in retest_pool if not e["aligned"]]
    pool_diag={"aligned_independent":base.stat(aligned_pool),"regime_lost_before_retest":base.stat(lost_regime_pool)}

    resolved=[e for e in all_events if e["outcome"] in ("WIN","LOSS")]
    wins=[e for e in resolved if e["outcome"]=="WIN"]; losses=[e for e in resolved if e["outcome"]=="LOSS"]
    wl={
        "risk_pct":{"winner_median":base.median(wins,"risk_pct"),"loser_median":base.median(losses,"risk_pct")},
        "retest_bars":{"winner_median":base.median(wins,"retest_bars"),"loser_median":base.median(losses,"retest_bars")},
    }

    pair_pass=sum(1 for x in by_pair.values() if x["resolved"]>=5 and (x["wr_pct"] or 0)>50)
    dir_pass=all(by_direction[d]["resolved"]>=10 and (by_direction[d]["wr_pct"] or 0)>50 for d in by_direction)
    time_pass=all(by_time[k]["resolved"]>=10 and (by_time[k]["wr_pct"] or 0)>50 for k in ("first_60d","last_60d"))
    earns=bool(overall["resolved"]>=40 and (overall["wr_pct"] or 0)>=70 and pair_pass>=3 and dir_pass and time_pass)

    out={
        "phase":"V7-B","status":"FROZEN_REGIME_BREAKOUT_RETEST_CONTINUATION_120D_SCREEN",
        "frozen_definition":{
            "regime":"existing mode3_regime 1H defaults; latest completed 1H only",
            "tradeable_regimes":["bull_markup","bear_markdown"],
            "breakout_reference":"previous 12 completed 5m bars (1h)",
            "bull_breakout":"close > prior12 high while BULL_MARKUP",
            "bear_breakout":"close < prior12 low while BEAR_MARKDOWN",
            "retest_window":"next 12 completed 5m bars (1h)",
            "long_retest":"first low<=level, close>level, close>open; regime still BULL_MARKUP",
            "short_retest":"first high>=level, close<level, close<open; regime still BEAR_MARKDOWN",
            "entry":"retest 5m close","stop":"retest candle extreme","target":"1R",
            "tracking":"next 5m onward <=72h; same-child ambiguity excluded",
            "pending_rule":"one pending breakout per pair; retest bar cannot also create new breakout",
            "position_rule":"one active position per pair","threshold_sweep":False,"other_filters":False,
        },
        "predeclared_gate":{
            "overall_wr_pct":">=70","resolved_n":">=40",
            "pair_distribution":">=3/4 pairs each resolved>=5 and WR>50",
            "both_directions":"LONG and SHORT each resolved>=10 and WR>50",
            "both_60d_halves":"each resolved>=10 and WR>50",
        },
        "sample_start":sample_start.isoformat(),"sample_end_exclusive":sample_end.isoformat(),
        "coverage":coverage,"overall":overall,"by_pair":by_pair,"by_direction":by_direction,"by_time":by_time,
        "retest_pool_diagnostic_only":pool_diag,"winner_loser_diagnostic_only":wl,"mechanics_diagnostics":mechanics,
        "gate_checks":{"pairs_passing":pair_pass,"direction_check":dir_pass,"time_check":time_pass,"earns_971d_validation":earns},
        "errors":errors,
        "notes":{"scientific_lock":"No alternate breakout lookback, retest window, candle threshold, RR, stop, pair or side may be promoted post-hoc from this sample."},
    }
    print("V7_B_RESULT",json.dumps(out,separators=(",",":"),default=str))

if __name__=="__main__":
    main()
