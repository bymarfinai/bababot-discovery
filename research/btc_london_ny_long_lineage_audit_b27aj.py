#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

P_CHECKPOINT = ROOT / 'BabaBot_V2_V2.5_Final_Checkpoint.md'
P_Q_PRE = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Preregistration.md'
P_Q = ROOT / 'research/btc_session_liquidity_pressure_entry_b27q.py'
P_W = ROOT / 'research/btc_london_ny_pre_second_touch_entry_b27w.py'
P_AC = ROOT / 'research/btc_london_ny_e20_profit_lock_runner_b27ac.py'
P_AC_TRADES = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Trades.csv'
P_AG_DETAIL = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Detail.csv'

OUT = ROOT / 'BTC_LONDON_NY_LONG_LINEAGE_AUDIT_B27AJ_Result.md'
STATUS = ROOT / 'BTC_LONDON_NY_LONG_LINEAGE_AUDIT_B27AJ_Status.txt'
MAJOR = {'external','development','reference_validation'}


def block(text, a, b):
    i=text.index(a); j=text.index(b,i)
    return text[i:j]


def main():
    ck=P_CHECKPOINT.read_text()
    qpre=P_Q_PRE.read_text()
    q=P_Q.read_text()
    w=P_W.read_text()
    ac=P_AC.read_text()

    # 1) Older detector really did have HH/HL BULL semantics.
    assert 'BULL: 2 confirmed HH + 2 confirmed HL' in ck
    assert 'BEAR: 2 confirmed LH + 2 confirmed LL' in ck

    # 2) B27Q intentionally starts a separate liquidity experiment without prior swing/fractal engine.
    assert 'without the prior swing/fractal/touch engines' in qpre
    assert 'No fractal swing, EMA, order block, ATR band' in qpre

    # 3) b22b is imported only to reuse partition boundaries, not its state detector.
    uses=[ln.strip() for ln in q.splitlines() if 'b22b.' in ln]
    assert uses == ['PARTS = b22b.PARTS'], uses

    # 4) Direction in B27Q is created directly from which frozen level was visited.
    assert "side = 'LONG' if v['level'] == 'HIGH' else 'SHORT'" in q
    q_signal_block=block(q, "for v in scan['visits']:", "visits = pd.DataFrame")
    for forbidden in ('regime', 'SwingRegime', 'higher high', 'HH', 'HL'):
        assert forbidden not in q_signal_block, (forbidden, 'B27Q signal block')

    # 5) B27W only selects the B27Q LONG/K1/OPP0 liquidity cohort.
    w_load=block(w, 'def load_k1():', 'def qualifies_high_touch')
    assert "s.transition=='LONDON_TO_NEWYORK'" in w_load
    assert "s.side=='LONG'" in w_load
    assert 's.k==1' in w_load
    assert 's.opp_visits_at_signal==0' in w_load
    for forbidden in ('regime', 'SwingRegime', 'HH', 'HL'):
        assert forbidden not in w_load, (forbidden, 'B27W load_k1')

    # 6) B27AC cohort construction has no regime predicate.
    ac_load=block(ac, 'def load_cohorts()', 'def verify_baselines')
    for forbidden in ('regime', 'SwingRegime', 'HH', 'HL'):
        assert forbidden not in ac_load, (forbidden, 'B27AC load_cohorts')

    # 7) Reproduce old SAME_BAR pooled-major hybrid economics.
    t=pd.read_csv(P_AC_TRADES)
    t=t[(t['rule']=='SAME_BAR_REJECTION') & t['partition'].isin(MAJOR)].copy()
    assert len(t)==68, len(t)
    total=float(pd.to_numeric(t['hybrid_net_pnl_usd']).sum())
    wr=float((pd.to_numeric(t['hybrid_net_pnl_usd'])>0).mean())
    assert abs(total-91.31) < 0.02, total
    assert abs(wr-(47/68)) < 1e-12, wr

    # 8) Attribute those exact trades with later causal 4H state labels.
    d=pd.read_csv(P_AG_DETAIL)
    d=d[(d['side']=='LONG') & d['partition'].isin(MAJOR)].copy()
    t['signal_ts']=pd.to_datetime(t['signal_ts'],utc=True)
    d['signal_ts']=pd.to_datetime(d['signal_ts'],utc=True)
    j=t.merge(d[['partition','signal_ts','regime_at_signal']],on=['partition','signal_ts'],how='left',validate='one_to_one')
    assert j['regime_at_signal'].notna().all()
    counts=j['regime_at_signal'].value_counts().to_dict()
    expected={'BULL':37,'BEAR':19,'SIDEWAYS':12}
    assert counts==expected, (counts,expected)

    lines=[
        '# B27AJ — BTC London->NY LONG Lineage / Regime-Gate Audit — Result','',
        '**Audit status: PASS.** Source-code lineage and persisted trade identities were checked directly.','',
        '## Finding','',
        '- The older V2 detector really did define BULL as 2 confirmed HH + 2 confirmed HL (and BEAR as 2 LH + 2 LL).',
        '- B27Q was explicitly a new liquidity experiment **without** the prior swing/fractal engine.',
        '- In B27Q code, `b22b` is used only for scoring partitions (`PARTS`); its regime state is not used to create signals.',
        '- B27Q creates LONG directly when the visited frozen level is `HIGH`; B27W then selects only `LONDON_TO_NEWYORK + LONG + K1 + OPP0`.',
        '- B27AC cohort construction contains no HH/HL or regime predicate.',
        f'- Original SAME_BAR pooled-major hybrid reproduces **N=68**, **WR={wr:.1%}**, **total=${total:+.2f}**.',
        f"- Those exact 68 trades later label as **BULL={counts['BULL']}**, **BEAR={counts['BEAR']}**, **SIDEWAYS={counts['SIDEWAYS']}** under the causal B27AG 4H regime detector.",
        '',
        '**Conclusion: the +$91.31 B27AC SAME_BAR LONG result was an all-regime liquidity cohort. It was not pre-gated by the older HH/HL BULL regime.**','',
        'The historical HH/HL regime detector existed, but it belongs to an earlier research lineage and was not inherited into B27Q/B27W/B27AC.','',
        'Research only; live BBC unchanged.'
    ]
    OUT.write_text('\n'.join(lines)+'\n')
    STATUS.write_text('B27AJ_PASS_OLD_LONG_WAS_ALL_REGIME\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
