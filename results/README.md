# Results Overview

This page summarizes the machine results currently merged into `main`. Values are generated from validated evidence in each machine directory.

## Speed Results

Rows are ordered by Page/s. The Profile column identifies the measurement inventory used for each result.

| Machine | Accelerator | Profile | Avg latency (s)↓ | P95 (s)↓ | Page/s↑ | Token/s* |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [nvidia-rtx4090-amd-sys-741ge-tnrt](nvidia-rtx4090-amd-sys-741ge-tnrt/) | 1× NVIDIA GeForce RTX 4090 | quick9-c1 | 1.682 | 4.569 | 0.5944 | 392.7 |
| [amd-w7900d-gpu1-xw-k8s-test-m-001](amd-w7900d-gpu1-xw-k8s-test-m-001/) | 1× AMD Radeon PRO W7900D (gfx1100) | quick9-c1 | 4.662 | 21.929 | 0.2145 | 90.7 |
| [nvidia-gb10-spark2-shanghai](nvidia-gb10-spark2-shanghai/) | 1× NVIDIA GB10 | quick9-c1 | 5.397 | 15.168 | 0.1853 | 122.0 |
| [amd-strix-halo-halo3](amd-strix-halo-halo3/) | 1× AMD Ryzen AI Max+ 395 w/ Radeon 8060S (gfx1151) | sampled-30-from-584 | 10.371 | 32.408 | 0.0964 | 80.9 |

## Accuracy Status

No complete accuracy result has been published yet. Accuracy requires full 1,651-page inference and the official OmniDocBench evaluator.

## Detailed Outputs

- [Speed leaderboard](../leaderboards/speed.md)
- [Structured speed results](../leaderboards/speed-results.json)
- [Accuracy leaderboard](../leaderboards/accuracy.md)

\* Token/s is diagnostic only and is not comparable across different tokenizers.
