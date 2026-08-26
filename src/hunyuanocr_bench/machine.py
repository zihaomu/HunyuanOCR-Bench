from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


def _capture(command: list[str]) -> dict[str, Any]:
    if not shutil.which(command[0]):
        return {"available": False, "command": command}
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"available": True, "command": command, "timed_out": True, "timeout_seconds": 30}
    stdout = completed.stdout
    stderr = completed.stderr
    return {
        "available": True,
        "command": command,
        "returncode": completed.returncode,
        "stdout": stdout[:65536].strip(),
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "stdout_truncated": len(stdout) > 65536,
        "stderr": stderr[:16384].strip(),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        "stderr_truncated": len(stderr) > 16384,
    }


def capture_machine(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "declared_profile": profile,
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "commands": {
            "nvidia_smi": _capture(
                [
                    "nvidia-smi",
                    "--query-gpu=name,uuid,memory.total,driver_version,vbios_version",
                    "--format=csv,noheader",
                ]
            ),
            "rocm_smi": _capture(["rocm-smi", "--showproductname", "--showuniqueid", "--showmeminfo", "vram"]),
            "rocminfo": _capture(["rocminfo"]),
            "docker": _capture(["docker", "version", "--format", "{{json .}}"]),
            "git": _capture(["git", "version"]),
        },
    }
