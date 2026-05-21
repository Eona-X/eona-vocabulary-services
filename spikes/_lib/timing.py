"""Latency sampler — used by spike 2 to record p50/p95/p99 for a query mix."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class LatencyTrace:
    label: str
    samples_ms: list[float] = field(default_factory=list)

    def add(self, ms: float) -> None:
        self.samples_ms.append(ms)

    def summary(self) -> dict:
        if not self.samples_ms:
            return {"n": 0}
        s = sorted(self.samples_ms)
        return {
            "n": len(s),
            "min_ms": s[0],
            "p50_ms": _pct(s, 50),
            "p95_ms": _pct(s, 95),
            "p99_ms": _pct(s, 99),
            "max_ms": s[-1],
            "mean_ms": statistics.fmean(s),
        }


def _pct(sorted_samples: list[float], p: float) -> float:
    if not sorted_samples:
        return 0.0
    k = max(0, min(len(sorted_samples) - 1, int(round((p / 100) * (len(sorted_samples) - 1)))))
    return sorted_samples[k]
