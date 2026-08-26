# AMD Radeon PRO W7900D Results

Machine branch: `machine/amd-w7900d-gpu1-xw-k8s-test-m-001`

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
| Average latency | 4.662196 s/page |
| P50 latency | 2.968424 s |
| P95 latency | 21.928563 s |
| Page throughput | 0.214491 page/s |
| Token throughput | 90.7059 token/s |
| Measured wall time | 125.922038 s |

The run used one visible AMD Radeon PRO W7900D (physical GPU1), tensor
parallelism 1, and request concurrency 1. GPU0 and GPU2 did not participate in
the speed measurement. Request settings were `temperature=0`,
`max_tokens=8000`, and `top_k=1`.

The fixed inventory contains three text, three formula, and three table pages,
with one low-, medium-, and high-complexity case in each category. Its SHA-256
is `28f59abf2efbac69a32a3914e184e63d160accb90474036b51105ec7817d72eb`.

## Evidence

- [Machine profile](../../machines/amd-w7900d-gpu1-xw-k8s-test-m-001.json)
- [Quick9 inventory](../../protocol/omnidocbench-v1.6-speed-quick9.txt)
- [Speed summary](interim-speed-quick9-c1/speed.json)
- [Per-request records](interim-speed-quick9-c1/speed-records.jsonl)

Evidence SHA-256:

```text
speed.json          e041d22904efefda9398edfac676d632026a646f0f32c5701ee22a01a828d4ba
speed-records.jsonl 87bd69cf65a0550b8bc39b7fdd99f5c1aafa4e67859b16efcdb405498c83cac4
```
