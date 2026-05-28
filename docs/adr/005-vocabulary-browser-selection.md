# ADR-005: Vocabulary Browser and Documentation Selection (L4)

- **Status**: Proposed
- **Date**: 2026-05-28
- **Layer / Purpose**: L4 Authoring & UI — *selection*
- **Context**: The Vocabulary Hub requires a human-readable interface for discovering, searching, and browsing ontologies, SKOS vocabularies, and SHACL shapes.
- **Related**: [ADR-000](000-adr-process-and-constraints.md) (Constraints), [ADR-004](004-l1-l3-component-reselection.md) (Storage is Oxigraph).

## Context

The Eona Vocabulary Hub hosts three types of semantic assets (per the README):
1. **Ontologies** (RDFS/OWL)
2. **Schemas** (SHACL shapes)
3. **Reference data** (SKOS concept schemes)

While the L1/L2 layer (Oxigraph) provides machine-readable access via SPARQL and IRI dereferencing, a human-readable UI (L4) is essential for "discoverability" and "human-readable documentation" (per README features). This ADR evaluates whether to adopt an off-the-shelf OSS tool or invest in a custom development.

## Decision Drivers

1. **Format Coverage**: Must handle SKOS (hierarchies, labels) and OWL/RDFS (classes, properties) effectively.
2. **Search Experience**: Needs high-performance search across labels, notations, and definitions.
3. **Maintenance & Effort**: Preference for existing mature tools to minimize "reinventing the wheel."
4. **Stack Alignment**: Should be lightweight and ideally not introduce heavy new runtime requirements (e.g., another large JVM).
5. **Branding & UI/UX**: Ability to provide a modern, professional interface that matches the Eona project identity.
6. **Governance Integration**: Potential to eventually support the "editor/reviewer/publisher" roles mentioned in the README.

## Options Considered

### Option A: Skosmos (PHP/Twig)

The de-facto standard for SKOS-based vocabulary browsing.

| Aspect | Detail |
|---|---|
| License | MIT |
| Main focus | SKOS / SKOS-XL |
| OWL support | Basic (displays classes/properties, but less optimized than SKOS) |
| Search | Built-in, uses Lucene/Text index or SPARQL queries |
| Maturity | Very high (used by Finto, FAO, many national libraries) |
| Runtime | PHP / Web server |

### Option B: ShowVoc (Java/Spring)

The browsing companion to VocBench 3.

| Aspect | Detail |
|---|---|
| License | BSD-3-Clause |
| Main focus | Full RDF model (SKOS, OWL, OntoLex) |
| Search | Rich, leveraging the VocBench/SemanticTurkey backend |
| Maturity | High, backed by EU Publications Office |
| Runtime | Java (heavyweight) |

### Option C: Custom Development (Svelte/TypeScript SPA)

Building a tailored browser that queries the Oxigraph SPARQL endpoint directly.

| Aspect | Detail |
|---|---|
| License | Apache 2.0 (local) |
| Main focus | Tailored to Eona's specific needs and branding |
| Search | Requires implementing a search abstraction or using SPARQL `regex`/`fts` |
| Maturity | N/A (new development) |
| Effort | High (estimated 3–6 PM for a feature-complete browser) |

### Option D: Static Documentation Generators (Widoco / pylode)

Generating HTML pages at publish time from the RDF sources.

| Aspect | Detail |
|---|---|
| License | MIT / Apache 2.0 |
| Main focus | Human-readable documentation for ontologies |
| Search | Limited or non-existent across vocabularies |
| Runtime | None (static files) |

## Analysis

```
                  SKOS support  OWL support  Search  Effort  Runtime footprint
Skosmos (A)       *****         **           ****    Low     Medium (PHP)
ShowVoc (B)       ****          ****         ****    Low     High (JVM)
Custom SPA (C)    ***           ***          **      High    Low (Client-side)
Static Docs (D)   **            *****        *       Low     Zero
```

- **Skosmos** is the strongest candidate for *browsing* existing SKOS vocabularies, which is the primary use case for "Reference Data." Its UI is battle-tested and highly usable. However, it requires a PHP environment, which is currently not in the stack.
- **ShowVoc** provides better OWL support but its weight and complexity (Java/Spring) go against the "lightweight" driver that led to Oxigraph re-selection in ADR-004.
- **Custom Development** allows the best branding and potential integration of the "governance" roles (editors, reviewers) mentioned in the README. However, re-implementing hierarchy browsing and multilingual search from scratch is a significant investment.
- **Static Documentation** (like pylode) is excellent for the *documentation* aspect of ontologies but fails as a *discoverability* tool where users need to search across concepts.

## Recommendation

**Hybrid Approach: Custom SPA for the Hub Front-end + Integrated Browsing Components.**

1. **Phase 1: Custom "Shell" and Discovery UI (Svelte/TS)**. Develop a lightweight Svelte SPA that serves as the Hub's landing page, displaying the catalog of vocabularies and providing a global search across metadata.
2. **Phase 2: Use `pylode` for Ontology Documentation**. For RDFS/OWL ontologies, generate static documentation pages using `pylode` (Python-based, aligns with L3 stack) and link them from the shell.
3. **Phase 3: Custom "SKOS-lite" Browser**. Instead of deploying a full Skosmos instance, implement a specialized Svelte component for SKOS hierarchy navigation, querying Oxigraph directly. This keeps the stack "Rust + Python + TS" without adding PHP or more Java.

### Rationale

- **Avoids Stack Bloat**: Prevents introducing PHP (Skosmos) or re-introducing a large JVM (ShowVoc) for the UI layer.
- **Tailored Governance**: A custom SPA can natively implement the "editor/reviewer" workflows and "governance" features mentioned in the README, which are not present in Skosmos/ShowVoc.
- **Leverages Oxigraph**: Oxigraph 0.5.8's native support for JSON-LD and SPARQL 1.1 makes building a decoupled SPA straightforward.
- **Phased Value**: Starts with static docs (fast to ship) and evolves into a rich interactive browser.

## Consequences

- **Positive**:
  - Unified Eona branding and UX.
  - No new heavy backend runtimes.
  - Direct path to implementing the governance features in the README.
  - Aligns with the modern "Headless" architecture.
- **Negative**:
  - Higher initial development effort compared to just deploying Skosmos.
  - Search functionality will be simpler than Skosmos's until a dedicated index (e.g., Meilisearch or Oxigraph FTS) is integrated.
- **Neutral**:
  - Documentation for ontologies is "Static-first," which is standard practice for high-quality ontology documentation (similar to W3C specs).

## Validation Plan

1. **UX Spike**: Create a minimal Svelte app that queries Oxigraph for a SKOS concept tree to validate latency and ease of use.
2. **pylode Integration**: Integrate `pylode` into the query-service pipeline to automatically generate docs on vocabulary publication.
3. **Search Bench**: Evaluate Oxigraph's `FILTER regex` vs. a sidecar search index for the "Global Search" requirement.

## References

- [Skosmos](http://skosmos.org/)
- [VocBench 3 / ShowVoc](http://vocbench.uniroma2.it/showvoc/)
- [pylode (Python Linked Data Editor/Documentation)](https://github.com/RDFLib/pyLODE)
- [Widoco](https://github.com/dgarijo/Widoco)
- [ADR-004: Re-selecting L1–L3 Components](004-l1-l3-component-reselection.md)

