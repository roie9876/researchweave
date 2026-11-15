# ResearchWeave company brain: technical proposal

Status: research-backed proposal, not a tested or approved architecture.
This refines and corrects the earlier
[architecture proposal](researchweave-architecture-proposal.md).

## 1. The key distinction

Blob Storage, PostgreSQL, and Azure AI Search do not themselves create
scientific understanding or connect research findings. They are storage and
retrieval infrastructure. ResearchWeave needs a **knowledge engine** and an
evidence model that use those stores to extract, connect, query, correct, and
explain knowledge.

The recommendation is to reuse an existing open-source knowledge engine
rather than build that entire layer from scratch. Start by testing
**TrustGraph** as the ontology-and-provenance-oriented candidate, with
**LightRAG** and **Graphiti** as comparisons. The winning engine and its
actual graph/vector/object backends must be selected together, after testing;
they are not assumed to be interchangeable.

## 2. Logical architecture

```text
Public sources + uploaded files + research outputs
                       |
                       v
       Ingestion: version, parse, identify, normalize
                       |
                       v
       Open-source knowledge engine + research adapters
       - identify entities and relationships
       - link hypotheses, claims, experiments, evidence
       - preserve source references and history
                       |
            +----------+-----------+
            |                      |
            v                      v
  Connected knowledge graph   Text/vector retrieval index
            |                      |
            +----------+-----------+
                       |
                       v
      Evidence-aware retrieval for research agents
       -> relevant graph paths and original evidence
       -> hypotheses, tests, findings, report
```

Different underlying implementations store these components differently:

- **Blob Storage:** original uploaded data, permitted source snapshots, and
  generated artifacts. A separate Blob container per run was requested.
- **PostgreSQL:** proposed canonical application records such as runs,
  objectives, task state, messages, evidence identifiers and status.
- **Graph store:** connected entities, claims, hypotheses, and evidence links,
  backed by the store supported by the selected knowledge engine. Do not
  assume PostgreSQL/AGE without validating the engine's driver.
- **Search index:** text and vector retrieval. The selected engine may already
  supply this; Azure AI Search is an alternative or supplement only if tests
  justify the duplication and cost.

The exact canonical ownership of evidence and extracted claims across the
engine and the application must be designed for the selected integration.
Indexes and graph projections must be recoverable from authoritative
records; no two stores should silently disagree about which version is valid.

## 3. How connections are created

1. **Register and preserve the source.** Create a stable source identifier,
   version and content hash; record its origin, access terms and capture
   status. Store permitted original files and artifacts in Blob Storage.
2. **Parse the actual material.** Use existing document-processing software
   such as Docling, plus suitable spreadsheet/CSV parsers. Keep page,
   section, table, cell, file or other locators where supported. Raw data and
   numerical results remain accessible as data, not only as embeddings.
3. **Extract candidate knowledge.** Use the chosen engine and configured
   models to identify domain entities, methods, observations, hypotheses and
   relationships. Validate the output against an explicit domain schema.
   Extraction is a proposal, not proof.
4. **Resolve identities conservatively.** Use established identifiers and
   aliases where available; flag uncertain matches rather than merging
   unrelated entities automatically. Retain the original references and
   contexts.
5. **Record claims with evidence.** Link each claim or hypothesis to the
   source version and specific evidence, relevant conditions, time,
   research run, and review status. Preserve supporting and contradicting
   claims separately; don't silently replace disputed scientific findings.
6. **Update the graph and retrieval indexes.** Use durable, retryable,
   idempotent work and versioned updates. Track lag or failed indexing; do not
   present stale or missing index data as successfully processed.
7. **Retrieve and investigate.** When a researcher asks a question, use
   keyword/vector search to find candidate evidence and graph traversal to
   follow relevant relationships. Restrict results to authorized sources and
   prior investigations the researcher selected. Agents inspect original
   evidence, form hypotheses, run analyses, and independently check important
   findings.
8. **Maintain history and corrections.** Source changes, retractions, and
   deletions must trigger explicit updates to claims, graph edges, search
   indexes, and affected reports. Define historical retention and deletion
   semantics before implementation.

Graph edges describe relationships; they do not prove causation. An
automatically extracted claim, a measured observation, a verified
calculation, and a hypothesis must remain distinguishable.

## 4. Example: connecting two investigations

This is a fictional example, not a scientific finding.

- Investigation A records that **material X** showed degradation under a
  specific condition, with a link to the dataset and calculation.
- Investigation B examines **material Y** and cites a paper describing a
  mechanism that could also be relevant to material X.
- The engine links each material, condition, mechanism, experiment, claim,
  and supporting source. It keeps the original contexts and any contradictory
  findings.
- A later agent can traverse `material X -> degradation -> condition ->
  possible mechanism -> material Y`, retrieve the underlying sources, and
  propose a hypothesis for testing. It must not state that the connection is
  proven merely because a path exists.
- The researcher can inspect the graph path, data, source references,
  tests, and whether the conclusion remains a hypothesis.

This is how the system can *find candidate connections*. Whether those
connections are accurate, useful, or novel still requires evaluation.

## 5. Existing projects: what we would reuse and what remains

| Question | TrustGraph | LightRAG | Graphiti |
|---|---|---|---|
| Core approach | Ontology-guided graph extraction and provenance | Lightweight graph-enhanced document retrieval | Incremental, temporal context graph |
| Knowledge model | RDF, optional OWL ontology, and source/explanation graphs | Entities, relationships, document chunks, and graph/vector retrieval | Typed entities, temporal edges, and source episodes |
| Evidence trail | Documents, pages, chunks, and extracted graph edges through PROV-O | Source and chunk citations; exact scientific-evidence granularity must be tested | Each derived fact traces to an ingested episode; page/measurement-level evidence needs testing or an added layer |
| Changes and contradictions | Ingestion and provenance exist; scientific contradiction handling needs validation | Incremental changes and deletion are documented; conflict semantics need validation | Temporal invalidation and historical edges; scientific disagreements must not be silently treated as superseded facts |
| Typical documented graph stores | Cassandra; other graph backends are available | PostgreSQL/AGE, Neo4j, and others | Neo4j, FalkorDB, Neptune; no documented official PostgreSQL/AGE core driver |
| Deployment footprint | Multiple services plus graph, vectors, object storage, and messaging | Comparatively simple starting configurations; backend and concurrency choice matters | Python framework plus graph database; application supplies service, access control, and operations |
| Core license | Apache-2.0 | MIT | Apache-2.0 |

This table summarizes documented or inspected behavior, not independently
measured quality or scale. Product and database versions must be pinned in
any comparison.

### TrustGraph: first knowledge-engine candidate

- **Reuse to evaluate:** ontology-grounded extraction, connected graph,
  source lineage and graph-based retrieval. Its core is Apache-2.0.
- **Why first:** the requested brain needs structured relationships and
  source provenance across many research investigations, not merely
  conversation memory.
- **Integration cost:** its documented architecture uses Cassandra for
  graph data, Qdrant for embeddings, an S3-compatible object store, and
  messaging such as Pulsar or RabbitMQ. These are real operational
  dependencies, not PostgreSQL/AGE or native Azure Blob. Other supported
  backends do not automatically eliminate all of these responsibilities.
  Determine whether an Azure-compatible deployment and Blob integration are
  practical without unsupported assumptions.
- **Boundaries:** open-source versus enterprise IAM, policy, and temporal
  features must be checked for the exact version. The engine is not proven
  to deliver scientific correctness or the requested organization-wide scale.

### LightRAG: simpler graph/retrieval comparison

- **Reuse to evaluate:** document entity/relationship extraction,
  graph-enhanced retrieval, citation support, incremental processing, and
  document deletion. The core is MIT.
- **Integration advantage:** its PostgreSQL graph storage uses Apache AGE,
  so it is a candidate for an integrated PostgreSQL-based prototype.
- **Risk:** an open upstream report describes concurrent ingestion failures
  with a particular PostgreSQL/AGE configuration. This is a reported issue,
  not an independently reproduced result or a universal scale limit.
  Test the exact versions and concurrency. Research-grade provenance,
  competing evidence, and authorization still need verification or
  application-level work.
- **Version compatibility:** the inspected PostgreSQL implementation also
  guards against unsupported AGE versions. Confirm the Azure PostgreSQL,
  AGE, and LightRAG versions work together rather than assuming any
  PostgreSQL/AGE combination is safe.

### Graphiti: temporal context comparison

- **Reuse to evaluate:** incremental entity and relationship extraction,
  episode provenance, temporal edges and graph-based retrieval. The core
  is Apache-2.0.
- **Integration cost:** its documented core drivers use Neo4j, FalkorDB, or
  Neptune; PostgreSQL/AGE is not a documented official core backend. A
  third-party driver exists but is not assumed production-ready.
- **Boundaries:** temporal invalidation of an outdated fact is not the same
  as scientifically resolving competing hypotheses. Preserve original
  evidence separately. Its reference REST and MCP servers explicitly lack
  authentication and authorization and are not production-ready. The
  application must supply appropriate authorization and review
  graph-database licensing: for example Neo4j Community is GPLv3 and
  FalkorDB is SSPL.

### Cognee: additional candidate, not an automatic PostgreSQL answer

Cognee has a reusable document-to-graph memory pipeline and an Apache-2.0
core. Its documentation describes the bundled PostgreSQL graph adapter as a
demo and identifies a separate licensed production adapter. An alternate
backend would need its own deployment and license review.

**Important:** these are alternatives to compare, not four frameworks that
must all be deployed. Reuse the best-supported pieces where integration and
licensing are verified; implement ResearchWeave-specific evidence semantics,
permissions, investigation selection, and orchestration only where missing.

### Current recommendation and fallback

Prototype **TrustGraph first** because ontology, source lineage, and
cross-document relationships are central to this product. In parallel or
sequence, run the same evidence and workload tests against **LightRAG**;
use **Graphiti** as the temporal-knowledge comparison. This is not a claim
that TrustGraph is already proven best.

If TrustGraph's actual multi-service deployment, Azure integration, or
open-source feature boundaries do not meet the gates, use the comparison
results to choose a different engine or backend. Do not retain both full
stacks by default. Keep the research evidence and application interface
portable so changing engines is feasible, and validate the claimed export
and reindex path.

## 6. Azure service choices, revised

- **Blob Storage: yes, as requested.** It is the original-file and artifact
  store, not the knowledge graph.
- **PostgreSQL: recommended for application state.** Relational records,
  transactions, and joins fit investigation metadata and user interaction.
  It does not have to be the graph backend.
- **Graph database/backend: not yet selected.** TrustGraph, LightRAG, and
  Graphiti have different supported backends. Selecting an engine implies
  real deployment and license choices; PostgreSQL/AGE must earn its place
  through compatibility and workload testing.
- **Azure AI Search: optional, not preselected.** Compare its hybrid search
  with the selected engine's own search and a PostgreSQL-based baseline.
  Add it if relevance, scaling or operating evidence justifies the extra
  index and ongoing charges.
- **Cosmos DB: a possible backend, not a necessary consequence of scale.**
  If TrustGraph's Cassandra storage is selected, compare self-managed Apache
  Cassandra, Azure Managed Instance for Apache Cassandra, and the Cassandra
  API of Azure Cosmos DB. Cosmos's Cassandra API is a compatibility layer,
  not the same implementation as Apache Cassandra; verify the exact
  TrustGraph queries, schemas, partitioning and consistency before treating
  it as a supported replacement. Neither PostgreSQL nor Cosmos DB alone
  solves graph extraction, provenance, or scientific reasoning.

## 7. What would make the system robust?

No candidate has been installed or benchmarked for this workload; there is
not enough evidence to promise enterprise-scale robustness. The user expects
an eventual corpus on the order of **100,000 to 1 million items**. An item
may be a document, dataset, or research artifact; sizes, formats, growth
rate, and the number of derived chunks remain unknown.

The item count alone is not the size of the graph or search index. For an
illustrative upper-end scenario only, 1 million documents with 100 chunks
each would produce 100 million chunks. Storing one 1,536-dimensional
32-bit vector per chunk would use about 614 GB of raw vectors alone, before
indexes, replicas, text, graph edges, original files, or backups. Actual
chunk counts, vector dimensions, representations, and usage may differ.

Design for incremental processing with durable queues, batched and
idempotent writes, bounded concurrency, independent scaling of extraction
and querying, and observable indexing lag. Avoid regenerating the entire
graph on each update. Evaluate source-quality and domain-aware extraction to
control processing costs without assuming every chunk deserves an expensive
model call. Verify the selected engine actually supports the required update
and recovery behavior.

Test a representative, versioned dataset with known relationships,
conflicting claims, tables, long documents, and updated/deleted sources:

- Compare TrustGraph, LightRAG, and Graphiti using equivalent data,
  extraction models, retrieval questions, and grading. Add a conventional
  keyword/vector retrieval baseline.
- Proposed mandatory correctness gates: every conclusion labeled verified
  has retrievable evidence and a recorded verification method; test cases
  return no evidence outside the selected authorized investigation scope;
  and deleting one source removes its attributable search results while
  retaining independent evidence from other sources. Unknown or unsupported
  claims must remain explicitly unverified.
- Measure entity-resolution accuracy, evidence/provenance completeness,
  multi-hop retrieval quality, false or missing connections, handling of
  conflicts, and usefulness of generated hypotheses.
- Exercise simultaneous ingestion and queries, recovery after interruption,
  duplicate events, partial writes, model/provider outages, authorization,
  source updates and deletes, and full graph/index rebuild.
- Measure document and chunk count, graph nodes/edges, ingest rate, query
  latency, model calls, storage, and cost as workload grows. Run
  representative long-running investigations.
- As a provisional scale-test design, ramp a representative corpus through
  10,000, 100,000, and 1,000,000 documents, with parallel ingestion and
  research queries. Specify document sizes, graph density, writer counts,
  and quality thresholds before running; these are test scenarios, not
  vendor guarantees or agreed production requirements.
- Define workload sizes and pass/fail thresholds before tests and obtain
  approval before tests that incur material Azure charges. Do not confuse
  vendor demonstrations or benchmark claims with results for this project.

## 8. Sources

- [Market study: knowledge systems](../../../researchweave/docs/autonomous-research-market-study-2026-11-14.md)
  documents the inspected versions and limitations.
- [TrustGraph repository](https://github.com/trustgraph-ai/trustgraph),
  [storage architecture](https://docs.trustgraph.ai/architecture/storage.html),
  and [open-source and enterprise security](https://docs.trustgraph.ai/architecture/security.html).
- [LightRAG repository](https://github.com/HKUDS/LightRAG),
  [PostgreSQL graph implementation](https://github.com/HKUDS/LightRAG/blob/main/lightrag/kg/postgres_impl.py),
  and [reported concurrent AGE ingestion issue](https://github.com/HKUDS/LightRAG/issues/4211).
- [Graphiti repository](https://github.com/getzep/graphiti) and
  [documented graph drivers](https://github.com/getzep/graphiti/tree/main/graphiti_core/driver)
  and [reference-server security](https://github.com/getzep/graphiti/blob/main/server/README.md).
- [Cognee graph-store documentation](https://docs.cognee.ai/setup-configuration/graph-stores).
- [TrustGraph architecture and service dependencies](https://docs.trustgraph.ai/architecture/architecture.html)
  and [ontology support](https://docs.trustgraph.ai/learn/ontologies.html).
- [Azure Cosmos DB Cassandra compatibility](https://learn.microsoft.com/en-us/azure/cosmos-db/cassandra/support)
  and [managed Cassandra versus Cosmos Cassandra](https://learn.microsoft.com/en-us/azure/cosmos-db/cassandra/choose-service).
- [Neo4j licensing](https://neo4j.com/licensing/) and
  [FalkorDB licensing](https://docs.falkordb.com/references/license).
- [Azure AI Search change and deletion detection](https://learn.microsoft.com/en-us/azure/search/search-how-to-index-azure-blob-changed-deleted).
