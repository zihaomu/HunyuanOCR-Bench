# Machine Branch Runbook

## 1. Create the branch

Use a stable lowercase identifier that includes vendor, accelerator, and host:

```bash
./scripts/new-machine-branch.sh amd amd-w7900d-host01
./scripts/new-machine-branch.sh nvidia nvidia-h20-host01
```

Do not edit shared code in a machine branch. If the shared harness is wrong,
fix it on a new kickoff revision and rerun every affected result.

## 2. Complete the profile

The machine profile is evidence, not merely configuration. Record:

- exact accelerator model, count, and memory;
- OS, kernel/driver, ROCm or CUDA version;
- PyTorch and inference framework versions;
- image name and immutable digest;
- precision, TP, and inference method (`ar` or `dflash`);
- endpoint model alias.

`run-all.sh` captures `rocm-smi`/`rocminfo` or `nvidia-smi` output in addition
to the declared profile.

## 3. Start the endpoint

Each machine owns its deployment. The common requirement is:

```text
GET  <base_url>/models
POST <base_url>/chat/completions
served model ID: tencent/HunyuanOCR
```

AMD containers normally need `/dev/kfd`, `/dev/dri`, video/render group access,
and `HIP_VISIBLE_DEVICES`. NVIDIA containers normally need `--gpus` or the
NVIDIA Container Toolkit and `CUDA_VISIBLE_DEVICES`. Those flags are deliberately
not embedded in the shared benchmark.

The accuracy runner currently invokes the pinned HunyuanOCR batch client on the
host. Set `PYTHON_BIN` if its dependencies live in a virtual environment:

```bash
PYTHON_BIN=/path/to/runtime/bin/python ./scripts/run-all.sh machines/<id>.json
```

## 4. Pre-run controls

- Reserve the declared accelerator(s); capture competing processes.
- Use a fixed power/performance policy and record deviations in `notes`.
- Disable unrelated workloads when measuring speed.
- Keep the endpoint alive throughout speed and accuracy inference.
- Do not modify generation parameters in the machine branch.

## 5. Execute and inspect

```bash
./scripts/check-endpoint.sh machines/<id>.json
./scripts/run-all.sh machines/<id>.json quick9-c1
```

Inspect the canonical `result.json` and both verification reports before commit.
Zero-byte Markdown is allowed when it is the model's successful output; a failed
inference record is not.

## 6. Publish

Only commit the machine profile and its canonical result directory. Never add
`assets/`, `work/`, model weights, dataset images, predictions, evaluator render
files, or endpoint logs.

```bash
./scripts/validate-machine-branch.sh
git status --short
git add machines/<id>.json results/<id>/
git commit -m "results: add <id> HunyuanOCR benchmark"
git push -u origin machine/<id>
```
