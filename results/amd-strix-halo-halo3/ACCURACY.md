# AMD Strix Halo Accuracy Configuration

This page contains only the configuration behind the Strix Halo column in the
root accuracy table. The run covered all 1,651 OmniDocBench v1.6 pages on the
integrated Radeon 8060S in an AMD Ryzen AI Max+ 395.

- [Pinned benchmark contract](../../protocol/benchmark-v1.json)
- [Machine profile](../../machines/amd-strix-halo-halo3.json)
- [Complete c2 evidence](full1651-c2-accuracy-20260826T065105Z-ar/README.md)
- [Accuracy metrics](full1651-c2-accuracy-20260826T065105Z-ar/accuracy.json)

## Runtime

| Setting | Value |
| --- | --- |
| Accelerator | AMD Radeon 8060S (`gfx1151`), integrated in Ryzen AI Max+ 395 |
| Device memory visible to PyTorch | 120 GiB unified memory |
| Serving framework | vLLM `0.1.dev1+ga1274c75b.d20260807` |
| Precision | BF16 |
| Tensor parallelism | 1 |
| Served model | `tencent/HunyuanOCR` |
| Container image | `ghcr.io/inferstation/vllm-rocm-halo:latest` |
| Container digest | `sha256:ff89ae6d0cc44eb70b9bada85b535652058c0daf3c2c2c542da844b6f592cae6` |
| ROCm / PyTorch | ROCm 7.15.0 / PyTorch 2.14.0a0+rocm7.15.0a20260719 |
| Accuracy endpoint | HIP0, port 8000 |
| Fixed KV cache | 16 GiB |
| Model context | 131072 tokens |
| Maximum batched tokens / sequences | 131072 / 8 |

Start the accuracy endpoint with the fixed 16 GiB KV cache captured by the run:

```bash
BENCH_ROOT=/path/to/HunyuanOCR-Bench
RUNTIME_CACHE=/path/to/vllm-cache

docker run -d --name hunyuanocr-strix-halo-accuracy \
  --device=/dev/kfd --device=/dev/dri \
  --group-add 44 --group-add 992 \
  --security-opt seccomp=unconfined --security-opt label=disable \
  --ipc=host --shm-size=32g \
  -p 8000:8000 \
  -e HIP_VISIBLE_DEVICES=0 -e CUDA_VISIBLE_DEVICES=0 \
  -e HF_HOME=/runtime-cache/huggingface -e XDG_CACHE_HOME=/runtime-cache \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -v "$RUNTIME_CACHE:/runtime-cache" \
  -v "$BENCH_ROOT/assets/models/HunyuanOCR:/model:ro" \
  ghcr.io/inferstation/vllm-rocm-halo@sha256:ff89ae6d0cc44eb70b9bada85b535652058c0daf3c2c2c542da844b6f592cae6 \
  --model /model \
  --served-model-name tencent/HunyuanOCR \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --limit-mm-per-prompt '{"image":4,"video":0}' \
  --trust-remote-code \
  --kv-cache-memory-bytes 17179869184 \
  --skip-mm-profiling \
  --max-model-len 131072 \
  --max-num-batched-tokens 131072 \
  --max-num-seqs 8 \
  --host 0.0.0.0 \
  --port 8000
```

## Run Accuracy

Prepare the pinned assets, then invoke the upstream batch client directly to
preserve the published run's concurrency 2:

```bash
HF_ENDPOINT=https://hf-mirror.com ./scripts/prepare-assets.sh

RUN_ID=reproduce-strix-halo-accuracy-c2
PYTHON_BIN=/path/to/hunyuan-runtime/bin/python
mkdir -p "work/$RUN_ID/predictions"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" \
  assets/src/HunyuanOCR/inference/vLLM/batch_infer.py \
  --image-dir assets/data/OmniDocBench_v1_6/images \
  --out-dir "work/$RUN_ID/predictions" \
  --host 127.0.0.1 --ports 8000 \
  --model tencent/HunyuanOCR --task-type doc_parse \
  --max-tokens 32768 --repetition-penalty 1.08 --concurrency 2
PYTHONPATH=src python3 -m hunyuanocr_bench.cli verify-predictions \
  --gt assets/data/OmniDocBench_v1_6/OmniDocBench.json \
  --prediction-dir "work/$RUN_ID/predictions" \
  --output "work/$RUN_ID/prediction-verification.json"
./scripts/run-evaluation.sh "$RUN_ID"
PYTHONPATH=src python3 -m hunyuanocr_bench.cli accuracy-report \
  --machine machines/amd-strix-halo-halo3.json \
  --source "$(<work/$RUN_ID/evaluator-summary.path)" \
  --output "work/$RUN_ID/accuracy.json"
```

Generation uses document parsing, `max_tokens=32768`, `temperature=0`,
`top_p=1`, `top_k=-1`, `repetition_penalty=1.08`, and official document
post-processing. These defaults are set by the pinned upstream batch client;
the command records the non-default repetition penalty and concurrency.

Concurrency 2 differs from the protocol-required concurrency 1. The score is
therefore labeled `c2` and is complete comparison evidence rather than a
canonical leaderboard result.
