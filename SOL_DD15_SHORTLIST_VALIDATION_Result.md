# SOL DD15 — Frozen Shortlist Validation Result

Raw SOLUSDT 5m coverage: **99.7698%**.

Seven frozen rank-1 candidates were evaluated without rescanning or substitution. H15/H22/H23 reuse already-opened locked OOS evidence; H17/H18/H20/H21 are the newly opened rescued candidates.

| H | WIB | Character | LB/Hold | OOS N | WR | Net | Exp | PF | DD/Net | L-streak | Ext | RefVal | Pool | Anchors | Verdict |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| H15 | 22:00-23:00 | EFF_HIGH__RANGE_LOW | 240m/960m | 152 | 44.08% | $-325.45 | $-2.14 | 0.776 | inf% | 10 | FAIL | FAIL | FAIL | 0/1 | **FAILED** |
| H17 | 00:00-01:00 | EFF_LOW__RANGE_HIGH | 30m/720m | 211 | 52.13% | $+236.05 | $+1.12 | 1.119 | 181.00% | 9 | FAIL | FAIL | FAIL | 1/4 | **FAILED** |
| H18 | 01:00-02:00 | RV_HIGH__RANGE_MID | 120m/720m | 213 | 47.42% | $+106.01 | $+0.50 | 1.071 | 391.89% | 17 | FAIL | FAIL | FAIL | 1/4 | **FAILED** |
| H20 | 03:00-04:00 | DRIVE_UP__STR_B80_100 | 360m/960m | 338 | 44.67% | $+329.94 | $+0.98 | 1.094 | 255.11% | 23 | FAIL | FAIL | FAIL | 0/4 | **FAILED** |
| H21 | 04:00-05:00 | DRIVE_UP__RV_HIGH | 360m/960m | 436 | 48.17% | $+188.61 | $+0.43 | 1.037 | 612.69% | 27 | FAIL | FAIL | FAIL | 0/4 | **FAILED** |
| H22 | 05:00-06:00 | EFF_LOW__EXT_MID | 240m/360m | 226 | 46.90% | $-163.33 | $-0.72 | 0.861 | inf% | 11 | FAIL | FAIL | FAIL | 0/4 | **FAILED** |
| H23 | 06:00-07:00 | DRIVE_DOWN__STR_B80_100 | 15m/120m | 287 | 49.83% | $+255.56 | $+0.89 | 1.245 | 135.83% | 7 | FAIL | FAIL | FAIL | 1/4 | **FAILED** |

## Exact failure reasons

- **H15:** external:WR>=52%;external:net>0;external:exp>0;external:PF>=1.05;external:DD<=125;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;reference_validation:DD<=125;combined_oos:N>=160;combined_oos:WR>55%;combined_oos:net>0;combined_oos:exp>=0.50;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:0/1_supportive
- **H17:** external:WR>=52%;external:DD<=125;reference_validation:DD<=125;combined_oos:WR>55%;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:1/4_supportive
- **H18:** external:WR>=52%;external:DD<=125;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;reference_validation:DD<=125;reference_validation:loss_streak<=10;combined_oos:WR>55%;combined_oos:exp>=0.50;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:1/4_supportive
- **H20:** external:WR>=52%;external:DD<=125;external:loss_streak<=10;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;reference_validation:DD<=125;reference_validation:loss_streak<=10;combined_oos:WR>55%;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:0/4_supportive
- **H21:** external:DD<=125;external:loss_streak<=10;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;reference_validation:DD<=125;reference_validation:loss_streak<=10;combined_oos:WR>55%;combined_oos:exp>=0.50;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:0/4_supportive
- **H22:** external:WR>=52%;external:PF>=1.05;external:DD<=125;external:loss_streak<=10;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;reference_validation:DD<=125;combined_oos:WR>55%;combined_oos:net>0;combined_oos:exp>=0.50;combined_oos:PF>=1.20;combined_oos:DD/net<=15%;combined_oos:loss_streak<=8;anchor_local:0/4_supportive
- **H23:** external:WR>=52%;external:DD<=125;reference_validation:WR>=52%;reference_validation:net>0;reference_validation:exp>0;reference_validation:PF>=1.05;combined_oos:WR>55%;combined_oos:DD/net<=15%;anchor_local:1/4_supportive

**Status: SOL_DD15_SHORTLIST_0_OF_7_VALIDATED**

Stop here. No new hour, rule, threshold, anchor subset, exit, or replacement candidate is authorized by this run.
Research/shadow only; no live-trading authorization.
