# BNB B30 — State-Structure Entry Discovery Stop Verdict

**Status: BNB_B30_V1_STOP_NO_ENTRY**

## Valid evidence
- S1 pure structure census: 8/8 state-based detector families were structurally viable.
- S2 generic entry archetype run is descriptive only.
- S2B initial run at commit `120dc15...` was INVALID because a pandas timestamp-unit mismatch marked every 5m interval as a gap.
- Tooling-only continuity patch: `0e5bbc628f8b19679e8ee4224b19315141642787`.
- Valid corrected rerun: GitHub Actions `35215722798`, head `7e39087aae29692f921946371cb061ebc05732f9`.
- Raw 5m coverage: 100%; raw/A1 ret15 and close-location identity checks passed.

## Corrected S2B conclusion
No preregistered structure-specific entry mechanism passed the frozen development gate.

Nearest long candidate:
- S01 SWEEP_LOW_RECLAIM + STRUCTURE_CLOSE
- development N = 5,245
- participation = 100%
- +60 directional hit = 54.6616%
- Wilson LCB = 53.3114%
- worst development era = 53.6860%
- preregistered hit gate = 55%
- verdict = REJECT

Important semantic diagnostic:
- S02 HL_CONTINUATION + STRUCTURE_CLOSE: +60 LONG hit 43.8878%.
- S06 LH_CONTINUATION + STRUCTURE_CLOSE: +60 SHORT hit 46.7290%.
- S03 BREAK_HIGH_HOLD + STRUCTURE_CLOSE: +60 LONG hit 47.2883%.
- S07 BREAK_LOW_HOLD + STRUCTURE_CLOSE: +60 SHORT hit 43.6242%.

These results indicate that the B30 S1 definitions are valid repeatable **state transitions**, but they should not be treated as faithful swing-chart structures such as a confirmed higher-low setup. In particular, S02/S06 require the path already to have returned to CONT_UP/CONT_DOWN at the detector completion timestamp, which may occur after the actionable structural phase.

## Scientific stop
- Do not lower the 55% development gate.
- Do not send any B30-v1 pair to economics.
- Do not retrofit B30-v1 detector clauses after observing outcomes.
- B30-v1 is frozen and stopped.

## Allowed next identity
A new identity may replace rolling-state proxies with causally confirmed **swing-structure detectors** built directly from immutable/raw-identity-guarded OHLC:
1. detect/confirm swing highs and lows causally;
2. construct HH/HL/LH/LL, sweep, BOS, break-retest, failed-break structures;
3. census structures without outcomes;
4. only then run independent entry discovery per structure;
5. economics remains forbidden until a structure+entry pair is frozen.
