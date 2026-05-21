# ADR-003: Full Rust Stack Proposition

- **Status**: Proposed
- **Date**: 2026-05-21
- **Layer / Purpose**: Cross-cutting / Strategy — *architecture-evolution*
- **Context**: Evaluating the feasibility and benefits of moving from a polyglot (Java/Python/Rust) stack to a unified, high-performance Rust ecosystem for the Vocabulary Hub.
- **Related**: [ADR-000](000-adr-process-and-constraints.md) (Constraints), [ADR-001](001-triplestore-stack-selection.md) (Storage), [ADR-002](002-mapping-and-virtualization.md) (Mapping)

## Context

The current architectural trajectory (ADR-001, ADR-002) favors a hybrid stack:
- **Java** for the triplestore (Jena/Fuseki), virtualization (ONTOP), and IDS adapter (EDC).
- **Python** for high-speed ETL (Morph-KGC) and ingestion pipelines.
- **Rust** as a potential niche player (Oxigraph).

While "safe" due to the maturity of Java tools, this approach introduces a "Polyglot Tax":
1. **Memory Overhead**: JVM-based services (Jena + EDC) require 2-5 GB RSS minimum.
2. **Serialization Latency**: Moving RDF data across the Rust/JVM/Python boundaries on the hot path (e.g., during IDS artifact transfers) incurs significant CPU and latency costs.
3. **Operational Complexity**: Managing three different runtimes (JRE, Python, Rust binaries) in a single deployment.

## The "Full Rust" Proposition

We propose a unified architecture leveraging the **Polars/Arrow** and **Oxigraph** ecosystems to handle all semantic layers natively in Rust.

### The Proposed Stack

| Layer | Component | Implementation | Displacement |
|---|---|---|---|
| **L1 Storage** | **Triplestore** | **Oxigraph** (RocksDB backend) | Displaces Apache Jena TDB2 |
| **L2 Services** | **SPARQL Engine** | **OxiRS** or `oxigraph-server` | Displaces Fuseki |
| **L3 Mapping** | **NoETL (Virtual)** | **Chrontext** (Polars-based) | Displaces ONTOP (Java) |
| **L3 Mapping** | **ETL (Material)** | **Maplib** (OTTR/Arrow) | Displaces Morph-KGC (Python) |
| **L5 Conformance**| **IDS Adapter** | **`idscp2-rust` + `odrl-rs`** | Displaces Java EDC Adapter |
| **L6 Pipelines** | **Orchestration** | **Tokio + Polars** | Displaces Python/Bash scripts |

---

## Analysis by Layer

### L1 & L2: Storage and Services
**Oxigraph** has reached production maturity. It offers a 10x memory advantage over Jena and eliminates the JVM's "cold start" issues.
- **Benefit**: Footprint reduced to ~100-200MB RSS. Zero-copy access to the RDF model for other Rust components.

### L3: Mapping and Virtualization
Instead of RMLMapper (Java) or Morph-KGC (Python), we adopt the **DataTreehouse** toolset:
- **NoETL (Chrontext)**: Optimized for high-volume hybrid queries (Knowledge Graph + Analytical DB) using Polars. It is specifically designed for the "Dataspace" use case of sensor/time-series data.
- **ETL (Maplib)**: Benchmarks show it is **47x to 182x faster** than Morph-KGC. It leverages Apache Arrow for extreme materialization throughput.

### L5: IDS Conformance
The "serialization penalty" identified in ADR-001 (Rust triplestore ↔ Java adapter) is a valid concern. However, the solution is not to stay in Java, but to **remove the boundary**.
- **Strategy**: Use `idscp2-rust` for secure transport and a Rust-native "Lightweight Data Plane." The hub can interface with an external Java EDC "Control Plane" for contract negotiation while serving actual RDF artifacts through a high-performance Rust Data Plane.

---

## Decision Drivers & ADR-000 Compliance

1. **Functional Coverage**: Covers NoETL, ETL, RML/R2RML (via MappingLoom-RS), and CSVW.
2. **Performance**: Polars-based engines provide the highest throughput available in the OSS semantic ecosystem.
3. **Resource Efficiency**: Fits the entire hub into a < 1 GB container, making it ideal for edge deployments.
4. **License**: All proposed crates (`oxigraph`, `polars`, `chrontext`, `maplib`) are **Apache-2.0 or MIT**.
5. **Modernity**: Aligns with the shift toward columnar data processing (Arrow) in the semantic web community.

---

## Consequences

- **Positive**:
  - Unified runtime (single static binary possible).
  - Massive reduction in infrastructure costs and memory footprint.
  - No serialization penalty on the hot path.
  - High-speed ingestion (millions of triples/sec).
- **Negative**:
  - Smaller community support compared to the Apache Jena ecosystem.
  - Requires Rust expertise for core maintenance.
  - IDS tooling in Rust is currently more "modular" than the monolithic EDC.

## Implementation Roadmap

1. **Phase 1 (Ingestion)**: Replace the Python query-service with a **Maplib**-based service.
2. **Phase 2 (Virtualization)**: Deploy **Chrontext** as a sidecar to handle large SQL/Time-series sources.
3. **Phase 3 (Core)**: Migrate the primary triplestore to **Oxigraph**.
4. **Phase 4 (Connectivity)**: Integrate the Rust-native IDS Data Plane.

## References

- [Oxigraph — GitHub](https://github.com/oxigraph/oxigraph)
- [Chrontext — GitHub](https://github.com/DataTreehouse/chrontext)
- [Maplib — GitHub](https://github.com/DataTreehouse/maplib)
- [MappingLoom-RS — GitHub](https://github.com/RMLio/mappingloom-rs)
- [GTFS-Madrid-Bench (maplib vs Morph-KGC)](https://ieee.org)
- [IDS-RAM 4.0 Conformance](https://github.com/International-Data-Spaces-Association/IDS-RAM_4_0)
