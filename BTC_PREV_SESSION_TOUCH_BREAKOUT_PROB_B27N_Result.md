# B27N — Previous-Session Touch Count -> Breakout Probability

Derived deterministically from the frozen B27M event summary. No B27M labels or retest definitions were changed.

Primary configuration: 15m, previous-session High/Low, ±0.20% zone, both transitions combined.

`Target all` includes NO_BREAK in the denominator. `Target if break` asks: if the session eventually breaks either side after the threshold was reached, how often is it the repeatedly-touched side?

## Primary — 15m

| Partition | Level | Touches >= | N | Target all | Target if break | No break |
|---|---|---:|---:|---:|---:|---:|
| external | HIGH→BULL | 1x | 406 | 63.5% | 87.5% | 27.3% |
| external | HIGH→BULL | 2x | 154 | 60.4% | 93.0% | 35.1% |
| external | HIGH→BULL | 3x | 56 | 50.0% | 96.6% | 48.2% |
| external | HIGH→BULL | 4x | 10 | 50.0% | 100.0% | 50.0% |
| external | LOW→BEAR | 1x | 346 | 64.2% | 86.7% | 26.0% |
| external | LOW→BEAR | 2x | 128 | 57.8% | 92.5% | 37.5% |
| external | LOW→BEAR | 3x | 40 | 55.0% | 100.0% | 45.0% |
| external | LOW→BEAR | 4x | 4 | 0.0% | - | 100.0% |
| development | HIGH→BULL | 1x | 728 | 55.6% | 77.6% | 28.3% |
| development | HIGH→BULL | 2x | 271 | 46.1% | 82.2% | 43.9% |
| development | HIGH→BULL | 3x | 79 | 44.3% | 89.7% | 50.6% |
| development | HIGH→BULL | 4x | 19 | 31.6% | 100.0% | 68.4% |
| development | LOW→BEAR | 1x | 681 | 55.7% | 75.3% | 26.1% |
| development | LOW→BEAR | 2x | 211 | 45.5% | 77.4% | 41.2% |
| development | LOW→BEAR | 3x | 76 | 30.3% | 74.2% | 59.2% |
| development | LOW→BEAR | 4x | 16 | 31.2% | 83.3% | 62.5% |
| reference_validation | HIGH→BULL | 1x | 392 | 57.4% | 74.3% | 22.7% |
| reference_validation | HIGH→BULL | 2x | 122 | 51.6% | 82.9% | 37.7% |
| reference_validation | HIGH→BULL | 3x | 32 | 43.8% | 87.5% | 50.0% |
| reference_validation | HIGH→BULL | 4x | 12 | 41.7% | 83.3% | 50.0% |
| reference_validation | LOW→BEAR | 1x | 382 | 61.5% | 78.1% | 21.2% |
| reference_validation | LOW→BEAR | 2x | 120 | 50.0% | 72.3% | 30.8% |
| reference_validation | LOW→BEAR | 3x | 35 | 51.4% | 90.0% | 42.9% |
| reference_validation | LOW→BEAR | 4x | 9 | 66.7% | 100.0% | 33.3% |

## Secondary — 1H

| Partition | Level | Touches >= | N | Target all | Target if break | No break |
|---|---|---:|---:|---:|---:|---:|
| external | HIGH→BULL | 1x | 375 | 49.3% | 81.9% | 39.7% |
| external | HIGH→BULL | 2x | 51 | 27.5% | 100.0% | 72.5% |
| external | HIGH→BULL | 3x | 3 | 0.0% | - | 100.0% |
| external | HIGH→BULL | 4x | 0 | - | - | - |
| external | LOW→BEAR | 1x | 318 | 42.8% | 79.5% | 46.2% |
| external | LOW→BEAR | 2x | 51 | 13.7% | 100.0% | 86.3% |
| external | LOW→BEAR | 3x | 1 | 0.0% | - | 100.0% |
| external | LOW→BEAR | 4x | 0 | - | - | - |
| development | HIGH→BULL | 1x | 637 | 39.7% | 69.1% | 42.5% |
| development | HIGH→BULL | 2x | 106 | 26.4% | 87.5% | 69.8% |
| development | HIGH→BULL | 3x | 3 | 0.0% | - | 100.0% |
| development | HIGH→BULL | 4x | 0 | - | - | - |
| development | LOW→BEAR | 1x | 600 | 37.7% | 66.3% | 43.2% |
| development | LOW→BEAR | 2x | 76 | 11.8% | 81.8% | 85.5% |
| development | LOW→BEAR | 3x | 3 | 0.0% | - | 100.0% |
| development | LOW→BEAR | 4x | 0 | - | - | - |
| reference_validation | HIGH→BULL | 1x | 344 | 44.5% | 68.9% | 35.5% |
| reference_validation | HIGH→BULL | 2x | 42 | 35.7% | 88.2% | 59.5% |
| reference_validation | HIGH→BULL | 3x | 1 | 100.0% | 100.0% | 0.0% |
| reference_validation | HIGH→BULL | 4x | 0 | - | - | - |
| reference_validation | LOW→BEAR | 1x | 328 | 46.3% | 70.4% | 34.1% |
| reference_validation | LOW→BEAR | 2x | 37 | 18.9% | 46.7% | 59.5% |
| reference_validation | LOW→BEAR | 3x | 0 | - | - | - |
| reference_validation | LOW→BEAR | 4x | 0 | - | - | - |

## Diagnostic conclusion

On 15m, repeated touches generally make the direction of an eventual breakout more concentrated toward the repeatedly-touched side, but they also materially increase the chance that no breakout occurs before the active session ends. Therefore higher touch count is not by itself a higher unconditional breakout probability.

Diagnostic only; no threshold is promoted to a trading rule. Research only; live BBC unchanged.
