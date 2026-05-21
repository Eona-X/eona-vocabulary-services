"""Provenance helpers — every spike run uses these to write a manifest
alongside its raw outputs so the result directory is self-describing.

Manifest schema (v1):

    {
      "schema": "adr-004-spike-manifest/v1",
      "run_id": "20260521T143000Z-728771b-3f1a2c",
      "spike": "01_oxigraph_coverage",
      "started_at": "2026-05-21T14:30:00Z",
      "finished_at": "2026-05-21T14:31:02Z",
      "git": {"sha": "728771b...", "dirty": false, "branch": "impl/adr-004"},
      "host": {"hostname": "...", "os": "Linux 6.8.0", "cpu_count": 16, "mem_total_gb": 31.2},
      "python": "3.11.9",
      "tools": {"pyoxigraph": "0.4.7", "rdflib": "7.0.0", "maplib": "...", ...},
      "inputs": {"kind": "public-reference", "files": [{"path": "...", "sha256": "..."}]},
      "args": {...},                  # spike-specific CLI args
      "notes": "free text"
    }
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from importlib import metadata as _md
from pathlib import Path
from typing import Iterable

SCHEMA = "adr-004-spike-manifest/v1"


def _git(*args: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=Path(__file__).resolve().parents[2],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return ""


def _short(sha: str) -> str:
    return sha[:7] if sha else "nogit"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def inputs_digest(paths: Iterable[Path]) -> tuple[str, list[dict]]:
    """Return a stable short digest of the input set + per-file records."""
    files: list[dict] = []
    h = hashlib.sha256()
    for p in sorted(paths):
        if not p.exists():
            continue
        digest = sha256_file(p)
        files.append({"path": str(p), "sha256": digest, "size": p.stat().st_size})
        h.update(digest.encode())
    return h.hexdigest()[:6], files


def _tool_versions(names: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for n in names:
        try:
            out[n] = _md.version(n)
        except Exception:
            out[n] = "not-installed"
    return out


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id(inputs_hash: str) -> str:
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = _short(_git("rev-parse", "HEAD"))
    return f"{ts}-{sha}-{inputs_hash}"


def start_run(
    spike: str,
    spike_dir: Path,
    inputs: Iterable[Path],
    tools: Iterable[str],
    args: dict | None = None,
    inputs_kind: str = "public-reference",
    notes: str = "",
) -> tuple[Path, dict]:
    """Create results/<run-id>/ and write a partial manifest. Returns
    (run_dir, manifest_dict). Call `finish_run(manifest)` when done."""
    inputs_hash, files = inputs_digest(inputs)
    run_id = make_run_id(inputs_hash)
    run_dir = spike_dir / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": SCHEMA,
        "run_id": run_id,
        "spike": spike,
        "started_at": utc_now_iso(),
        "finished_at": None,
        "git": {
            "sha": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "host": {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_count": os.cpu_count(),
            "mem_total_gb": round(_mem_total_gb(), 2),
        },
        "python": sys.version.split()[0],
        "tools": _tool_versions(tools),
        "inputs": {"kind": inputs_kind, "files": files},
        "args": args or {},
        "notes": notes,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return run_dir, manifest


def finish_run(run_dir: Path, manifest: dict, extra: dict | None = None) -> None:
    manifest["finished_at"] = utc_now_iso()
    if extra:
        manifest.update(extra)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _mem_total_gb() -> float:
    try:
        import psutil

        return psutil.virtual_memory().total / 1024**3
    except Exception:
        return 0.0
