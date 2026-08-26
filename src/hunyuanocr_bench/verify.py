from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .config import sha256_file


def _git_blob_sha1(path: Path) -> str:
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:
        digest = hashlib.sha1()
    digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_snapshot(
    root: Path,
    expected_repository: str,
    expected_revision: str,
    expected_files: int,
    expected_images: int,
    errors: list[str],
) -> dict[str, Any]:
    manifest_path = root / ".download-manifest.json"
    if not manifest_path.is_file():
        errors.append(f"snapshot manifest is missing: {root}")
        return {"verified_files": 0, "verified_bytes": 0}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, expected in (
        ("repository", expected_repository),
        ("revision", expected_revision),
        ("file_count", expected_files),
        ("image_count", expected_images),
    ):
        if manifest.get(key) != expected:
            errors.append(f"snapshot manifest {key} mismatch: {root}")
    records = manifest.get("files") or []
    if len(records) != expected_files:
        errors.append(f"snapshot file record count mismatch: {root}")

    verified_files = verified_bytes = 0
    for record in records:
        relative = Path(record.get("path", ""))
        if not record.get("path") or relative.is_absolute() or ".." in relative.parts:
            errors.append(f"unsafe snapshot path in {root}: {record.get('path')}")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"snapshot file is missing: {path}")
            continue
        size = path.stat().st_size
        if record.get("size") is not None and size != record["size"]:
            errors.append(f"snapshot file size mismatch: {path}")
            continue
        expected_sha = record.get("sha256")
        if expected_sha and sha256_file(path) != expected_sha:
            errors.append(f"snapshot file SHA-256 mismatch: {path}")
            continue
        expected_blob = record.get("git_blob_sha1")
        if expected_blob and _git_blob_sha1(path) != expected_blob:
            errors.append(f"snapshot file Git blob SHA-1 mismatch: {path}")
            continue
        verified_files += 1
        verified_bytes += size
    return {"verified_files": verified_files, "verified_bytes": verified_bytes}


def _source_dirty(path: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(completed.stdout.strip())


def _git_head(path: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def verify_assets(assets_dir: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    model = protocol["model"]
    dataset = protocol["dataset"]
    evaluator = protocol["evaluator"]
    hunyuan_source = assets_dir / "src" / "HunyuanOCR"
    evaluator_source = assets_dir / "src" / "OmniDocBench"
    model_dir = assets_dir / "models" / "HunyuanOCR"
    data_dir = assets_dir / "data" / "OmniDocBench_v1_6"
    gt_path = data_dir / dataset["gt_file"]
    image_dir = data_dir / "images"

    source_revisions = {
        "hunyuanocr": _git_head(hunyuan_source),
        "omnidocbench": _git_head(evaluator_source),
    }
    if source_revisions["hunyuanocr"] != model["code_revision"]:
        errors.append("HunyuanOCR source revision mismatch")
    if source_revisions["omnidocbench"] != evaluator["revision"]:
        errors.append("OmniDocBench source revision mismatch")
    source_dirty = {
        "hunyuanocr": _source_dirty(hunyuan_source),
        "omnidocbench": _source_dirty(evaluator_source),
    }
    if any(source_dirty.values()):
        errors.append(f"source checkout is dirty: {source_dirty}")

    model_marker = model_dir / ".snapshot-revision"
    if not model_marker.is_file() or model_marker.read_text().strip() != model["weights_revision"]:
        errors.append("HunyuanOCR model revision marker mismatch")
    if not (model_dir / "config.json").is_file():
        errors.append("HunyuanOCR model config.json is missing")
    weight_files = sorted(model_dir.glob("*.safetensors"))
    if not weight_files:
        errors.append("HunyuanOCR model weights are missing")

    model_snapshot = _verify_snapshot(
        model_dir,
        model["weights_repository"],
        model["weights_revision"],
        22,
        0,
        errors,
    )
    data_snapshot = _verify_snapshot(
        data_dir,
        dataset["repository"],
        dataset["revision"],
        dataset["expected_files"],
        dataset["expected_images"],
        errors,
    )

    pages: list[dict[str, Any]] = []
    if not gt_path.is_file():
        errors.append("OmniDocBench ground truth is missing")
        gt_sha256 = None
        gt_bytes = None
    else:
        gt_sha256 = sha256_file(gt_path)
        gt_bytes = gt_path.stat().st_size
        if gt_sha256 != dataset["gt_sha256"]:
            errors.append("OmniDocBench ground-truth SHA-256 mismatch")
        if gt_bytes != dataset["gt_bytes"]:
            errors.append("OmniDocBench ground-truth byte count mismatch")
        try:
            pages = json.loads(gt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"OmniDocBench ground truth is invalid: {exc}")

    expected_names = [Path(page["page_info"]["image_path"]).name for page in pages]
    if len(pages) != dataset["expected_images"]:
        errors.append(f"expected {dataset['expected_images']} GT pages, found {len(pages)}")
    if len(expected_names) != len(set(expected_names)):
        errors.append("ground truth contains duplicate image names")
    actual_names = sorted(path.name for path in image_dir.iterdir() if path.is_file()) if image_dir.is_dir() else []
    if set(actual_names) != set(expected_names):
        errors.append(
            f"image inventory mismatch: missing={len(set(expected_names) - set(actual_names))} "
            f"extra={len(set(actual_names) - set(expected_names))}"
        )

    subsets = Counter(
        page.get("page_info", {}).get("page_attribute", {}).get("subset") for page in pages
    )
    expected_subsets = dataset["coverage"]["subsets"]
    if dict(subsets) != expected_subsets:
        errors.append(f"dataset subset distribution mismatch: {dict(subsets)}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "source_revisions": source_revisions,
        "source_dirty": source_dirty,
        "model": {
            "revision": model["weights_revision"],
            "weight_files": len(weight_files),
            "weight_bytes": sum(path.stat().st_size for path in weight_files),
            "snapshot": model_snapshot,
        },
        "dataset": {
            "revision": dataset["revision"],
            "gt_sha256": gt_sha256,
            "gt_bytes": gt_bytes,
            "pages": len(pages),
            "images": len(actual_names),
            "subsets": dict(subsets),
            "snapshot": data_snapshot,
        },
        "errors": errors,
    }


def verify_predictions(gt_path: Path, prediction_dir: Path) -> dict[str, Any]:
    pages = json.loads(gt_path.read_text(encoding="utf-8"))
    image_names = [Path(page["page_info"]["image_path"]).name for page in pages]
    expected = {f"{Path(name).stem}.md" for name in image_names}
    errors: list[str] = []
    if len(expected) != len(image_names):
        errors.append("image stems collide and cannot map one-to-one to Markdown")
    actual_paths = {path.name: path for path in prediction_dir.glob("*.md") if path.is_file()}
    missing = sorted(expected - set(actual_paths))
    extra = sorted(set(actual_paths) - expected)
    if missing:
        errors.append(f"missing Markdown predictions: {len(missing)}")
    if extra:
        errors.append(f"unexpected Markdown predictions: {len(extra)}")

    records_path = prediction_dir / "results.jsonl"
    latest: dict[str, dict[str, Any]] = {}
    record_count = 0
    malformed: list[int] = []
    if not records_path.is_file():
        errors.append("results.jsonl is missing")
    else:
        for line_number, line in enumerate(records_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed.append(line_number)
                continue
            if record.get("image"):
                latest[record["image"]] = record
        if malformed:
            errors.append(f"malformed results.jsonl lines: {malformed[:10]}")

    missing_records = sorted(set(image_names) - set(latest))
    failed_records = sorted(name for name, record in latest.items() if not record.get("ok"))
    if missing_records:
        errors.append(f"missing latest inference records: {len(missing_records)}")
    if failed_records:
        errors.append(f"failed latest inference records: {len(failed_records)}")

    empty = sorted(name for name, path in actual_paths.items() if path.stat().st_size == 0)
    whitespace = sorted(
        name
        for name, path in actual_paths.items()
        if path.stat().st_size > 0 and not path.read_text(encoding="utf-8").strip()
    )
    return {
        "status": "PASS" if not errors else "FAIL",
        "gt_pages": len(pages),
        "markdown_files": len(actual_paths),
        "result_records_total": record_count,
        "latest_records": len(latest),
        "missing_markdown_count": len(missing),
        "extra_markdown_count": len(extra),
        "missing_record_count": len(missing_records),
        "failed_record_count": len(failed_records),
        "zero_byte_count": len(empty),
        "whitespace_only_count": len(whitespace),
        "samples": {
            "missing_markdown": missing[:20],
            "extra_markdown": extra[:20],
            "missing_records": missing_records[:20],
            "failed_records": failed_records[:20],
            "zero_byte": empty[:20],
            "whitespace_only": whitespace[:20],
        },
        "errors": errors,
    }
