#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and verify an immutable Hugging Face snapshot.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--repo-type", choices=("model", "dataset"), required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--endpoint", default=os.environ.get("HF_ENDPOINT", "https://huggingface.co"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--expected-files", type=int, required=True)
    parser.add_argument("--expected-images", type=int, required=True)
    parser.add_argument("--exclude-prefix", action="append", default=[])
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:
        digest = hashlib.sha1()
    digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_manifest(args: argparse.Namespace) -> dict:
    kind = "datasets" if args.repo_type == "dataset" else "models"
    url = (
        f"{args.endpoint.rstrip('/')}/api/{kind}/{quote(args.repo, safe='/')}"
        f"/revision/{quote(args.revision, safe='')}?blobs=true"
    )
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "hunyuanocr-bench/1"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def local_path(destination: Path, filename: str) -> Path:
    relative = PurePosixPath(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe repository path: {filename}")
    path = destination.joinpath(*relative.parts)
    path.resolve().relative_to(destination.resolve())
    return path


def validate(path: Path, sibling: dict) -> None:
    if not path.is_file():
        raise RuntimeError(f"missing file: {path}")
    expected_size = sibling.get("size")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise RuntimeError(f"size mismatch: {path}")
    expected_sha = (sibling.get("lfs") or {}).get("sha256")
    if expected_sha and sha256_file(path) != expected_sha:
        raise RuntimeError(f"SHA-256 mismatch: {path}")
    expected_blob = sibling.get("blobId") if not sibling.get("lfs") else None
    if expected_blob and git_blob_sha1(path) != expected_blob:
        raise RuntimeError(f"Git blob SHA-1 mismatch: {path}")


def download_one(args: argparse.Namespace, sibling: dict) -> tuple[int, bool]:
    filename = sibling["rfilename"]
    destination = local_path(args.destination, filename)
    expected_size = sibling.get("size")
    cached = destination.is_file() and (
        expected_size is None or destination.stat().st_size == expected_size
    )
    if cached:
        try:
            validate(destination, sibling)
            return int(expected_size or destination.stat().st_size), True
        except RuntimeError:
            destination.unlink()
            cached = False
    if not cached:
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(f".{destination.name}.part")
        prefix = "datasets/" if args.repo_type == "dataset" else ""
        url = (
            f"{args.endpoint.rstrip('/')}/{prefix}{quote(args.repo, safe='/')}"
            f"/resolve/{quote(args.revision, safe='')}/{quote(filename, safe='/')}?download=true"
        )
        subprocess.run(
            [
                "curl", "--noproxy", "*", "-L", "--fail", "--retry", "8",
                "--retry-all-errors", "--retry-delay", "2", "--connect-timeout", "15",
                "--max-time", "0", "--continue-at", "-", "--silent", "--show-error",
                "--output", str(partial), url,
            ],
            check=True,
        )
        os.replace(partial, destination)
    validate(destination, sibling)
    return int(expected_size or destination.stat().st_size), cached


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    manifest = fetch_manifest(args)
    if manifest.get("sha") != args.revision:
        raise RuntimeError(f"revision mismatch: {manifest.get('sha')}")
    siblings = [
        item
        for item in (manifest.get("siblings") or [])
        if not any(item.get("rfilename", "").startswith(prefix) for prefix in args.exclude_prefix)
    ]
    filenames = [item.get("rfilename") for item in siblings]
    if len(siblings) != args.expected_files:
        raise RuntimeError(f"expected {args.expected_files} files, found {len(siblings)}")
    image_count = sum(str(name).startswith("images/") for name in filenames)
    if image_count != args.expected_images:
        raise RuntimeError(f"expected {args.expected_images} images, found {image_count}")
    if any(not name for name in filenames) or len(filenames) != len(set(filenames)):
        raise RuntimeError("snapshot manifest has missing or duplicate names")

    args.destination.mkdir(parents=True, exist_ok=True)
    completed = cached_count = verified_bytes = 0
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_one, args, item): item for item in siblings}
        for future in as_completed(futures):
            item = futures[future]
            try:
                size, cached = future.result()
                completed += 1
                cached_count += int(cached)
                verified_bytes += size
                if completed % 50 == 0 or completed == len(siblings):
                    print(
                        f"[snapshot] {completed}/{len(siblings)} cached={cached_count} "
                        f"verified_bytes={verified_bytes}",
                        flush=True,
                    )
            except Exception as exc:
                failures.append(f"{item.get('rfilename')}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError("snapshot failures:\n" + "\n".join(failures[:20]))

    audit = {
        "repository": args.repo,
        "repository_type": args.repo_type,
        "revision": args.revision,
        "endpoint": args.endpoint,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(siblings),
        "image_count": image_count,
        "total_bytes": sum(item.get("size") or 0 for item in siblings),
        "excluded_prefixes": args.exclude_prefix,
        "files": [
            {
                "path": item["rfilename"],
                "size": item.get("size"),
                "sha256": (item.get("lfs") or {}).get("sha256"),
                "git_blob_sha1": item.get("blobId") if not item.get("lfs") else None,
            }
            for item in siblings
        ],
    }
    (args.destination / ".download-manifest.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.destination / ".snapshot-revision").write_text(args.revision + "\n", encoding="utf-8")
    print(f"PASS: {args.repo}@{args.revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
