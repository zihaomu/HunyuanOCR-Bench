# HunyuanOCR-Bench

HunyuanOCR-Bench is the shared benchmark protocol for **HunyuanOCR-1.5** on
**OmniDocBench v1.6** across AMD and NVIDIA accelerators. The repository keeps
benchmark logic immutable on `kickoff`, stores one machine's evidence on each
`machine/<machine-id>` branch, and aggregates accepted results on `main`.

The two primary outputs are:

1. **Speed**: average end-to-end page latency and page/s under concurrency 1.
2. **Accuracy**: OmniDocBench v1.6 over all 1,651 pages. The local columns use
   the pinned HunyuanOCR-1.5 1B weights, dataset, and evaluator source/config;
   the paper column is the published Table 12 reference.

### Speed (`quick9-c1`)

| Accelerator / configuration | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |
| --- | ---: | ---: | ---: | ---: |
| [NVIDIA RTX 4090](results/nvidia-rtx4090-amd-sys-741ge-tnrt/SERVING.md) | 1.682 | 4.569 | 0.5944 | 392.7 |
| [AMD Radeon PRO W7900D](results/amd-w7900d-gpu1-xw-k8s-test-m-001/SERVING.md) | 4.662 | 21.929 | 0.2145 | 90.7 |
| [AMD Ryzen AI Max+ 395 (Radeon 8060S)](results/amd-strix-halo-halo3/SERVING.md) | 4.962 | 14.020 | 0.2015 | 132.2 |
| [NVIDIA GB10](results/nvidia-gb10-spark2-shanghai/) | 5.397 | 15.168 | 0.1853 | 122.0 |
| [AMD Radeon AI PRO R9700](results/amd-r9700-workstation-sh/SERVING.md) | 5.700 | 16.534 | 0.1754 | 115.2 |

All rows above use the same fixed nine-page inventory, one GPU, request
concurrency 1, one warm-up per page, and three measured repetitions. Page/s is
the primary speed metric. Token/s is diagnostic only across tokenizers.

### Accuracy (OmniDocBench v1.6)

| Metric | [Official paper](https://arxiv.org/pdf/2607.04884v2) | [NVIDIA RTX 4090](results/nvidia-rtx4090-amd-sys-741ge-tnrt/SERVING.md) | [AMD Radeon PRO W7900D](results/amd-w7900d-gpu1-xw-k8s-test-m-001/SERVING.md) | [AMD Strix Halo (Ryzen AI Max+ 395 / Radeon 8060S, c2)](results/amd-strix-halo-halo3/SERVING.md) | [AMD Radeon AI PRO R9700](results/amd-r9700-workstation-sh/SERVING.md) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall↑ | 94.74 | 95.443681 | 95.593058 | 95.345115 | 95.618309 |
| TextEdit↓ | 0.039 | 0.036132 | 0.036086 | 0.036755 | 0.034877 |
| FormulaCDM↑ | 94.50 | 94.651074 | 95.129761 | 94.213906 | 94.705744 |
| TableTEDS↑ | 93.67 | 95.293169 | 95.258004 | 95.496913 | 95.636851 |
| TableTEDS_S↑ | 94.71 | 96.385071 | 96.362554 | 96.682094 | 96.721318 |
| OrderEdit↓ | 0.129 | 0.127247 | 0.124724 | 0.125789 | 0.124848 |

The paper column is the HunyuanOCR-1.5 reference from Table 12. The
[R9700 evidence](results/amd-r9700-workstation-sh/amd-r9700-workstation-sh-20260827T014842Z-ar/result.json)
and
[W7900D evidence](results/amd-w7900d-gpu1-xw-k8s-test-m-001/amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/result.json)
are canonical and used the protocol-pinned evaluator image. The
[RTX 4090 evidence](results/nvidia-rtx4090-amd-sys-741ge-tnrt/local-evaluator-accuracy-20260826T063000Z-ar/README.md)
used the pinned evaluator source/config but a version-aligned local evaluator
toolchain, so it is complete comparison evidence rather than a canonical result.
The [Strix Halo evidence](results/amd-strix-halo-halo3/full1651-c2-accuracy-20260826T065105Z-ar/README.md)
used the protocol-pinned evaluator image and all 1,651 pages, but accuracy
request concurrency was 2 instead of the required 1. It is therefore labeled
`c2` and reported as complete comparison evidence, not a canonical result.

## Benchmark Contract

The immutable contract lives in [protocol/benchmark-v1.json](protocol/benchmark-v1.json):

- HunyuanOCR code: `c55965d3da1e6f41987abec8068f2e70851318bc`
- HunyuanOCR weights: `449e7d471a8a1ef5bd5d652e4881183d7252cbc7`
- OmniDocBench v1.6 data: `d386947f7fc3bafdcd756c8485845a2f43a19875`
- OmniDocBench v1.6 evaluator: `147cd5ac9472002f5751221d390bf00abdbc0d2f`
- Dataset: 1651 pages, including 100 formula-hard, 99 layout-hard, and 97 table-hard pages
- Accuracy inference: AR, concurrency 1, `max_tokens=32768`, `top_k=-1`,
  `repetition_penalty=1.08`, official document post-processing
- Accuracy evaluation: official MGAM/quick-match and Python CDM implementation

The official overall score is:

```text
Overall = ((1 - TextEdit) * 100 + FormulaCDM + TableTEDS) / 3
```

`TableTEDS_S` and `OrderEdit` are reported but are not terms in `Overall`.

## Speed Profiles

`quick9-c1` is the project leaderboard speed profile. It contains nine fixed
pages: three text, three formula, and three table cases at low, medium, and high
complexity. Speed uses one GPU and request concurrency 1. Each case is warmed up
once and measured three times, for 27 timed requests. The request keeps the paper's
`temperature=0`, `max_tokens=8000`, and `top_k=1` settings.

`full1651-c1` remains an extended diagnostic profile; the full 1651 pages are
required for accuracy, not for the primary speed leaderboard.

For page latency `t_i` and generated token count `c_i`:

```text
Latency = sum(t_i) / N
Page/s  = N / sum(t_i)
Token/s = sum(c_i) / sum(t_i)
```

`paper930-c1` can reproduce the paper's 930-page speed profile only when the exact
`speed_eval_set_930.txt` is provided via `PAPER930_LIST`. The upstream docs refer
to this file, but it is absent from the public repository tree as of the pinned
revision. It is therefore non-publishable in protocol v1. Results from
`quick9-c1`, `full1651-c1`, and `paper930-c1` must never share one ranking.
Token/s is diagnostic only across different models because tokenizers differ.

## Repository Flow

```mermaid
flowchart LR
    K[kickoff: protocol and code] --> M1[machine/amd-...]
    K --> M2[machine/nvidia-...]
    M1 --> R1[profile + canonical results]
    M2 --> R2[profile + canonical results]
    R1 --> MAIN[main]
    R2 --> MAIN
    MAIN --> L[generated leaderboards]
```

Branch rules:

- `kickoff`: immutable benchmark implementation and protocol.
- `machine/<machine-id>`: created from `kickoff`; may change only
  `machines/<machine-id>.json` and `results/<machine-id>/`.
- `main`: merges verified machine results and regenerates `leaderboards/`.
- A benchmark protocol change creates a new protocol ID and a new kickoff tag;
  it does not silently rewrite old results.

## Start A Machine Branch

After cloning and checking out the committed `kickoff` baseline:

```bash
./scripts/new-machine-branch.sh amd amd-w7900d-host01
# or
./scripts/new-machine-branch.sh nvidia nvidia-h20-host01
```

Edit the generated machine file and replace every `REPLACE_ME`. Start a local
OpenAI-compatible HunyuanOCR endpoint using that machine's native ROCm or CUDA
runtime. The benchmark intentionally treats serving as a machine adapter; it
does not alter the shared request or metric logic.

Validate the endpoint:

```bash
./scripts/check-endpoint.sh machines/amd-w7900d-host01.json
```

## Prepare Assets

Large assets are stored under ignored `assets/` and never committed:

```bash
HF_ENDPOINT=https://hf-mirror.com ./scripts/prepare-assets.sh
```

The command checks every immutable revision, the 42,208,096-byte GT file and its
SHA-256, all 1651 images, and the exact v1.6 subset distribution.

Alternative Git mirrors can be supplied without changing protocol revisions:

```bash
HUNYUANOCR_GIT_URL=<mirror-url> \
OMNIDOCBENCH_GIT_URL=<mirror-url> \
./scripts/prepare-assets.sh
```

## Run The Benchmark

The default complete run is:

```bash
./scripts/run-all.sh machines/amd-w7900d-host01.json quick9-c1
```

This performs, in order:

1. asset and source revision verification;
2. machine/runtime evidence capture;
3. full 1651-page speed benchmark;
4. full 1651-page accuracy inference;
5. prediction inventory verification;
6. official OmniDocBench v1.6 evaluation;
7. canonical result assembly and validation.

Raw predictions and evaluator details remain in ignored `work/<run-id>/`.
Publishable evidence is copied to:

```text
results/<machine-id>/<run-id>/
├── result.json
├── machine.json
├── machine-capture.json
├── accuracy.json
├── speed.json
├── assets-verification.json
├── prediction-verification.json
├── evaluator-summary.json
└── speed-records.jsonl
```

Commit that directory on the machine branch, validate branch scope, and push:

```bash
./scripts/validate-machine-branch.sh
git add machines/<machine-id>.json results/<machine-id>/
git commit -m "results: add <machine-id> HunyuanOCR benchmark"
git push -u origin machine/<machine-id>
```

## Aggregate On Main

After merging accepted result branches:

```bash
./scripts/aggregate.sh
git add leaderboards/ results/README.md
```

The generated [results overview](results/) links each machine's evidence and combines
all available speed measurements in one table. Detailed accuracy and speed tables are in [leaderboards](leaderboards/).

## Development Checks

No Python runtime dependencies are required for the shared CLI. HunyuanOCR's
official accuracy batch client still requires the dependencies of the pinned
HunyuanOCR runtime, including `openai`.

```bash
make check
```

See [docs/protocol.md](docs/protocol.md) for metric provenance and
[docs/machine-runbook.md](docs/machine-runbook.md) for the AMD/NVIDIA operator checklist.
