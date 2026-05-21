"""Lightweight RSS sampler — polls a process and records peak / timeseries.

Used by spikes 2 and 4 to capture the memory profile of the engine under
test while a workload runs.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import psutil


@dataclass
class RssSample:
    t: float
    rss_mb: float


@dataclass
class RssTrace:
    label: str
    interval_s: float
    samples: list[RssSample] = field(default_factory=list)

    @property
    def peak_mb(self) -> float:
        return max((s.rss_mb for s in self.samples), default=0.0)

    def write_csv(self, path: Path) -> None:
        with path.open("w") as f:
            f.write("t_seconds,rss_mb\n")
            for s in self.samples:
                f.write(f"{s.t:.3f},{s.rss_mb:.2f}\n")


class RssSampler:
    """Background sampler. Use as a context manager around the workload."""

    def __init__(self, pid: int, label: str, interval_s: float = 0.25):
        self.proc = psutil.Process(pid)
        self.trace = RssTrace(label=label, interval_s=interval_s)
        self._stop = threading.Event()
        self._t0 = 0.0
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                rss_mb = self._collect_rss_mb()
                self.trace.samples.append(RssSample(time.time() - self._t0, rss_mb))
            except psutil.NoSuchProcess:
                break
            self._stop.wait(self.trace.interval_s)

    def _collect_rss_mb(self) -> float:
        total = self.proc.memory_info().rss
        try:
            for child in self.proc.children(recursive=True):
                total += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
        return total / 1024**2

    def __enter__(self) -> "RssSampler":
        self._t0 = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
