# AMD Strix Halo Results

Machine branch: `machine/amd-strix-halo-halo3`

## Quick9 Speed Result

The primary `quick9-c1` speed benchmark is complete and passed.

| Metric | Result |
| --- | ---: |
| Status | PASS |
| Images | 9 |
| Warm-up requests | 9 |
| Measured repetitions | 3 |
| Measured requests | 27 |
| Successful / failed / truncated | 27 / 0 / 0 |
| Average latency | 4.962382 s/page |
| P50 latency | 3.898368 s |
| P95 latency | 14.019636 s |
| Page throughput | 0.201516 page/s |
| Token throughput | 132.217 token/s |

The fixed inventory contains three text, three formula, and three table pages,
with one low-, medium-, and high-complexity case in each category. See the
[serving configuration](SERVING.md) for the runtime and startup command.

## Interim Speed Result

The 30-page sampled speed benchmark is complete and passed. Accuracy is not
included in this interim publication: full inference over all 1,651
OmniDocBench v1.6 pages and the official evaluator must finish before accuracy
is published. This sample is not an official `full1651-c1` leaderboard result.

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
- [Serving configuration](SERVING.md)
- [Quick9 inventory](../../protocol/omnidocbench-v1.6-speed-quick9.txt)
- [Quick9 speed summary](interim-speed-quick9-c1/speed.json)
- [Quick9 per-request records](interim-speed-quick9-c1/speed-records.jsonl)
- [Sample details](sampled-speed-30-20260826T065105Z-ar/README.md)
- [Speed summary](sampled-speed-30-20260826T065105Z-ar/sampled-speed.json)
- [Per-request records](sampled-speed-30-20260826T065105Z-ar/speed-records.jsonl)

Evidence SHA-256:

```text
sampled-speed.json  1ee2e5712a3e89a11a08359637abf407ffc4742316479ecb3133cc6788fec80a
speed-records.jsonl 9701377b80d4fe80b0adab14bb6dc1dd7232fd7a3b18e0c62b2c347a7eff6520
```