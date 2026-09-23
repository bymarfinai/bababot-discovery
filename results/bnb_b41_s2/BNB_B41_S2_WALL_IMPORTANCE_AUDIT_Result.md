# BNB B41-S2 — Wall Importance Audit

**Status: BNB_B41_S2_WALL_IMPORTANCE_AUDIT_COMPLETE**

Parent wall signature: `4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6`
S2 signature: `53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2`

S2 is descriptive and non-trading. It measures what happens when the frozen B41-S1 levels are reached.

## Core audit

| Period | Family | Side | Touch | Touch rate | Med touch | Med overshoot | NE25 | NE50 | Med reaction | Close inside | Next wall |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | MID | UPPER | 540/1096 | 49.3% | 450m | 0.864x | 18.0% | 33.9% | 0.976x | 50.6% | 43.1% |
| DEV | MID | LOWER | 544/1096 | 49.6% | 432m | 0.905x | 19.1% | 33.5% | 0.929x | 56.2% | 44.3% |
| DEV | WALL | UPPER | 233/1096 | 21.3% | 660m | 0.484x | 28.3% | 50.6% | 0.494x | 51.9% | 33.0% |
| DEV | WALL | LOWER | 241/1096 | 22.0% | 825m | 0.478x | 28.2% | 51.5% | 0.515x | 59.3% | 26.1% |
| DEV | EXTREME | UPPER | 77/1096 | 7.0% | 790m | 0.331x | 40.3% | 67.5% | 0.410x | 50.6% | — |
| DEV | EXTREME | LOWER | 63/1096 | 5.7% | 825m | 0.413x | 41.3% | 52.4% | 0.455x | 58.7% | — |
| DEV | RV1 | UPPER | 307/1096 | 28.0% | 605m | 0.611x | 27.7% | 43.3% | 0.586x | 47.6% | — |
| DEV | RV1 | LOWER | 327/1096 | 29.8% | 715m | 0.625x | 24.8% | 43.1% | 0.595x | 56.0% | — |
| REF | MID | UPPER | 291/603 | 48.3% | 495m | 0.830x | 19.9% | 34.7% | 0.833x | 50.5% | 43.3% |
| REF | MID | LOWER | 279/603 | 46.3% | 495m | 0.974x | 15.4% | 28.0% | 0.845x | 51.6% | 40.1% |
| REF | WALL | UPPER | 126/603 | 20.9% | 775m | 0.439x | 32.5% | 55.6% | 0.466x | 52.4% | 29.4% |
| REF | WALL | LOWER | 112/603 | 18.6% | 762m | 0.370x | 28.6% | 57.1% | 0.528x | 62.5% | 37.5% |
| REF | EXTREME | UPPER | 37/603 | 6.1% | 900m | 0.472x | 32.4% | 51.4% | 0.381x | 45.9% | — |
| REF | EXTREME | LOWER | 42/603 | 7.0% | 922m | 0.329x | 40.5% | 61.9% | 0.399x | 61.9% | — |
| REF | RV1 | UPPER | 177/603 | 29.4% | 780m | 0.532x | 27.7% | 48.6% | 0.577x | 54.8% | — |
| REF | RV1 | LOWER | 195/603 | 32.3% | 710m | 0.527x | 28.2% | 47.2% | 0.559x | 61.0% | — |
| ALL | MID | UPPER | 831/1699 | 48.9% | 465m | 0.848x | 18.7% | 34.2% | 0.922x | 50.5% | 43.2% |
| ALL | MID | LOWER | 823/1699 | 48.4% | 445m | 0.949x | 17.9% | 31.6% | 0.898x | 54.7% | 42.9% |
| ALL | WALL | UPPER | 359/1699 | 21.1% | 705m | 0.458x | 29.8% | 52.4% | 0.485x | 52.1% | 31.8% |
| ALL | WALL | LOWER | 353/1699 | 20.8% | 805m | 0.465x | 28.3% | 53.3% | 0.524x | 60.3% | 29.7% |
| ALL | EXTREME | UPPER | 114/1699 | 6.7% | 820m | 0.358x | 37.7% | 62.3% | 0.386x | 49.1% | — |
| ALL | EXTREME | LOWER | 105/1699 | 6.2% | 900m | 0.367x | 41.0% | 56.2% | 0.411x | 60.0% | — |
| ALL | RV1 | UPPER | 484/1699 | 28.5% | 680m | 0.584x | 27.7% | 45.2% | 0.585x | 50.2% | — |
| ALL | RV1 | LOWER | 522/1699 | 30.7% | 712m | 0.601x | 26.1% | 44.6% | 0.586x | 57.9% | — |

## Preregistered importance support vs MID

| Family | Side | DEV N | REF N | DEV NE25 Δ | REF NE25 Δ | DEV overshoot Δ | REF overshoot Δ | Supported |
|---|---|---:|---:|---:|---:|---:|---:|---|
| WALL | UPPER | 233 | 126 | +10.4pp | +12.6pp | -0.380x | -0.391x | YES |
| WALL | LOWER | 241 | 112 | +9.1pp | +13.2pp | -0.427x | -0.604x | YES |
| EXTREME | UPPER | 77 | 37 | +22.3pp | +12.5pp | -0.533x | -0.358x | NO |
| EXTREME | LOWER | 63 | 42 | +22.2pp | +25.1pp | -0.492x | -0.645x | NO |
| RV1 | UPPER | 307 | 177 | +9.7pp | +7.8pp | -0.253x | -0.298x | YES |
| RV1 | LOWER | 327 | 195 | +5.7pp | +12.8pp | -0.281x | -0.447x | YES |

## S2 interpretation boundary
Q80 WALL both-side decision-point support: **YES**.
This result does not establish long/short direction or reversal edge.
B41-S3 may use the persisted event ledger to discover interaction character without changing the S1 wall definitions.
