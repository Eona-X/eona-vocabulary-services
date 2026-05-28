# ADR-005: Vocabulary Browser Selection (L4)

- **Status**: Proposed
- **Date**: 2026-05-28
- **Layer / Purpose**: L4 Authoring & UI — *selection* (browsing only; authoring is out of scope and will be addressed in a separate ADR)
- **Context**: The Vocabulary Hub needs a human-readable interface for discovering, searching, and browsing ontologies, SKOS vocabularies, and SHACL shapes hosted by Oxigraph (ADR-004). This ADR covers the read-only browser. Editor/reviewer/publisher workflows are explicitly excluded.
- **Related**: [ADR-000](000-adr-process-and-constraints.md) (Constraints), [ADR-002](002-semantic-services-engine-selection.md) (L2 services), [ADR-004](004-l1-l3-component-reselection.md) (Oxigraph storage).

## Context

The Eona Vocabulary Hub hosts three asset types:

1. Ontologies (RDFS/OWL)
2. Schemas (SHACL shapes)
3. Reference data (SKOS concept schemes)

L1/L2 (Oxigraph) already exposes SPARQL and IRI dereferencing. This ADR selects the L4 *browsing* surface — a read-only UI for discovery and inspection. Authoring, governance, and editorial workflow are out of scope and belong to a future L4 *authoring* ADR.

### Expectations from IDS-RAM 4.0 §3.5.6 (Vocabulary Hub)

The browser is the human-facing face of an IDS Vocabulary Hub. Per IDS-RAM 4.0 §3.5.6, the Hub exists to *host, maintain, publish, and document* vocabularies beyond the IDS Information Model. The L4 browser must therefore expose, in human-readable form, the same artifacts the Hub serves to Connectors via IDS-conform endpoints:

- **Term access**: every defined term reachable by IRI, with its description, type/class, multilingual labels, and any annotations the Hub holds.
- **Vocabulary access**: complete vocabulary documents, partial subsets, and individual terms — each as a distinct, linkable page.
- **Namespace landing pages**: a page per managed namespace (e.g., `ids`, `idsc`, project-defined) summarising the vocabularies under it.
- **Versioning visibility**: surface available versions of every vocabulary, mark the current version, and present a diff/changelog view between versions.
- **Documentation & visualization**: render definitions, examples, and structural views (SKOS hierarchies, OWL class trees, SHACL targets/constraints).
- **HTML/RDF content negotiation**: the same IRI that returns the "small RDF document explaining the attribute" to a Connector must return a human-readable page to a browser. The dereferencing contract is shared with L2 (ADR-002); the browser provides the HTML representation.
- **Third-party vocabulary visibility**: vocabularies imported from external sources are first-class browsable assets, with provenance shown.

Out of scope for this ADR: term creation, editorial workflows, publication tooling, access control for editors. Those are L4 *authoring* concerns covered by a separate ADR. The browser only consumes what the Hub has already published.

### Read-path priorities

Human consumers (domain experts, modellers, dataspace integrators) and Connector operators dereferencing IRIs in a browser dominate the access pattern. Search quality, dereferencing latency, and version navigation are the load-bearing characteristics. Write-path concerns do not apply.

## Decision Drivers

1. **IDS-RAM §3.5.6 conformance**: every Hub-served artifact (term, subset, full vocabulary, namespace, version) has a corresponding browsable page reachable by stable IRI.
2. **Search quality and latency**: full-text search across labels (multilingual), notations, definitions, comments, and IRI fragments, with p95 < 100 ms on the published corpus.
3. **Format coverage**: first-class rendering of SKOS hierarchies, OWL/RDFS class & property pages, and SHACL shape summaries.
4. **Versioning & change presentation**: list versions per vocabulary, mark current, show inter-version diff (added / removed / changed terms).
5. **Performance under load**: SSR with HTTP caching; p95 TTFB < 300 ms for catalog, namespace, term, class, and shape pages.
6. **Content negotiation**: HTML at the IRI for browsers, RDF/JSON-LD/Turtle for Connectors (delegated to L2 — ADR-002 — but coordinated here).
7. **Stack alignment**: no new heavy runtimes. Project stack is Rust (Oxigraph) + Python (query-service, Morph-KGC per ADR-003) + TypeScript tooling. PHP and additional JVM services are disfavored.
8. **OSI license** (ADR-000 §2).
9. **Deployment footprint**: single container for the app + one sidecar search index; no managed external services.

## Options Considered

### Option A: Skosmos (PHP/Twig + Jena Fuseki backend)

| Aspect | Detail |
|---|---|
| License | MIT |
| Focus | SKOS / SKOS-XL browsing |
| OWL support | Weak (lists classes/properties but not first-class) |
| SHACL support | None |
| Search | Lucene-backed via Fuseki text index, mature |
| Runtime | PHP + Java (Fuseki) — adds two runtimes the project rejected in ADR-004 |
| Backend coupling | Hard requirement on Fuseki text index; does not target Oxigraph |

### Option B: ShowVoc (Java/Spring, SemanticTurkey backend)

| Aspect | Detail |
|---|---|
| License | BSD-3-Clause |
| Focus | SKOS, OWL, OntoLex browsing |
| SHACL support | Partial |
| Search | Rich, via SemanticTurkey |
| Runtime | JVM + SemanticTurkey + RDF4J — heavy, conflicts with ADR-004 lightweight driver |
| Backend coupling | SemanticTurkey is authoritative store; Oxigraph would be redundant |

### Option C: Static documentation generators (pyLODE, Widoco)

| Aspect | Detail |
|---|---|
| License | MIT / Apache 2.0 |
| Focus | Per-ontology HTML documentation |
| SKOS hierarchy browsing | None (single-file output) |
| SHACL support | Limited |
| Search | None across vocabularies (per-page only) |
| Runtime | Build-time only |

### Option D: Custom SPA (SvelteKit/TypeScript) + sidecar search index

| Aspect | Detail |
|---|---|
| License | Apache-2.0 (project) |
| Focus | Tailored read-only browser over Oxigraph SPARQL + sidecar FTS |
| SKOS / OWL / SHACL | All three rendered by purpose-built components |
| Search | Meilisearch sidecar populated from Oxigraph on publish |
| Runtime | Node (SSR) + Meilisearch container; no new language families |
| Backend coupling | Decoupled; Oxigraph stays authoritative |

## Analysis

```
                  SKOS  OWL   SHACL  Search  Latency  Stack fit  Effort
Skosmos (A)       *****  **    -      ****    ***      *          Low
ShowVoc (B)       ****   ****  **     ****    ***      *          Low
Static (C)        *      ****  *      *       *****    ****       Low
Custom SPA (D)    ****   ****  ****   *****   ****     ****       Medium
```

- **Skosmos** is the strongest off-the-shelf SKOS browser but drags in PHP *and* Fuseki. Oxigraph (ADR-004) was selected over Fuseki; reintroducing Fuseki as a Skosmos backend dependency reverses that decision for the UI layer alone.
- **ShowVoc** has the broadest format coverage but its SemanticTurkey backend duplicates Oxigraph's role and adds a JVM service — same conflict with ADR-004.
- **Static generators** are excellent for per-ontology reference pages but cannot satisfy Driver #1 (cross-corpus search) and do not browse SKOS hierarchies interactively.
- **Custom SPA** is the only option that (a) talks directly to Oxigraph, (b) lets us pick a search backend matched to the latency budget, and (c) covers all three asset types under one navigation model. Cost is the build effort, which is bounded below.

### Why a custom application is required

No surveyed OSS browser targets Oxigraph or covers SKOS + OWL + SHACL in one UI without pulling in a competing triplestore. Adopting Skosmos or ShowVoc means running their preferred backend alongside Oxigraph and synchronising the two — equivalent in operational cost to building the SPA, with worse stack fit. Static generators do not meet the search requirement.

### Effort estimate

Scope: read-only SvelteKit app, SSR pages for catalog / namespace / vocabulary / version / concept scheme / concept / class / property / shape, IRI dereferencing with content negotiation, version-diff view, Meilisearch sidecar with publish-time indexer. Authoring and editorial workflows excluded.

| Workstream | Tasks | Effort (PD, 1 senior FE + 0.25 BE) |
|---|---|---|
| Project shell, routing, SSR, layout, design tokens, i18n scaffolding | Base components, locale switch, multilingual labels everywhere | 8 |
| Catalog + facets (asset type, namespace, language, status, version) | List/filter endpoints over SPARQL | 6 |
| Namespace landing pages | Per-namespace summary, vocabularies & terms under namespace | 3 |
| Vocabulary pages (full + partial subset views) | Whole-doc, subset-by-filter, individual-term links per §3.5.6 | 5 |
| SKOS browser (tree, alt labels, mappings, multilingual) | Hierarchy component, lazy loading | 10 |
| OWL/RDFS class & property pages | Class hierarchy, domain/range, usage | 7 |
| SHACL shape pages | Shape → targets → constraints rendering | 4 |
| Versioning UI (version list, current marker, diff view) | added/removed/changed terms between two versions | 6 |
| IRI dereferencing + content negotiation (HTML branch) | HTML at IRI, RDF representations delegated to L2 endpoint | 3 |
| Meilisearch indexer (publish hook → docs) | Per-asset indexer, language analyzers, version-aware ranking | 7 |
| Search UI (instant search, highlighting, facets) | Frontend integration | 4 |
| Perf hardening, caching headers, SPARQL query cache | TTFB and search-latency budgets | 4 |
| Tests, CI, container packaging | Playwright + unit, single container build | 5 |
| Docs and acceptance against validation plan | IDS-RAM §3.5.6 trace matrix | 3 |
| **Total** | | **75 PD (~15 dev-weeks, ~3.4 PM)** |

Contingency: +25% → **~94 PD (~4.3 PM)**. Comparable to the operational cost of running Skosmos+Fuseki+sync alongside Oxigraph over a 12-month horizon, with strictly better stack fit, search latency, and §3.5.6 coverage.

## Recommendation

**Option D — Custom SvelteKit SPA + Meilisearch sidecar, browsing only, conformant to IDS-RAM §3.5.6.**

1. SvelteKit application, SSR by default, served from a single container alongside the Hub.
2. Backend reads exclusively via Oxigraph SPARQL 1.1 and RDF/JSON-LD content negotiation.
3. IRI strategy: every Hub-served artifact (namespace, vocabulary, version, term, subset) has a stable IRI; the same IRI returns HTML to browsers and RDF (Turtle/JSON-LD/RDF-XML) to Connectors via content negotiation. RDF branch is L2 (ADR-002); HTML branch is this app.
4. Meilisearch sidecar populated by a publish-time indexer (Python, in the existing query-service pipeline) — labels, alt labels, notations, definitions, comments, IRI fragments, per-language analyzers, version-aware.
5. Asset-type-specific renderers for SKOS, OWL/RDFS, SHACL. Namespace landing pages and per-vocabulary subset views included. No editor surface.
6. Versioning surface: version list per vocabulary, current-version marker, diff view (added / removed / changed terms) — backed by the publish pipeline's version graph.
7. Static fall-through for per-ontology reference pages via pyLODE is **not** adopted in this ADR; revisit if SEO of long-form definitions becomes a requirement.

### Rationale

- Meets Driver #1 (search) with Meilisearch — typo-tolerant, sub-50 ms typical, multilingual.
- Meets Driver #3 (perf) via SSR + HTTP caching + bounded SPARQL queries.
- Meets Driver #4 (stack) — no PHP, no extra JVM. Node for SSR, Python for indexer (already in stack), Rust for storage.
- Keeps authoring out of scope; that decision is deferred to its own ADR with its own drivers (governance, RBAC, edit conflict, provenance).

## Consequences

- **Positive**:
  - Unified browser across SKOS + OWL + SHACL.
  - Search latency and quality under our control.
  - No second triplestore.
- **Negative**:
  - ~3 PM build cost before first usable release.
  - We own all UI bugs and accessibility work; no upstream community fixes.
  - Meilisearch becomes a managed dependency (sync correctness, reindex on publish).
- **Neutral**:
  - Per-ontology static documentation (pyLODE/Widoco) remains an option for *publishing artefacts* outside the browser; not part of this decision.

## Validation Plan

Acceptance gates (must pass before status → Accepted):

1. **Search latency**: p95 < 100 ms over a corpus of ≥50k SKOS concepts + ≥5 mid-size ontologies on a single 4-core node.
2. **Page TTFB**: p95 < 300 ms for catalog, namespace, vocabulary, term, class, and shape pages on the same node.
3. **SKOS spike**: render a 3-level concept tree with 10k concepts; lazy-load children; interaction latency < 150 ms per expansion.
4. **OWL spike**: render a class page with inferred subclasses (materialized via L2) and verify cross-links.
5. **Indexer correctness**: publish → index lag < 30 s for a 1k-concept update.
6. **IDS-RAM §3.5.6 trace matrix**: each capability — term access, partial-subset access, namespace landing, version listing, version diff, multilingual labels, HTML/RDF content negotiation, third-party vocabulary visibility — has a passing end-to-end test against a fixture corpus.
7. **Dereferencing parity**: for a sampled set of 100 IRIs, the HTML page and the RDF response describe the same entity (same labels, types, key properties) — no drift between human and machine views.

Failures on any gate trigger a re-evaluation of the search backend (Oxigraph FTS vs. Meilisearch vs. Tantivy) or the version-store contract before commitment.

## References

- [Skosmos](https://skosmos.org/)
- [ShowVoc](https://showvoc.op.europa.eu/)
- [pyLODE](https://github.com/RDFLib/pyLODE)
- [Widoco](https://github.com/dgarijo/Widoco)
- [Meilisearch](https://www.meilisearch.com/) — MIT
- [SvelteKit](https://kit.svelte.dev/) — MIT
- [IDS-RAM 4.0 §3.5.6 — Vocabulary Hub](https://github.com/International-Data-Spaces-Association/IDS-RAM_4_0/blob/main/documentation/3_Layers_of_the_Reference_Architecture_Model/3_5_System_Layer/3_5_6_Vocabulary_Hub.md)
- [ADR-002](002-semantic-services-engine-selection.md)
- [ADR-004](004-l1-l3-component-reselection.md)
