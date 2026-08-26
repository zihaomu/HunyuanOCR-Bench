# NVIDIA GeForce RTX 4090 Results

Machine branch: `machine/nvidia-rtx4090-amd-sys-741ge-tnrt`

## Interim Speed Result

The `quick9-c1` speed benchmark is complete and passed. Accuracy is not included
in this interim publication: full inference over all 1,651 OmniDocBench v1.6
pages and the official evaluator must finish before accuracy is published.

| Metric | Result |
| --- | ---: |
| Status | PASS |
| Images | 9 |
| Warm-up requests | 9 |
| Measured repetitions | 3 |
| Measured requests | 27 |
| Successful / failed / truncated | 27 / 0 / 0 |
| Average latency | 1.682490 s/page |
| P50 latency | 1.402098 s |
| P95 latency | 4.569469 s |
| Page throughput | 0.594357 page/s |
| Token throughput | 392.6721 token/s |
| Measured wall time | 45.502569 s |

The run used one visible NVIDIA GeForce RTX 4090 (physical GPU0), tensor
parallelism 1, and request concurrency 1. GPU1 did not participate in the speed
measurement. Request settings were `temperature=0`, `max_tokens=8000`, and
`top_k=1`.

The fixed inventory contains three text, three formula, and three table pages,
with one low-, medium-, and high-complexity case in each category. Its SHA-256
is `28f59abf2efbac69a32a3914e184e63d160accb90474036b51105ec7817d72eb`.

## Evidence

- [Machine profile](../../machines/nvidia-rtx4090-amd-sys-741ge-tnrt.json)
- [Quick9 inventory](../../protocol/omnidocbench-v1.6-speed-quick9.txt)
- [Speed summary](interim-speed-quick9-c1/speed.json)
- [Per-request records](interim-speed-quick9-c1/speed-records.jsonl)

Evidence SHA-256:

```text
speed.json          6acb979c721d711df640f4aa60b1904942314760837756f1c261421f8af4e62f
speed-records.jsonl 5ba466c3a2f7311bfb527546951abdd2c8a509c6283b1a2802d0357160b7a62c
```
