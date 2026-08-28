# AMD Strix Halo Results

Machine branch: `machine/amd-strix-halo-halo3`

## Full Accuracy Result

The complete 1,651-page accuracy run and pinned OmniDocBench evaluator are
finished. Accuracy used request concurrency 2, so this is a complete local
score but not the protocol's strict concurrency-1 leaderboard result.

| Status | Pages | Overall↑ | TextEdit↓ | FormulaCDM↑ | TableTEDS↑ | TableTEDS_S↑ | OrderEdit↓ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PASS_LOCAL_EVALUATOR (c2) | 1,651 | 95.35 | 0.037 | 94.21 | 95.50 | 96.68 | 0.126 |

Prediction verification passed with no missing, extra, or failed records. The
official evaluator completed with zero page-match, CDM, or TEDS timeouts and
errors. See the [complete run evidence](full1651-c2-accuracy-20260826T065105Z-ar/README.md).

## Full Speed Result

The `full1651-c1` speed run processed all 1,651 pages successfully at
18.473307 seconds/page (0.054132 page/s) and 54.7279 completion tokens/s. Its
strict status is **FAIL** because 13 pages reached the 8,000-token output limit.
The full records are published for transparency but are not accepted by the
canonical result validator.

## Sampled Speed Result

The 30-page sampled speed benchmark is complete and passed. Accuracy is not
part of this sampled artifact. This sample is not an official `full1651-c1`
leaderboard result.

| Metric | Result |
| --- | ---: |
| Status | PASS (sampled) |
| Images | 30 |
| Warm-up requests | 10 |
| Measured repetitions | 1 |
| Measured requests | 30 |
| Successful / failed / truncated | 30 / 0 / 0 |
| Average latency | 10.371472 s/page |
| P50 latency | 5.678095 s |
| P95 latency | 32.408052 s |
| Page throughput | 0.096418 page/s |
| Token throughput | 80.8532 token/s |
| Measured request time | 311.144174 s |

The run used the integrated Radeon 8060S (`gfx1151`) in an AMD Ryzen AI Max+
395, tensor parallelism 1, BF16 precision, and request concurrency 1. Request
settings were `temperature=0`, `max_tokens=8000`, and `top_k=1`.

The sample contains 30 deterministic, evenly spaced records selected without
using latency or token counts. It covers seven document sources and three
language groups. Its inventory SHA-256 is
`934258614d8ea4e5f54d4caed29a07b54324320a8125136d006a0721257c43ca`.
The sampled average latency differs from the available 584-page reference by
2.75%, and sampled token throughput differs by -1.76%.

## Evidence

- [Machine profile](../../machines/amd-strix-halo-halo3.json)
- [Complete accuracy and full speed evidence](full1651-c2-accuracy-20260826T065105Z-ar/README.md)
- [Final accuracy report](full1651-c2-accuracy-20260826T065105Z-ar/accuracy.json)
- [Official evaluator summary](full1651-c2-accuracy-20260826T065105Z-ar/evaluator-summary.json)
- [Full speed summary](full1651-c2-accuracy-20260826T065105Z-ar/speed.json)
- [Sample details](sampled-speed-30-20260826T065105Z-ar/README.md)
- [Speed summary](sampled-speed-30-20260826T065105Z-ar/sampled-speed.json)
- [Per-request records](sampled-speed-30-20260826T065105Z-ar/speed-records.jsonl)

Evidence SHA-256:

```text
sampled-speed.json  1ee2e5712a3e89a11a08359637abf407ffc4742316479ecb3133cc6788fec80a
speed-records.jsonl 9701377b80d4fe80b0adab14bb6dc1dd7232fd7a3b18e0c62b2c347a7eff6520
```