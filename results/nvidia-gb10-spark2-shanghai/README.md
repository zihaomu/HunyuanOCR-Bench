# NVIDIA GB10 DGX Spark Results

Machine branch: `machine/nvidia-gb10-spark2-shanghai`

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
| Average latency | 5.396540 s/page |
| P50 latency | 4.296761 s |
| P95 latency | 15.168406 s |
| Page throughput | 0.185304 page/s |
| Token throughput | 121.9712 token/s |
| Measured wall time | 145.732924 s |

The run used one NVIDIA GB10 on DGX Spark, tensor parallelism 1, bfloat16,
and request concurrency 1. The vLLM server used a 0.35 GPU-memory utilization
limit because the GB10 and host share 128 GB unified memory. Request settings
were `temperature=0`, `max_tokens=8000`, and `top_k=1`.

The fixed inventory contains three text, three formula, and three table pages,
with one low-, medium-, and high-complexity case in each category. Its SHA-256
is `28f59abf2efbac69a32a3914e184e63d160accb90474036b51105ec7817d72eb`.

## Evidence

- [Machine profile](../../machines/nvidia-gb10-spark2-shanghai.json)
- [Quick9 inventory](../../protocol/omnidocbench-v1.6-speed-quick9.txt)
- [Speed summary](interim-speed-quick9-c1/speed.json)
- [Per-request records](interim-speed-quick9-c1/speed-records.jsonl)

Evidence SHA-256:

```text
speed.json          1e62916e2b46be0253e209f379d2c8455c84e3f4942abe450dd64413d6f6850c
speed-records.jsonl 15e01d38cf126e89c1984f84b5a4e0d028eeadc60b8c5faa42691cdef84da173
```
