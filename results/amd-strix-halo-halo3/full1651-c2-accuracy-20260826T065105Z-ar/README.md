# Full 1,651-page Strix Halo run (accuracy c2)

This directory publishes the complete accuracy evidence and full speed evidence
from the Strix Halo run. It is intentionally **not** a canonical leaderboard
result: accuracy used request concurrency 2 instead of the protocol's required
concurrency 1, and the `full1651-c1` speed run reached the 8,000-token limit on
13 pages. No `result.json` is provided, so repository aggregation will not
accept this directory as a protocol PASS.

## Accuracy

| Status | Pages | Overall↑ | TextEdit↓ | FormulaCDM↑ | TableTEDS↑ | TableTEDS_S↑ | OrderEdit↓ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PASS_LOCAL_EVALUATOR (c2) | 1,651 | 95.35 | 0.037 | 94.21 | 95.50 | 96.68 | 0.126 |

The prediction gate found 1,651 GT pages, 1,651 Markdown files, and 1,651
successful latest records, with no missing or extra predictions and no failed
records. Three Markdown files are zero-byte model outputs; they are preserved
as produced and included in evaluation.

The pinned OmniDocBench evaluator completed all 1,651 page matches, 2,352 CDM
formula samples, and 665 TEDS table samples. Page matching, CDM, and TEDS each
reported zero timeouts and zero errors. Metric page denominators were 1,557 for
text, 313 for formula, 458 for table, and 1,638 for reading order.

Accuracy inference used the upstream `batch_infer.py` client with two request
workers, `max_tokens=32768`, `repetition_penalty=1.08`, and document Markdown
post-processing. The vLLM endpoint used BF16, TP=1, a 16 GiB fixed KV cache,
`max_model_len=131072`, `max_num_batched_tokens=131072`, and
`max_num_seqs=8`. Concurrency 2 was selected by a local c1/c2/c4 throughput
comparison, but it remains a protocol deviation and the score must not be
compared as a strict c1 result.

## Speed

| Metric | Result |
| --- | ---: |
| Strict status | FAIL |
| Images / requests / successful | 1,651 / 1,651 / 1,651 |
| Failed / truncated | 0 / 13 |
| Average latency | 18.473307 s/page |
| P50 / P95 / P99 latency | 7.801051 / 86.535468 / 139.778957 s |
| Page throughput | 0.054132 page/s |
| Token throughput | 54.7279 token/s |
| Completion tokens | 1,669,171 |
| Request time sum | 30,499.429615 s |

Speed used the canonical `full1651-c1` request settings: concurrency 1, ten
warm-up pages, one measured repetition, `temperature=0`, `max_tokens=8000`, and
`top_k=1`. The run resumed from a byte-preserved 584-record checkpoint. Its
summary uses the sum of all request latencies because a single uninterrupted
wall interval does not exist. All requests succeeded, but 13 responses ended
with `finish_reason=length`, so the strict speed gate correctly reports FAIL.

## Provenance

- Accelerator: AMD Ryzen AI Max+ 395 with Radeon 8060S (`gfx1151`)
- Runtime: vLLM `0.1.dev1+ga1274c75b.d20260807`, ROCm 7.15.0, BF16, TP=1
- Runtime image digest: `sha256:ff89ae6d0cc44eb70b9bada85b535652058c0daf3c2c2c542da844b6f592cae6`
- HunyuanOCR code: `c55965d3da1e6f41987abec8068f2e70851318bc`
- HunyuanOCR weights: `449e7d471a8a1ef5bd5d652e4881183d7252cbc7`
- OmniDocBench data: `d386947f7fc3bafdcd756c8485845a2f43a19875`
- OmniDocBench evaluator: `147cd5ac9472002f5751221d390bf00abdbc0d2f`
- Evaluator image digest: `sha256:6116ad72172e763b5c43e963d5efebf2093f2362b975f58156ce4f6c9142e617`

Evidence:

- [Accuracy report](accuracy.json)
- [Evaluator summary](evaluator-summary.json)
- [Prediction verification](prediction-verification.json)
- [Full speed summary](speed.json)
- [Full speed records](speed-records.jsonl)
- [Asset verification](assets-verification.json)
- [Machine capture](machine-capture.json)
- [Machine profile snapshot](machine.json)

Evidence SHA-256:

```text
accuracy.json                 057c4a8bccbd6a767e80a85dda506c45cfd5d3c32f6f2932128c831b02419cd7
assets-verification.json      2a3ea3144bd3d984256536e22267243a91614c975bf0bde54cad0582e7cb88ce
evaluator-summary.json        f083fc0b22755935c13bc0a8608fc42bccf1ade6c6c9f346c97428ef390a1264
machine-capture.json          b2b5f6c647891280c2b2af96b01c7ff5db7b6d91a1f6bb7c48f9bb8c285a682e
machine.json                  c11b8f9ef391f0e56edeaa378b1d012fb2a4773ce4b33eae6465056a46f7daa7
prediction-verification.json  2e6ce188d3fccf6857ae097b486830c892e1b8c238383cda425ea6613ad0e66f
speed.json                    2c47e2905221e6355fe6c6779b0147c9cdbce3f21d9e8b81bb695ed4122ebc26
speed-records.jsonl           568374e76ecdd5f7866ef7af6e735452f4d5c84482d8dfba02d13b63625dd733
```
