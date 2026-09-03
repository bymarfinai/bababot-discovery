# SOL LONG First-Break Visit Audit — A1B Result

A1B does not search parameters. It re-expresses the frozen A1 selected events using the denominator that directly answers: **where does the first completed-close upside breakout happen most often?**

## Modal first-break visit by frozen topology role and partition

| Role | Partition | Sessions | First breaks H1-H5 | Modal visit |
|---|---|---:|---:|---:|
| CENTRAL | development | 1088 | 566 | H1 |
| CENTRAL | external | 473 | 257 | H1 |
| CENTRAL | reference_validation | 574 | 297 | H1 |
| CLOCK_SUPPORT | development | 1088 | 543 | H1 |
| CLOCK_SUPPORT | external | 473 | 267 | H1 |
| CLOCK_SUPPORT | reference_validation | 574 | 299 | H1 |
| REF_SUPPORT | development | 1088 | 637 | H1 |
| REF_SUPPORT | external | 473 | 279 | H1 |
| REF_SUPPORT | reference_validation | 574 | 330 | H1 |

## CENTRAL first-break distribution

| Partition | H1 | H2 | H3 | H4 | H5 |
|---|---:|---:|---:|---:|---:|
| development | 71.7% | 22.6% | 3.9% | 1.4% | 0.4% |
| external | 81.7% | 13.6% | 2.7% | 1.9% | 0.0% |
| reference_validation | 73.7% | 17.8% | 5.7% | 1.0% | 1.7% |

## CLOCK_SUPPORT first-break distribution

| Partition | H1 | H2 | H3 | H4 | H5 |
|---|---:|---:|---:|---:|---:|
| development | 71.8% | 20.1% | 6.4% | 1.3% | 0.4% |
| external | 80.5% | 15.0% | 3.7% | 0.7% | 0.0% |
| reference_validation | 76.6% | 17.4% | 4.7% | 0.7% | 0.7% |

## REF_SUPPORT first-break distribution

| Partition | H1 | H2 | H3 | H4 | H5 |
|---|---:|---:|---:|---:|---:|
| development | 72.7% | 20.7% | 4.6% | 1.6% | 0.5% |
| external | 81.0% | 12.5% | 4.7% | 1.4% | 0.4% |
| reference_validation | 71.2% | 20.3% | 5.5% | 1.5% | 1.5% |

## Central Development funnel and anatomy

| Visit | Opportunity N | First-break N | Share of first breaks | Conditional conversion | Median extension |
|---|---:|---:|---:|---:|---:|
| H1 | 617 | 406 | 71.7% | 65.8% | 0.224R |
| H2 | 173 | 128 | 22.6% | 74.0% | 0.208R |
| H3 | 38 | 22 | 3.9% | 57.9% | 0.204R |
| H4 | 13 | 8 | 1.4% | 61.5% | 0.105R |
| H5 | 4 | 2 | 0.4% | 50.0% | 0.315R |

## Decision

**Status: SOL_LONG_FIRST_BREAK_A1B_H1_MODAL_SUPPORTED**

Across all **9/9 frozen role × partition combinations**, the modal first upside breakout occurs at **H1**.

Therefore the A1 Development selection of H2 was a conditional-survivor effect, not evidence that most SOL LONG breakouts begin at H2. The correct structural statement from the frozen A1 topology is: **the first completed-close breakout is most often an H1 event**.

This still does not define the entry. The next experiment may study whether entry should occur before that visit, on the breakout confirmation, or on a post-break retest.

Research only. Live Baba Bot remains unchanged.
