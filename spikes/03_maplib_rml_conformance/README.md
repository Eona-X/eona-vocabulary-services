# Spike 3 — Maplib RML conformance runner

**Gates:** L3 ETL swap (ADR-004 §2).

## What this spike answers

ADR-004 requires "run the RML test suite. Output: pass-rate vs.
Morph-KGC." This spike runs the upstream
[`kg-construct/rml-test-cases`](https://github.com/kg-construct/rml-test-cases)
test suite — the test suite the Morph-KGC project itself uses — on both
engines and emits per-test verdicts.

## How it runs

`run.sh` does the following:

1. Fetches a pinned commit of `rml-test-cases` into
   `inputs/rml-test-cases/` (commit SHA recorded in the manifest, so a
   re-run with a different upstream snapshot is a different
   `inputs.files[].sha256` and therefore a different `run-id`).
2. For each test case (each has `mapping.ttl`, source data files, and an
   expected `output.nq` / `output.nt`):
   1. Runs Morph-KGC.
   2. Runs Maplib.
   3. Canonicalises each engine's output (sorted N-Quads after rdflib
      isomorphism normalisation).
   4. Diffs against the canonicalised expected output.
3. Writes:
   - `results/<run-id>/verdicts.json` — per-test `{engine, test, verdict,
     diff_path}` records.
   - `results/<run-id>/raw/<test-id>/{morph,maplib}.nq` — actual output.
   - `results/<run-id>/raw/<test-id>/{morph,maplib}.diff` — line diff
     against the expected canonical output (empty file ⇒ pass).
   - `results/<run-id>/summary.md` — pass-rate per engine, list of tests
     where the two engines diverge.

## Why save everything

A pass-rate number alone is not enough — the ADR reviewer needs to see
*which* tests Maplib fails to decide whether those failure modes affect
the hub. The per-test raw output and diff make that review possible
without re-running the spike.

## Re-running

```bash
./run.sh                # fetches the test suite once, then runs both engines
./run.sh --refresh-tests   # re-clone the test suite at the latest commit
```
