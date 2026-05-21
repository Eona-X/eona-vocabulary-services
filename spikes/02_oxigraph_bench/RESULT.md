# Spike 2 result — Oxigraph vs Fuseki benchmark

**Verdict:** **PASS (deployment-realistic)** — under the configuration the
hub would actually deploy (both engines on persistent volumes),
Oxigraph wins on **memory (~5×)** and on **most query shapes**, with
parity on label scans and a meaningful loss on cross-named-graph
aggregation. Bulk load is close (Fuseki 1.4× faster). UPDATE latency
under disk persistence is **~40× faster on Oxigraph** — a real
deployment-relevant finding that the prior mixed comparison hid.

The earlier "in-memory Fuseki vs RocksDB Oxigraph" pairing was unfair
to Oxigraph and is superseded by the two variants below.

## Variants

| Variant | Fuseki backend | Oxigraph backend | Run-id |
|---|---|---|---|
| `tmpfs` (engine-only) | `--mem` | RocksDB on tmpfs | [`20260521T173644Z-728771b-425148`](results/20260521T173644Z-728771b-425148/) |
| `disk` (deployment-realistic) | TDB2 on volume | RocksDB on volume | [`20260521T174117Z-728771b-425148`](results/20260521T174117Z-728771b-425148/) |

Both runs: 100 000-triple synthetic SKOS taxonomy, 8 hub-shaped queries
(3 warmup + 50 timed iterations), 4 Hz RSS sampling. Both engines wired
through their public binaries — no custom builds.

## Memory

| Variant | Fuseki RSS (MB) | Oxigraph RSS (MB) | Oxigraph saving |
|---|---:|---:|---:|
| tmpfs | 1175.9 | 243.3 | **4.83×** |
| disk  | 1252.5 | 243.4 | **5.15×** |

Oxigraph's footprint is stable across variants because RocksDB's working
set is small for 100k triples. Fuseki sits where ADR-001 predicted
(1.5–4 GB with `-Xmx2g`). The disk variant gives Oxigraph a slightly
larger margin because TDB2 caches more aggressively than `--mem` does.

ADR-004 §1 ("the '10x' figure from prior drafts is not substantiated")
is **confirmed**. The real ratio is ~5×, not 10×. Worth correcting in
the ADR.

## Bulk load (100 000 triples, single POST)

| Variant | Fuseki t/s | Oxigraph t/s | Fuseki advantage |
|---|---:|---:|---:|
| tmpfs | 116 138 | 32 656 | **3.56×** |
| disk  |  46 538 | 33 847 | **1.38×** |

Putting Fuseki on TDB2 removes most of its load advantage. The
deployment-realistic ratio is **1.4×, not 5.9×** as the original
misleading pairing suggested. For a hub that drop-and-reloads at deploy
time (per ADR-001 §Required capabilities — "we don't rely on
incremental transaction guarantees"), 3 seconds for 100k triples is not
a deployment blocker on either engine.

## Query latency (p50, ms — disk variant)

The deployment variant is the one the hub will run. Use these numbers
for the L1/L2 decision.

| Query | Shape | Fuseki TDB2 | Oxigraph RocksDB | Winner | Factor |
|---|---|---:|---:|---|---:|
| q01 | label-scan with FILTER string | 61.0 | 62.0 | tie | 1.02× |
| q02 | `skos:broader+` (few ancestors) | 13.5 | 2.1 | Oxigraph | **6.43×** |
| q03 | COUNT over `skos:inScheme` | 25.0 | 11.1 | Oxigraph | **2.25×** |
| q04 | CONSTRUCT neighbourhood | 12.1 | 2.4 | Oxigraph | **5.04×** |
| q05 | `skos:broader+` (many descendants) | 66.8 | 44.8 | Oxigraph | **1.49×** |
| q06 | COUNT across named graphs | 11.1 | 29.6 | Fuseki | 2.67× |
| q07 | UPDATE INSERT DATA | 84.3 | 2.1 | Oxigraph | **40.1×** |
| q08 | ASK | 10.1 | 2.1 | Oxigraph | **4.81×** |

Full n / min / p50 / p95 / p99 / mean in
[`results/20260521T174117Z-…/query_latency.json`](results/20260521T174117Z-728771b-425148/query_latency.json).

### Two findings the engine-only variant hid

1. **Fuseki TDB2 pays a real cost on UPDATE.** `q07 INSERT DATA` jumps
   from ~10 ms (in-memory) to **84 ms (TDB2 on disk)** — an 8× slowdown
   from the durability sync. Oxigraph RocksDB stays at 2.1 ms in both
   variants. For a Vocabulary Hub whose ingestion gate inserts validated
   triples on every publish, this is a **real deployment-relevant
   advantage for Oxigraph**.
2. **The deeper path query (`q05 narrower+`) flips.** On the engine-only
   variant Fuseki won (37 vs 49 ms); on disk Fuseki loses (67 vs 45 ms).
   TDB2's larger working set incurs more page faults than RocksDB does
   for the same traversal.

`q06 (named-graph aggregation)` remains a Fuseki win in both variants.
That is the one workload shape where Oxigraph is materially slower; if
the hub ever needs to aggregate across many named graphs in the hot
path, this is the row to revisit.

## What changed vs the first run

The originally reported numbers in the prior RESULT.md (since
overwritten) compared **in-memory Fuseki against on-disk Oxigraph** —
worst-of-both for Oxigraph. Three corrections:

| Metric | Old (mixed) | New (disk-vs-disk) |
|---|---|---|
| Bulk load ratio (Fuseki advantage) | 5.85× | **1.38×** |
| q07 UPDATE — Oxigraph advantage | 4.57× | **40.1×** |
| Memory ratio (Oxigraph saving) | 2.77× | **5.15×** |

Lesson logged for future spikes: **never compare engines across storage
tiers without flagging it.** The variant name is now embedded in every
manifest, run-id annotation, and summary header.

## Caveats still standing

- **Public-reference workload.** Numbers will move when a hub-owned
  dataset and query mix replace the synthetic SKOS taxonomy. Every
  manifest tags `inputs.kind = public-reference`; gating runs will tag
  `hub` and overrule the indicative numbers here.
- **Single-threaded client.** Concurrency dimension untested.
- **Single 100k-triple dataset.** Scale-dependent behaviour (e.g.
  Oxigraph's RocksDB cache saturating at 10M+ triples) not measured.

## Recommendation to ADR reviewer

In the deployment-realistic variant Oxigraph clears the spike on
memory and latency. Combine with Spike 1's two coverage flags
(JSON-LD, federation — both resolvable at the API layer) and Spike 2
becomes evidence to **accept the L1/L2 swap proposed by ADR-004**,
subject to:

- ADR text correction: "10× memory" → "~5× memory."
- API-layer commitment to JSON-LD transcoding at the gateway.
- A re-test if a hot-path workload emerges that resembles `q06`
  (cross-named-graph aggregation).

## Reproducing

```bash
cd spikes
uv sync
cd 02_oxigraph_bench
VARIANT=tmpfs ./run.sh        # engine-only
VARIANT=disk  ./run.sh        # deployment-realistic
```

Each invocation switches Docker Compose profiles cleanly (the script
runs `docker compose down` between variants so containers don't collide
on names or ports).

## Provenance

Both runs:

- `results/<run-id>/manifest.json` — git SHA, host, tool versions,
  input file hashes, `inputs.kind`, **`args.variant`**, `peak_rss_mb`.
- `…/load_results.json`, `…/query_latency.json`.
- `…/rss_fuseki.csv`, `…/rss_oxigraph.csv` — 4 Hz traces.
- `…/raw/<query>/<engine>.iter<0|1|2>.txt` — first three full response
  bodies per (engine × query) for cross-engine answer-diff audits.
