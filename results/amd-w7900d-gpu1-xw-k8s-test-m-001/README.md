# AMD Radeon PRO W7900D Results

Machine branch: `machine/amd-w7900d-gpu1-xw-k8s-test-m-001`

## Result Summary

HunyuanOCR-1.5 was evaluated on all 1,651 OmniDocBench v1.6 pages with the pinned official evaluator. The corrected accuracy run uses `MIOPEN_FIND_MODE=2`; the earlier 46.1285 result was replaced because the default MIOpen find path caused systemic coordinate-placeholder outputs on gfx1100.

| Accuracy metric | Result | Paper reference |
| --- | ---: | ---: |
| Overall | **95.5931** | 94.7400 |
| TextEdit | **0.036086** | 0.039000 |
| FormulaCDM | **95.1298** | 94.5000 |
| TableTEDS | **95.2580** | 93.6700 |
| TableTEDS_S | **96.3626** | 94.7100 |
| OrderEdit | **0.124724** | 0.129000 |

Overall is 0.8531 points above the paper reference. The official evaluation covered all 1,651 pages, with denominators of 1,557 text pages, 313 formula pages, 458 table pages, and 1,638 reading-order pages. Page matching, CDM, and TEDS completed without errors, exceptions, or timeouts.

## Accuracy Runtime

Accuracy inference used the original benchmark images and four independent TP=1 replicas:

| Physical GPU | Endpoint | Completed pages |
| ---: | ---: | ---: |
| 1 | 18016 | 416 |
| 2 | 18017 | 407 |
| 5 | 18020 | 388 |
| 6 | 18021 | 440 |

Each worker was permanently bound to one endpoint, limiting every replica to one in-flight request. All service processes inherited `MIOPEN_FIND_MODE=2`. Request settings were `temperature=0`, `top_p=1`, `top_k=-1`, `max_tokens=32768`, and `repetition_penalty=1.08`.

Before the full run, the fixed 10-page historical-failure set passed 10/10 on every replica. Cleaned outputs were byte-identical across GPUs 1, 2, 5, and 6.

## Prediction Quality

All 1,651 requests succeeded, with no missing prediction files or failed inference records. The collapse-aware quality check reports `PASS_WITH_WARNINGS`:

| Quality signal | Count |
| --- | ---: |
| Request errors | 0 |
| Missing predictions | 0 |
| Pathological evaluable pages | 1 |
| Non-evaluable empty pages | 2 |
| Repetition early-stops | 4 |
| Outputs under 64 characters | 55 |

The one evaluable empty page consistently generated the same coordinate placeholder on all four replicas; its ground truth contains one short text block embedded in a full-page figure. The other two empty pages contain only `figure` and `text_mask` annotations and do not contribute text, formula, or table content. These isolated model misses remain part of the official score.

The quality gate rejects systemic collapse above 1% of the dataset (16 pages). As a regression check, it accepts this corrected run with warnings but rejects the replaced 46.1285 run, which had 237 pathological evaluable pages, 231 coordinate placeholders, and 154 early-stops.

## Speed Result

Speed remains the original single-GPU `quick9-c1` measurement and is not derived from the four-replica accuracy run.

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

The speed run used one visible W7900D (physical GPU1), TP=1, and request concurrency 1. GPU0 and all accuracy replicas other than GPU1 did not participate in the speed measurement. Its fixed inventory contains three text, three formula, and three table pages, with one low-, medium-, and high-complexity case in each category.

## Evidence

- [Machine profile](../../machines/amd-w7900d-gpu1-xw-k8s-test-m-001.json)
- [Canonical result](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/result.json)
- [Official accuracy report](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/accuracy.json)
- [Official evaluator summary](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/evaluator-summary.json)
- [Prediction verification](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/prediction-verification.json)
- [Prediction quality report](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/prediction-quality.json)
- [Accuracy inference summary](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/inference-summary.json)
- [Quick9 speed summary](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/speed.json)
- [Quick9 per-request records](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/speed-records.jsonl)
- [Quick9 inventory](../../protocol/omnidocbench-v1.6-speed-quick9.txt)
