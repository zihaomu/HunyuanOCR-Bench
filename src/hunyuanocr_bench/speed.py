from __future__ import annotations

import base64
import json
import math
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .config import sha256_lines


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def select_images(
    image_dir: Path,
    expected_pages: int,
    gt_path: Path | None = None,
    sample_list: Path | None = None,
) -> list[Path]:
    if bool(gt_path) == bool(sample_list):
        raise ValueError("select exactly one of gt_path or sample_list")

    if sample_list:
        names = [line.strip() for line in sample_list.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        pages = json.loads(gt_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
        names = [Path(page["page_info"]["image_path"]).name for page in pages]

    if len(names) != len(set(names)):
        raise ValueError("speed sample inventory contains duplicate image names")
    if len(names) != expected_pages:
        raise ValueError(f"expected {expected_pages} speed pages, found {len(names)}")

    images = [image_dir / name for name in sorted(names)]
    missing = [path.name for path in images if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"speed images are missing ({len(missing)}): {missing[:10]}")
    invalid = [path.name for path in images if path.suffix.lower() not in IMAGE_EXTENSIONS]
    if invalid:
        raise ValueError(f"unsupported image extensions: {invalid[:10]}")
    return images


def encode_image(path: Path, mime: str = "image/png") -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class OpenAICompatibleClient:
    def __init__(self, base_url: str, timeout_seconds: float = 3600.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = build_opener(ProxyHandler({}))

    def _json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Authorization": "Bearer EMPTY", "Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"endpoint error: {exc.reason}") from exc
        if not isinstance(result, dict):
            raise RuntimeError("endpoint returned a non-object JSON payload")
        return result

    def verify_model(self, expected_model: str) -> None:
        result = self._json("GET", "/models")
        model_ids = [item.get("id") for item in result.get("data", []) if isinstance(item, dict)]
        if expected_model not in model_ids:
            raise RuntimeError(f"served model mismatch: expected {expected_model!r}, found {model_ids}")

    def infer(self, model: str, prompt: str, image_url: str, parameters: dict[str, Any]) -> dict[str, Any]:
        request_parameters = dict(parameters)
        extra_body = request_parameters.pop("extra_body", {})
        if not isinstance(extra_body, dict):
            raise ValueError("extra_body must be a JSON object")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            **request_parameters,
            **extra_body,
        }
        return self._json("POST", "/chat/completions", payload)


def summarize_speed(
    records: list[dict[str, Any]],
    wall_seconds: float,
    protocol_id: str,
    profile_id: str,
    sample_sha256: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    successful = [record for record in records if record.get("ok")]
    latencies = [float(record["latency_seconds"]) for record in successful]
    request_seconds = sum(latencies)
    token_total = sum(int(record.get("completion_tokens") or 0) for record in successful)
    failed = len(records) - len(successful)
    truncated = sum(record.get("finish_reason") == "length" for record in successful)
    missing_tokens = sum(record.get("completion_tokens") is None for record in successful)
    status = "PASS" if records and failed == 0 and truncated == 0 and missing_tokens == 0 else "FAIL"
    return {
        "status": status,
        "protocol_id": protocol_id,
        "profile_id": profile_id,
        "sample_inventory_sha256": sample_sha256,
        "images": len({record["image"] for record in records}),
        "requests": len(records),
        "successful": len(successful),
        "failed": failed,
        "truncated": truncated,
        "missing_completion_tokens": missing_tokens,
        "wall_seconds": round(wall_seconds, 6),
        "request_seconds_sum": round(request_seconds, 6),
        "average_latency_seconds": round(request_seconds / len(successful), 6) if successful else None,
        "page_per_second": round(len(successful) / request_seconds, 6) if request_seconds else None,
        "wall_page_per_second": round(len(successful) / wall_seconds, 6) if wall_seconds else None,
        "completion_tokens": token_total,
        "token_per_second": round(token_total / request_seconds, 4) if request_seconds else None,
        "latency_seconds": {
            "mean": round(request_seconds / len(successful), 6) if successful else None,
            "p50": percentile(latencies, 0.50),
            "p90": percentile(latencies, 0.90),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "min": min(latencies, default=None),
            "max": max(latencies, default=None),
        },
        "parameters": parameters,
    }


def run_speed(
    protocol: dict[str, Any],
    machine: dict[str, Any],
    profile_id: str,
    image_dir: Path,
    output_dir: Path,
    gt_path: Path | None = None,
    sample_list: Path | None = None,
) -> dict[str, Any]:
    profile = protocol["speed_profiles"][profile_id]
    images = select_images(image_dir, int(profile["expected_pages"]), gt_path, sample_list)
    image_names = [path.name for path in images]
    sample_sha256 = sha256_lines(image_names)
    expected_sample_sha256 = profile.get("sample_inventory_sha256")
    if expected_sample_sha256 and sample_sha256 != expected_sample_sha256:
        raise ValueError(
            f"speed inventory SHA-256 mismatch: expected {expected_sample_sha256}, found {sample_sha256}"
        )
    runtime = machine["runtime"]
    client = OpenAICompatibleClient(runtime["base_url"], float(profile["timeout_seconds"]))
    client.verify_model(runtime["served_model_name"])
    parameters = dict(profile["request"])
    prompt = protocol["prompt"]
    image_mime = profile.get("image_data_url_mime", "image/png")
    warmup = int(profile["warmup_pages"])
    repetitions = int(profile["repetitions"])

    output_dir.mkdir(parents=True, exist_ok=False)
    for path in images[:warmup]:
        client.infer(runtime["served_model_name"], prompt, encode_image(path, image_mime), parameters)

    records: list[dict[str, Any]] = []
    record_path = output_dir / "records.jsonl"
    wall_started = time.perf_counter()
    with record_path.open("w", encoding="utf-8") as record_file:
        for repetition in range(1, repetitions + 1):
            for path in images:
                image_url = encode_image(path, image_mime)
                started = time.perf_counter()
                record: dict[str, Any] = {"repetition": repetition, "image": path.name}
                try:
                    response = client.infer(
                        runtime["served_model_name"], prompt, image_url, parameters
                    )
                    choice = response["choices"][0]
                    text = choice.get("message", {}).get("content") or ""
                    usage = response.get("usage") or {}
                    record.update(
                        ok=True,
                        latency_seconds=round(time.perf_counter() - started, 6),
                        completion_tokens=usage.get("completion_tokens"),
                        output_chars=len(text),
                        finish_reason=choice.get("finish_reason"),
                    )
                except Exception as exc:
                    record.update(
                        ok=False,
                        latency_seconds=round(time.perf_counter() - started, 6),
                        error=f"{type(exc).__name__}: {exc}",
                    )
                records.append(record)
                record_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                record_file.flush()
                print(json.dumps(record, ensure_ascii=False), flush=True)
    wall_seconds = time.perf_counter() - wall_started
    summary_parameters = {
        **parameters,
        "base_url": runtime["base_url"],
        "model": runtime["served_model_name"],
        "concurrency": 1,
        "warmup_pages": warmup,
        "repetitions": repetitions,
        "image_data_url_mime": image_mime,
    }
    summary = summarize_speed(
        records,
        wall_seconds,
        protocol["protocol_id"],
        profile_id,
        sample_sha256,
        summary_parameters,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary
