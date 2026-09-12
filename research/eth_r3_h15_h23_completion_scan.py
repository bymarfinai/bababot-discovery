#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import eth_r3_h06_stageA_2022_dev as stageA
import eth_r3_h06_stageB_2023_test as stageB

ROOT = Path(__file__).resolve().parent.parent
HOURS = range(15, 24)
SUMMARY_CSV = ROOT / "ETH_R3_H15_H23_COMPLETION_SUMMARY.csv"
SUMMARY_MD = ROOT / "ETH_R3_H15_H23_COMPLETION_SUMMARY.md"


def relabel(path: Path, h: int):
    if path.exists():
        txt = path.read_text()
        txt = txt.replace("ETH R3 H06", f"ETH R3 H{h:02d}")
        txt = txt.replace("ETH_R3_H06", f"ETH_R3_H{h:02d}")
        path.write_text(txt)


def run_hour(h: int):
    hh = f"{h:02d}"
    pfxa = f"ETH_R3_H{hh}_STAGEA"
    stageA.PFX = pfxa
    stageA.OUT_GRID = ROOT / f"{pfxa}_2022_DevGrid.csv"
    stageA.OUT_LOCK = ROOT / f"{pfxa}_FrozenDevCandidate.csv"
    stageA.OUT_RESULT = ROOT / f"{pfxa}_Result.md"
    stageA.OUT_STATUS = ROOT / f"{pfxa}_Status.txt"
    stageA.HOUR_WIB = h
    stageA.main()
    relabel(stageA.OUT_RESULT, h)
    relabel(stageA.OUT_STATUS, h)

    row = {"hour_wib": h}
    if not stageA.OUT_LOCK.exists():
        row.update({
            "dev_rule": "", "dev_lb": None, "dev_hold": None, "dev_n": 0,
            "dev_wr": None, "dev_exp": None, "dev_pf": None, "dev_dd": None, "dev_ls": None,
            "stageB_verdict": "NO_2022_DEV_CANDIDATE", "test_exact_n": None,
            "test_exact_wr": None, "test_exact_exp": None, "test_exact_pf": None,
            "test_exact_net": None, "local_viable": 0, "local_stable": 0,
            "stable_lb": None, "stable_hold": None,
        })
        return row

    lock = pd.read_csv(stageA.OUT_LOCK).iloc[0]
    row.update({
        "dev_rule": str(lock.character_rule), "dev_lb": int(lock.dev_lb), "dev_hold": int(lock.dev_hold),
        "dev_n": int(lock.dev_n), "dev_wr": float(lock.dev_wr), "dev_exp": float(lock.dev_exp),
        "dev_pf": float(lock.dev_pf), "dev_dd": float(lock.dev_dd), "dev_ls": int(lock.dev_ls),
    })

    pfxb = f"ETH_R3_H{hh}_STAGEB"
    stageB.LOCK_PATH = stageA.OUT_LOCK
    stageB.OUT_NEIGHBOR = ROOT / f"{pfxb}_2023_LocalNeighborhood.csv"
    stageB.OUT_LOCK = ROOT / f"{pfxb}_FrozenStableCandidate.csv"
    stageB.OUT_RESULT = ROOT / f"{pfxb}_Result.md"
    stageB.OUT_STATUS = ROOT / f"{pfxb}_Status.txt"
    stageB.HOUR_WIB = h
    stageB.main()
    relabel(stageB.OUT_RESULT, h)
    relabel(stageB.OUT_STATUS, h)

    status = stageB.OUT_STATUS.read_text().strip().replace(f"ETH_R3_H{hh}_", "")
    N = pd.read_csv(stageB.OUT_NEIGHBOR)
    exact = N[N.manhattan_distance == 0].iloc[0]
    row.update({
        "stageB_verdict": status,
        "test_exact_n": int(exact.trades), "test_exact_wr": float(exact.wr),
        "test_exact_exp": float(exact.exp), "test_exact_pf": float(exact.pf),
        "test_exact_net": float(exact.net),
        "local_viable": int(N.economically_viable.astype(bool).sum()),
        "local_stable": int(N.performance_stable.astype(bool).sum()),
        "stable_lb": None, "stable_hold": None,
    })
    if stageB.OUT_LOCK.exists():
        s = pd.read_csv(stageB.OUT_LOCK).iloc[0]
        row["stable_lb"] = int(s.test_lb)
        row["stable_hold"] = int(s.test_hold)
    return row


def main():
    rows = []
    for h in HOURS:
        print(f"\n===== ETH R3 H{h:02d} =====")
        rows.append(run_hour(h))

    D = pd.DataFrame(rows)
    D.to_csv(SUMMARY_CSV, index=False)

    lines = [
        "# ETH R3 H15-H23 Completion Scan", "",
        "**Sequential per-hour protocol: 2022 Development freeze first, then 2023 frozen-rule local stability test. 2024 is NOT opened by this batch. 2025-2026 remain CLOSED.**", "",
        "| WIB hour | 2022 frozen character | Dev timing | Dev N | Dev WR | Dev Exp | Dev PF | 2023 exact WR | Exact Exp | Exact PF | Viable | Stable | Stage B verdict |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in D.itertuples(index=False):
        def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.2f}%"
        def num(x, n=2): return "-" if pd.isna(x) else f"{float(x):.{n}f}"
        timing = "-" if pd.isna(r.dev_lb) else f"LB{int(r.dev_lb)}/H{int(r.dev_hold)}"
        lines.append(
            f"| {int(r.hour_wib):02d}:00-{(int(r.hour_wib)+1)%24:02d}:00 | {r.dev_rule or '-'} | {timing} | {int(r.dev_n)} | {pct(r.dev_wr)} | ${num(r.dev_exp)} | {num(r.dev_pf,3)} | {pct(r.test_exact_wr)} | ${num(r.test_exact_exp)} | {num(r.test_exact_pf,3)} | {int(r.local_viable)} | {int(r.local_stable)} | {r.stageB_verdict} |"
        )
    lines += ["", "Any hour with STABLE_EDGE_FROZEN must be handled in a separate, frozen 2024 confirmation step before interpretation. No 2024 winner reselection is allowed."]
    SUMMARY_MD.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
