"""RML conformance runner for Maplib and Morph-KGC.

Each test in the rml-test-cases suite is a directory containing:
  - mapping.ttl     RML mapping
  - source files    CSV / JSON / XML referenced from the mapping
  - output.nq       expected output (or `expected_invalid` to assert error)

For every test, both engines are invoked, output is canonicalised via
rdflib graph isomorphism, and the diff against expected is saved.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib.provenance import finish_run, start_run

SPIKE = "03_maplib_rml_conformance"
SPIKE_DIR = Path(__file__).resolve().parent
TESTS_DIR = SPIKE_DIR / "inputs" / "rml-test-cases" / "test-cases"


@dataclass
class Verdict:
    test_id: str
    engine: str
    verdict: str  # pass | fail | error | skipped
    detail: str
    raw_path: str | None = None
    diff_path: str | None = None


def discover_tests() -> list[Path]:
    if not TESTS_DIR.exists():
        return []
    return sorted(p for p in TESTS_DIR.iterdir() if p.is_dir() and (p / "mapping.ttl").exists())


def run_morph(test_dir: Path, out_file: Path) -> tuple[bool, str]:
    """Morph-KGC reads a config.ini that points at the mapping + output."""
    cfg = (
        f"[CONFIGURATION]\noutput_file={out_file}\n"
        f"[Dataset1]\nmappings={test_dir / 'mapping.ttl'}\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False) as f:
        f.write(cfg)
        cfg_path = f.name
    try:
        proc = subprocess.run(
            ["uv", "run", "--isolated", "--with", "morph-kgc",
             "python", "-m", "morph_kgc", cfg_path],
            cwd=test_dir, capture_output=True, text=True, timeout=300,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)
    except Exception as e:
        return False, f"exception: {e}\n{traceback.format_exc()}"


def run_maplib(test_dir: Path, out_file: Path) -> tuple[bool, str]:
    try:
        from maplib import Mapping  # type: ignore
        m = Mapping()
        m.read_template(str(test_dir / "mapping.ttl"))
        m.expand_default()
        m.write_ntriples(str(out_file))
        return True, ""
    except Exception as e:
        return False, f"{e}\n{traceback.format_exc()}"


def canonicalise(path: Path) -> str:
    """Sorted serialised form for cheap diffing. Returns "" if unreadable."""
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(str(path))
        return "\n".join(sorted(g.serialize(format="nt").splitlines()))
    except Exception:
        return ""


def diff_against_expected(actual_path: Path, expected_path: Path, diff_path: Path) -> bool:
    a = canonicalise(actual_path)
    e = canonicalise(expected_path)
    if a == e and a:
        diff_path.write_text("")
        return True
    diff_path.write_text(
        f"--- expected\n+++ actual\n"
        f"-- expected ({len(e.splitlines())} lines) --\n{e}\n"
        f"-- actual ({len(a.splitlines())} lines) --\n{a}\n"
    )
    return False


def run_one(test_dir: Path, run_dir: Path) -> list[Verdict]:
    test_id = test_dir.name
    raw_dir = run_dir / "raw" / test_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    expected = test_dir / "output.nq"
    if not expected.exists():
        expected = test_dir / "output.nt"

    verdicts: list[Verdict] = []
    for engine, runner in (("morph", run_morph), ("maplib", run_maplib)):
        out_file = raw_dir / f"{engine}.nt"
        ok, log = runner(test_dir, out_file)
        (raw_dir / f"{engine}.log").write_text(log)
        if not ok:
            verdicts.append(Verdict(test_id, engine, "error", log[:500].strip(),
                                    raw_path=str(out_file)))
            continue
        if not expected.exists():
            verdicts.append(Verdict(test_id, engine, "skipped",
                                    "no expected output present",
                                    raw_path=str(out_file)))
            continue
        diff_path = raw_dir / f"{engine}.diff"
        passed = diff_against_expected(out_file, expected, diff_path)
        verdicts.append(Verdict(
            test_id, engine, "pass" if passed else "fail",
            "ok" if passed else "graphs differ",
            raw_path=str(out_file), diff_path=str(diff_path),
        ))
    return verdicts


def main() -> int:
    tests = discover_tests()
    if not tests:
        print(f"no tests found under {TESTS_DIR}; run run.sh to fetch the suite",
              file=sys.stderr)
        return 2

    run_dir, manifest = start_run(
        spike=SPIKE, spike_dir=SPIKE_DIR,
        inputs=[*TESTS_DIR.rglob("mapping.ttl")],
        tools=["maplib", "morph-kgc", "rdflib"],
        args={"n_tests": len(tests)},
        inputs_kind="public-reference",
        notes="rml-test-cases pinned via run.sh; see manifest input hashes for commit.",
    )

    all_verdicts: list[Verdict] = []
    for t in tests:
        all_verdicts.extend(run_one(t, run_dir))

    (run_dir / "verdicts.json").write_text(
        json.dumps([asdict(v) for v in all_verdicts], indent=2)
    )
    write_summary(run_dir, all_verdicts)
    finish_run(run_dir, manifest, {"tests": len(tests)})
    print(f"results: {run_dir}")
    return 0


def write_summary(run_dir: Path, verdicts: list[Verdict]) -> None:
    counts: dict[str, dict[str, int]] = {"morph": {}, "maplib": {}}
    for v in verdicts:
        counts[v.engine][v.verdict] = counts[v.engine].get(v.verdict, 0) + 1
    total = {e: sum(c.values()) for e, c in counts.items()}
    pass_rate = {e: counts[e].get("pass", 0) / total[e] if total[e] else 0.0
                 for e in counts}

    divergent = []
    by_test: dict[str, dict[str, str]] = {}
    for v in verdicts:
        by_test.setdefault(v.test_id, {})[v.engine] = v.verdict
    for t, by_engine in by_test.items():
        if by_engine.get("morph") != by_engine.get("maplib"):
            divergent.append((t, by_engine.get("morph", "?"), by_engine.get("maplib", "?")))

    lines = [
        f"# Spike 3 summary — {run_dir.name}",
        "",
        "| engine | pass | fail | error | skipped | total | pass-rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for e in ("morph", "maplib"):
        c = counts[e]
        lines.append(
            f"| {e} | {c.get('pass',0)} | {c.get('fail',0)} | {c.get('error',0)} | "
            f"{c.get('skipped',0)} | {total[e]} | {pass_rate[e]:.1%} |"
        )
    lines += ["", "## Divergent tests (Maplib verdict ≠ Morph verdict)", ""]
    if not divergent:
        lines.append("_none_")
    else:
        lines.append("| test | morph | maplib |")
        lines.append("|---|---|---|")
        for t, m, ml in sorted(divergent):
            lines.append(f"| {t} | {m} | {ml} |")
    (run_dir / "summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
