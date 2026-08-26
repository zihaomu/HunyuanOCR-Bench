# Local-Evaluator Accuracy Evidence

This directory records a complete 1,651-page OmniDocBench v1.6 accuracy run.
The OCR predictions passed the repository inventory gate, and the pinned
OmniDocBench evaluator source and benchmark config were used without changes.

This evidence is intentionally **non-canonical**: at the user's request, the
evaluation reused the RTX 4090 speed image plus a workspace-local evaluator
toolchain instead of the protocol-pinned evaluator image. No `result.json` is
present, so the repository aggregator will not add this run to the canonical
accuracy leaderboard.

## Accuracy

| Metric | Result |
| --- | ---: |
| Overall | 95.443681 |
| TextEdit | 0.036132 |
| FormulaCDM | 94.651074 |
| TableTEDS | 95.293169 |
| TableTEDS-S | 96.385071 |
| OrderEdit | 0.127247 |

The official formula is
`((1 - TextEdit) * 100 + FormulaCDM + TableTEDS) / 3`.

## Coverage Gates

| Gate | Result |
| --- | ---: |
| Dataset pages matched | 1,651 |
| Prediction Markdown files | 1,651 |
| Missing / failed prediction records | 0 / 0 |
| Formula CDM samples | 2,352 |
| Formula CDM errors / exceptions / timeouts | 0 / 0 / 0 |
| Table TEDS samples | 665 |
| Table TEDS errors / exceptions / timeouts | 0 / 0 / 0 |
| Formula page denominator | 313 |
| Table page denominator | 458 |

## Actual Evaluator Runtime

- Base image: `ghcr.io/inferstation/vllm-cuda-4090@sha256:6877023dee3a2456e00f468813607fd4ec21cd92c6386e5433e2f7422bf087a8`
- Image ID: `sha256:1f92b5cc10bd3a88d50259aeb6190fffc60299107ad93857eadd04deb01be21f`
- Evaluator source: `147cd5ac9472002f5751221d390bf00abdbc0d2f`
- Python 3.10.21; TeX Live 2025; pdfTeX 1.40.28
- ImageMagick 7.1.1-47; Ghostscript 9.55.0; CJK `gkai`
- `filelock==3.18.0`

The protocol-pinned evaluator image is
`ghcr.io/zeng-weijun/omnidocbench-eval@sha256:6116ad72172e763b5c43e963d5efebf2093f2362b975f58156ce4f6c9142e617`.
Because that image was not used, this run is evidence rather than a canonical
benchmark result.

The run-start machine capture predates the later explicit topology metadata in
the published profile. It is retained unchanged for chronology. The post-run
capture contains the finalized profile and a successful `nvidia-smi` hardware
capture.

## Files

- [Parsed accuracy](accuracy.json)
- [Evaluator run summary](evaluator-run-summary.json)
- [Evaluator stage execution](evaluator-stage-execution.json)
- [Evaluator metric result](evaluator-metric-result.json)
- [Evaluator runtime environment](evaluator-runtime-environment.json)
- [Prediction verification](prediction-verification.json)
- [Asset verification](assets-verification.json)
- [Run-start machine capture](machine-capture-run-start.json)
- [Post-run machine capture](machine-capture-postrun.json)
- [Runtime and artifact manifest](manifest.json)
