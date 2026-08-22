#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / 'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Events.csv'
OUT_MD = ROOT / 'BTC_PREV_SESSION_TOUCH_BREAKOUT_PROB_B27N_Result.md'
OUT_SUM = ROOT / 'BTC_PREV_SESSION_TOUCH_BREAKOUT_PROB_B27N_Summary.csv'

TFS = ['15m', '1h']
TOL = 'TOL_0.20'
PARTS = ['external', 'development', 'reference_validation', 'august']
THRESHOLDS = [1, 2, 3, 4]
TRANSITIONS = ['ASIA_TO_LONDON', 'LONDON_TO_NEWYORK']


def one_row(g: pd.DataFrame, tf: str, part: str, scope: str, level: str, k: int):
    col = 'high_retests' if level == 'HIGH' else 'low_retests'
    eligible = g[pd.to_numeric(g[col], errors='coerce').fillna(0).astype(int) >= k]
    n = len(eligible)
    if n == 0:
        return {
            'tf': tf, 'partition': part, 'scope': scope, 'level': level,
            'threshold': k, 'n': 0, 'bull_n': 0, 'bear_n': 0, 'no_break_n': 0,
            'bull_prob': float('nan'), 'bear_prob': float('nan'), 'no_break_prob': float('nan'),
            'target_prob': float('nan'), 'opposite_prob': float('nan')
        }
    vc = eligible['direction'].value_counts()
    bull = int(vc.get('BULL', 0)); bear = int(vc.get('BEAR', 0)); nob = int(vc.get('NO_BREAK', 0))
    target = bull if level == 'HIGH' else bear
    opposite = bear if level == 'HIGH' else bull
    return {
        'tf': tf, 'partition': part, 'scope': scope, 'level': level,
        'threshold': k, 'n': n, 'bull_n': bull, 'bear_n': bear, 'no_break_n': nob,
        'bull_prob': bull / n, 'bear_prob': bear / n, 'no_break_prob': nob / n,
        'target_prob': target / n, 'opposite_prob': opposite / n
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def main():
    e = pd.read_csv(EVENTS)
    rows = []
    for tf in TFS:
        for part in PARTS:
            base = e[(e['tf'] == tf) & (e['tolerance'] == TOL) & (e['partition'] == part)].copy()
            scopes = [('ALL_TRANSITIONS', base)]
            for tr in TRANSITIONS:
                scopes.append((tr, base[base['transition'] == tr]))
            for scope, g in scopes:
                for level in ['HIGH', 'LOW']:
                    for k in THRESHOLDS:
                        rows.append(one_row(g, tf, part, scope, level, k))
    s = pd.DataFrame(rows)
    s.to_csv(OUT_SUM, index=False)

    md = [
        '# B27N — Previous-Session Touch Count -> Breakout Probability', '',
        'Frozen from B27M. Primary = 15m, ±0.20% previous-session High/Low zones. Probability denominator includes BULL, BEAR, and NO_BREAK sessions.', '',
        '## Primary: 15m, both transitions combined', '',
        '| Partition | Level touched | At least | N | Intended breakout | Opposite breakout | No breakout |',
        '|---|---|---:|---:|---:|---:|---:|'
    ]
    p = s[(s.tf == '15m') & (s.scope == 'ALL_TRANSITIONS')]
    for part in PARTS:
        for level in ['HIGH', 'LOW']:
            z = p[(p.partition == part) & (p.level == level)].sort_values('threshold')
            for r in z.itertuples(index=False):
                intended = 'BULL' if level == 'HIGH' else 'BEAR'
                md.append(f'| {part} | {level} | {int(r.threshold)}x | {int(r.n)} | {intended} {pct(r.target_prob)} | {pct(r.opposite_prob)} | {pct(r.no_break_prob)} |')

    md += ['', '## Secondary: 1H, both transitions combined', '',
           '| Partition | Level touched | At least | N | Intended breakout | Opposite breakout | No breakout |',
           '|---|---|---:|---:|---:|---:|---:|']
    p = s[(s.tf == '1h') & (s.scope == 'ALL_TRANSITIONS')]
    for part in PARTS:
        for level in ['HIGH', 'LOW']:
            z = p[(p.partition == part) & (p.level == level)].sort_values('threshold')
            for r in z.itertuples(index=False):
                intended = 'BULL' if level == 'HIGH' else 'BEAR'
                md.append(f'| {part} | {level} | {int(r.threshold)}x | {int(r.n)} | {intended} {pct(r.target_prob)} | {pct(r.opposite_prob)} | {pct(r.no_break_prob)} |')

    md += ['', 'Transition-specific rows are persisted in the Summary CSV.', '',
           'Diagnostic only. No touch threshold is promoted to a trading rule. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
