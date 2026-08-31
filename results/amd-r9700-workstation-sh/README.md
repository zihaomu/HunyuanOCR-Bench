# AMD Radeon AI PRO R9700 Results

Machine branch: `machine/amd-r9700-workstation-sh`

- [Serving configuration](SERVING.md)
- [Canonical result](amd-r9700-workstation-sh-20260827T014842Z-ar/result.json)

## Accuracy

OmniDocBench v1.6, all 1,651 pages, protocol-pinned evaluator image:

| Overall↑ | TextEdit↓ | FormulaCDM↑ | TableTEDS↑ | TableTEDS_S↑ | OrderEdit↓ |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 95.618309 | 0.034877 | 94.705744 | 95.636851 | 96.721318 | 0.124848 |

## Speed

`quick9-c1`, one GPU, TP=1, concurrency 1:

| Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |
| ---: | ---: | ---: | ---: |
| 2.457 | 6.879 | 0.4070 | 267.4 |

## Evidence

- [Accuracy JSON](amd-r9700-workstation-sh-20260827T014842Z-ar/accuracy.json)
- [Speed JSON](amd-r9700-workstation-sh-20260827T014842Z-ar/speed.json)
- [Machine capture](amd-r9700-workstation-sh-20260827T014842Z-ar/machine-capture.json)
- [Prediction verification](amd-r9700-workstation-sh-20260827T014842Z-ar/prediction-verification.json)
- [Evaluator summary](amd-r9700-workstation-sh-20260827T014842Z-ar/evaluator-summary.json)

The result was assembled and validated against the repository schema. Accuracy
uses the official 1,651-page protocol; speed uses the independent `quick9-c1`
profile.

\* Token/s is diagnostic only and is not comparable across different tokenizers.
