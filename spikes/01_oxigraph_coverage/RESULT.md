# Spike 1 result — Oxigraph coverage

**Verdict:** **FAIL** (conditional — two real gaps found, both decidable
by ADR-004 reviewer with the evidence below).

- Run-id: [`20260521T150143Z-728771b-c282e2`](results/20260521T150143Z-728771b-c282e2/)
- Date: 2026-05-21
- Inputs kind: `public-reference` (no hub deployment exists)
- Engines: Oxigraph 0.5.8 (server, RocksDB backend) vs. Jena/Fuseki 5.0.0 (in-memory)
- Fixture: `inputs/probe-dataset.ttl` (SKOS + OWL + SHACL minimal graph)
  + `inputs/bulk-100k.nt` (100 000-triple deterministic SKOS taxonomy)

## Numbers

| engine   | pass | fail | manual | total |
|----------|-----:|-----:|-------:|------:|
| Oxigraph |   17 |    2 |      1 |    20 |
| Fuseki   |   18 |    1 |      1 |    20 |

## Gap detail (Oxigraph)

### G1. JSON-LD CONSTRUCT — `406 Not Acceptable` ([raw](results/20260521T150143Z-728771b-c282e2/raw/io-jsonld/))

Oxigraph 0.5.8 does not negotiate `application/ld+json` on the SPARQL
`/query` endpoint:

> The accept header does not provide any accepted format like
> application/n-quads or text/turtle

Fuseki serves it natively. README.md §Features advertises JSON-LD as a
supported serialization, so this is a real coverage gap, not a probe bug.

**Impact:** clients requesting JSON-LD from the SPARQL endpoint would
break. Two mitigations exist:

1. Serve JSON-LD by **converting on the way out** — Turtle from Oxigraph
   transcoded via `rdflib`/`pyld` at the API layer. Low risk for small
   responses; adds latency proportional to result size.
2. Serve JSON-LD **only on the REST resource endpoints** (per-vocabulary
   GET) and document the SPARQL endpoint as Turtle/N-Triples/RDF-XML/TriG
   only. Acceptable if SPARQL clients are machine-only.

Both keep Oxigraph viable. The decision belongs in the ADR.

### G2. SPARQL `SERVICE` federation — `400 Bad Request` ([raw](results/20260521T150143Z-728771b-c282e2/raw/sparql-service/))

ADR-004 §1 already flagged this as "gap to verify." Confirmed: Oxigraph
returns 400 on a SERVICE clause targeting `dbpedia.org`. Fuseki also
returns 400 in our test (likely network/sandbox), so the spike does
**not** treat this as Oxigraph-specific. The flag stands as a known
limitation in some Oxigraph builds; the hub must decide whether
cross-endpoint federation is required.

**Impact:** none today (hub spec does not require SERVICE). Re-evaluate
if/when the hub federates with other vocabulary registries.

## What Oxigraph passes (load-bearing rows)

SPARQL 1.1 SELECT / CONSTRUCT / ASK / DESCRIBE / UPDATE-INSERT /
UPDATE-DELETE; Graph Store Protocol PUT+GET; property paths;
named graphs; SKOS `broader+` transitive; Turtle, N-Triples, RDF/XML,
TriG content negotiation; SPARQL-results JSON; 100k-triple bulk load
(HTTP 201).

## Rows not auto-probed

| Row | Status | Why |
|---|---|---|
| C19 SHACL Core | manual | not in either engine via SPARQL probe; Jena has `jena-shacl`, Oxigraph has none — companion `rudof` per ADR-002 |
| C20 SHACL-SPARQL | manual | same — only Jena ships it |
| C21 OWL 2 RL runtime inference | manual | Jena's rule engine; Oxigraph: none built-in — companion `reasonable` per ADR-002 |
| C22 RDFS entailment regime | manual | engine-internal; needs OWL spike |
| C23 Persistence restart | manual | requires container restart; not in this run |
| C25 HTTP auth | manual | reverse-proxy concern; out of engine scope |

These are the rows where ADR-002 already documents a companion
component path. **Spike 1 does not block the L1/L2 swap on them** —
they belong to ADR-002 implementation, not to the L1/L2 engine choice.

## Recommendation to ADR reviewer

Treat the spike-1 outcome as: **Oxigraph clears the coverage gate
conditional on two API-layer decisions:**

1. JSON-LD policy (G1) — either convert at the gateway or restrict
   JSON-LD to REST endpoints.
2. Federation policy (G2) — confirm SERVICE is not required (likely;
   not in any documented hub requirement).

If both are agreed, Spike 1 flips to PASS. None of the failures are
intrinsic Oxigraph blockers.

## Reproducing

```bash
cd spikes
uv sync
docker compose -f docker/docker-compose.yml up -d
cd 01_oxigraph_coverage && ./run.sh
```

Each invocation produces a fresh `results/<run-id>/`; previous runs are
preserved.

## Provenance

Raw artifacts for this verdict:

- `results/20260521T150143Z-728771b-c282e2/manifest.json` — git SHA,
  host, tool versions, sha256 of every input file.
- `results/20260521T150143Z-728771b-c282e2/probe_results.json` — 40
  per-(row × engine) records with `verdict`, `detail`, `status_code`,
  `raw_path`.
- `results/20260521T150143Z-728771b-c282e2/raw/<probe>/<engine>.txt` —
  every HTTP response body, one file per probe per engine.
- `results/20260521T150143Z-728771b-c282e2/feature_matrix.md` —
  rendered template with verdict columns filled in.
