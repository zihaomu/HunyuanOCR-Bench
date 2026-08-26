from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = REPOSITORY_ROOT / "protocol" / "benchmark-v1.json"
MACHINE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = load_json(path)
    if protocol.get("protocol_id") != "hunyuanocr-1.5-omnidocbench-1.6-v1":
        raise ValueError(f"unsupported protocol_id in {path}")
    evaluator = protocol["evaluator"]
    config_path = REPOSITORY_ROOT / evaluator["config"]
    if sha256_file(config_path) != evaluator["config_sha256"]:
        raise ValueError(f"evaluator config SHA-256 mismatch: {config_path}")
    for profile_id, profile in protocol["speed_profiles"].items():
        sample_list = profile.get("sample_list")
        expected_sha = profile.get("sample_inventory_sha256")
        if not sample_list or not expected_sha:
            continue
        sample_path = REPOSITORY_ROOT / sample_list
        names = [line for line in sample_path.read_text(encoding="utf-8").splitlines() if line]
        if len(names) != profile["expected_pages"]:
            raise ValueError(f"{profile_id} page count mismatch: {sample_path}")
        if len(names) != len(set(names)) or names != sorted(names):
            raise ValueError(f"{profile_id} inventory must be unique and sorted")
        if sha256_lines(names) != expected_sha:
            raise ValueError(f"{profile_id} inventory SHA-256 mismatch: {sample_path}")
    return protocol


def load_machine(path: Path) -> dict[str, Any]:
    machine = load_json(path)
    required = ("machine_id", "vendor", "accelerator", "runtime")
    missing = [key for key in required if not machine.get(key)]
    if missing:
        raise ValueError(f"machine profile is missing: {', '.join(missing)}")
    if machine["vendor"] not in {"amd", "nvidia"}:
        raise ValueError("machine vendor must be 'amd' or 'nvidia'")
    machine_id = machine["machine_id"]
    if not MACHINE_ID_PATTERN.fullmatch(machine_id):
        raise ValueError("machine_id must be lowercase kebab-case")
    if not machine_id.startswith(f"{machine['vendor']}-"):
        raise ValueError("machine_id must start with the declared vendor")

    serialized = json.dumps(machine, ensure_ascii=False)
    if "REPLACE_ME" in serialized:
        raise ValueError(f"machine profile still contains REPLACE_ME: {path}")

    accelerator = machine["accelerator"]
    if not accelerator.get("model"):
        raise ValueError("machine accelerator model is required")
    if not isinstance(accelerator.get("count"), int) or accelerator["count"] < 1:
        raise ValueError("machine accelerator count must be a positive integer")
    memory = accelerator.get("memory_gib_each")
    if not isinstance(memory, (int, float)) or isinstance(memory, bool) or memory <= 0:
        raise ValueError("machine accelerator memory_gib_each must be positive")

    runtime = machine["runtime"]
    for key in (
        "framework",
        "framework_version",
        "inference_method",
        "base_url",
        "served_model_name",
        "container_image",
        "container_image_digest",
        "precision",
        "tensor_parallel",
    ):
        if not runtime.get(key):
            raise ValueError(f"machine runtime is missing {key}")
    if runtime["inference_method"] not in {"ar", "dflash"}:
        raise ValueError("runtime inference_method must be 'ar' or 'dflash'")
    if runtime["served_model_name"] != "tencent/HunyuanOCR":
        raise ValueError("served_model_name must be tencent/HunyuanOCR")
    if not isinstance(runtime["tensor_parallel"], int) or runtime["tensor_parallel"] < 1:
        raise ValueError("runtime tensor_parallel must be a positive integer")
    if runtime["inference_method"] == "dflash":
        draft = runtime.get("draft_model") or {}
        if not draft.get("repository") or not draft.get("revision"):
            raise ValueError("DFlash profiles must declare draft_model repository and revision")

    software = machine.get("software") or {}
    for key in ("os", "driver", "compute_stack", "pytorch"):
        if not software.get(key):
            raise ValueError(f"machine software is missing {key}")
    return machine


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_lines(lines: list[str]) -> str:
    payload = "".join(f"{line}\n" for line in lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def dotted_get(source: dict[str, Any], dotted_key: str) -> Any:
    value: Any = source
    for key in dotted_key.split("."):
        if not isinstance(value, dict) or key not in value:
            raise KeyError(dotted_key)
        value = value[key]
    return value


def accuracy_endpoint_config(machine: dict[str, Any]) -> tuple[str, list[int]]:
    runtime = machine["runtime"]
    parsed = urlparse(runtime["base_url"])
    if parsed.scheme != "http" or not parsed.hostname or not parsed.port or parsed.path.rstrip("/") != "/v1":
        raise ValueError("accuracy inference requires an http://HOST:PORT/v1 base_url")
    ports = runtime.get("accuracy_ports") or [parsed.port]
    if not isinstance(ports, list) or not ports:
        raise ValueError("runtime.accuracy_ports must be a non-empty list")
    if any(isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535 for port in ports):
        raise ValueError("runtime.accuracy_ports must contain valid integer ports")
    if len(ports) != len(set(ports)):
        raise ValueError("runtime.accuracy_ports must be unique")
    return parsed.hostname, ports
