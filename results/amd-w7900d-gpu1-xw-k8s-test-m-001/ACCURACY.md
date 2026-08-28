# AMD Radeon PRO W7900D Accuracy Configuration

This page contains only the configuration behind the W7900D column in the root
accuracy table. The canonical run covered all 1,651 OmniDocBench v1.6 pages.

- [Pinned benchmark contract](../../protocol/benchmark-v1.json)
- [Machine profile](../../machines/amd-w7900d-gpu1-xw-k8s-test-m-001.json)
- [Canonical result](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/result.json)
- [Accuracy metrics](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/accuracy.json)
- [Prediction quality gate](amd-w7900d-gpu1-xw-k8s-test-m-001-20260826-quick9-c1-r1/prediction-quality.json)

## Runtime

| Setting | Value |
| --- | --- |
| Accelerator | AMD Radeon PRO W7900D (`gfx1100`) |
| Serving framework | vLLM `0.27.0` |
| Precision | BF16 |
| Tensor parallelism | 1 per endpoint |
| Served model | `tencent/HunyuanOCR` |
| Container image | `hunyuanocr-base:rocm7.2.4-v0` |
| Container digest | `sha256:83fef91f42e0306dbf81d2d225086234e7fbc770eeba16a02a9a11f57e17d335` |
| ROCm / PyTorch | ROCm 7.2.4 / PyTorch 2.10.0+rocm7.2.4.git3d3aa833 |
| Accuracy endpoints | GPU1:18016, GPU2:18017, GPU5:18020, GPU6:18021 |
| Maximum model length / batched tokens | 131072 / 131072 |

`MIOPEN_FIND_MODE=2` is required for this exact ROCm 7.2.4, MIOpen 3.5.1,
and gfx1100 stack. Without it, some image shapes produced coordinate-only
placeholders. Start four independent TP=1 replicas with one worker per endpoint:

```bash
WORKSPACE=/path/to/hunyuanOCR_workspace

for pair in "1:18016" "2:18017" "5:18020" "6:18021"; do
  GPU=${pair%%:*}
  PORT=${pair##*:}
  docker run -d --name "hyocr-miopen2-gpu${GPU}" \
    --network host \
    --device=/dev/kfd --device=/dev/dri \
    --group-add 44 --group-add 993 \
    --security-opt seccomp=unconfined --ipc=host --shm-size=16g \
    -e "HIP_VISIBLE_DEVICES=${GPU}" \
    -e MIOPEN_FIND_MODE=2 \
    -e HF_HOME=/workspace/cache/huggingface \
    -e PYTORCH_ROCM_ARCH=gfx1100 \
    -e VLLM_TARGET_DEVICE=rocm \
    -v "$WORKSPACE:/workspace" \
    --entrypoint vllm \
    hunyuanocr-base:rocm7.2.4-v0 \
    serve /workspace/models/HunyuanOCR \
    --served-model-name tencent/HunyuanOCR \
    -tp 1 \
    --limit-mm-per-prompt '{"image":4,"video":0}' \
    --trust-remote-code \
    --port "$PORT" \
    --gpu-memory-utilization 0.90 \
    --max-model-len 131072 \
    --max-num-batched-tokens 131072 \
    --skip-mm-profiling
done
```

## Run Accuracy

```bash
HF_ENDPOINT=https://hf-mirror.com ./scripts/prepare-assets.sh

MACHINE=machines/amd-w7900d-gpu1-xw-k8s-test-m-001.json
RUN_ID=reproduce-w7900d-accuracy
PYTHON_BIN=/path/to/hunyuan-runtime/bin/python \
  ./scripts/run-accuracy-inference.sh "$MACHINE" "$RUN_ID"
./scripts/run-evaluation.sh "$RUN_ID"
PYTHONPATH=src python3 -m hunyuanocr_bench.cli accuracy-report \
  --machine "$MACHINE" \
  --source "$(<work/$RUN_ID/evaluator-summary.path)" \
  --output "work/$RUN_ID/accuracy.json"
```

The committed machine profile selects four ports, so client concurrency is 4:
one in-flight request per independent replica. Each request uses the original
benchmark image, document parsing, `max_tokens=32768`, `temperature=0`,
`top_p=1`, `top_k=-1`, `repetition_penalty=1.08`, and official document
post-processing. The pinned evaluator produced Overall 95.593058.
