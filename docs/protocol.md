# Benchmark Protocol v1

## Accuracy provenance

Accuracy is evaluated over all 1651 OmniDocBench v1.6 pages. The evaluator source
is pinned to the final public v1.6 release boundary and uses the official
`end2end_dataset`, quick/MGAM matching, Python CDM, TEDS, and reading-order edit
distance implementation.

Metric units are intentionally asymmetric because they follow the paper table:

| Field | Unit | Direction |
| --- | --- | --- |
| Overall | percent | higher |
| TextEdit | fraction in $[0,1]$ | lower |
| FormulaCDM | percent | higher |
| TableTEDS | percent | higher |
| TableTEDS_S | percent | higher |
| OrderEdit | fraction in $[0,1]$ | lower |

`Overall` uses only text score $100(1-\text{TextEdit})$, FormulaCDM, and
TableTEDS. This definition is taken from the v1.6 evaluator's
`build_notebook_metric_summary` implementation. It is validated against two
published Table 12 rows to prevent an accidental four-component average.

## Inference boundary

Accuracy uses HunyuanOCR's pinned `batch_infer.py` because it includes the
model-specific streaming repetition guard, repeated-substring cleanup, and
Markdown normalization. Empty and very short outputs are preserved as model
outputs. They are not deleted or replaced before evaluation.

The accuracy endpoint runs concurrency 1 so hardware branches do not change model
outputs through different request scheduling. This is conservative and gives a
single request protocol for both speed and accuracy.

## Speed boundary

The timed interval starts immediately before the HTTP request and ends after the
complete JSON response. Image reads and base64 encoding occur before timing.
Warm-up requests are not included. Primary speed is page/s computed from the sum
of individual request latencies; process wall page/s is retained as a diagnostic.

The paper's `paper930-c1` profile has no warm-up because the published reference
script has none. The project `full1651-c1` profile has ten warm-up requests so
JIT compilation and lazy model initialization do not dominate cross-machine
measurements.

The public `full1651-c1` filename list is committed as
`protocol/omnidocbench-v1.6-full1651.txt` with SHA-256
`344d236b31d265915b723f3106613bbbeaf37cf988db7f58b76d88cbb7c2a1b4`.
`paper930-c1` is not accepted into canonical results until its exact upstream
inventory is publicly available. The speed client follows the paper snippet and
declares every base64 image as `image/png`; accuracy uses the pinned model client.

## Comparability rules

- Compare speed only when `profile_id`, inference method, accelerator count,
  precision, tensor parallelism, model revision, and protocol ID are visible.
- AR and DFlash results may be displayed together but must preserve their
  `inference_method` label.
- A multi-GPU run is not a single-GPU result and must report accelerator count.
- A failed speed request makes the speed run non-publishable. A response ending
  at the fixed `max_tokens=8000` limit remains part of the published latency,
  page/s, and token totals, matching the upstream benchmark script; its count is
  reported as `truncated`.
- Missing prediction files or failed inference records make accuracy
  non-publishable.
- Evaluator runtime is not part of model speed.

## Versioning

Any change to dataset pages, prompt, generation parameters, output post-processing,
evaluator code, overall formula, speed inventory, or timing boundary requires a
new protocol ID. Old result JSON remains immutable.
