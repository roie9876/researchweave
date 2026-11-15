# ResearchWeave: proposed architecture

Status: architecture proposal for discussion, not an approved design or a
tested deployment. It reflects the current specification and favors reusable
open-source application components on Azure. Product, subscription, region,
quota, licensing, security, and compatibility checks remain necessary.

The [product specification](research-system-specification-draft.md) is the
requirements source. The [market study](../../../researchweave/docs/autonomous-research-market-study-2026-11-14.md)
provides the starting comparison of existing software.

The [company-brain proposal](researchweave-company-brain-proposal.md)
supersedes the earlier assumption that PostgreSQL/AGE and Azure AI Search
are the default graph and retrieval solution. The knowledge engine and its
supported backends must be selected and tested together.

The [core components proposal](researchweave-core-components-proposal.md)
compares existing research applications and agent runtimes. It recommends
evaluating AgentScope 2.0 first for dynamic teams, with LangGraph as an
alternative; their integration with Temporal must be validated.

## 1. Proposed stack in one page

| Building block | Initial recommendation | Role and qualification |
|---|---|---|
| Research application | Evaluate OpenScientist first | Reuse its application, code, or patterns where they satisfy the requirements; compare Agent Zero and OpenHands as appropriate. |
| Web UI | Existing application UI or React, TypeScript, Vite | Bilingual research workspace, live conversation, progressive disclosure. |
| Application API | Existing compatible API or Python and FastAPI | Authentication, investigation management, live input, event delivery, reports, and authorization. |
| Application hosting | Azure Container Apps | Host UI/API and research workers without managing Kubernetes initially. |
| Model access | Microsoft Foundry / Azure-hosted model endpoints | Call selected model deployments through an adapter. Use model endpoints without requiring the managed Agent Service as the core runtime. |
| Agent logic | Evaluate AgentScope 2.0 first; compare LangGraph / Deep Agents | Dynamic teams are a central requirement. Verify runtime-created roles, inherited permissions, model-pool switching, steering, and durability. |
| Durable coordination | Self-hosted Temporal and its Python SDK | Durable run lifecycle, retries, signals, and child work. Validate secure networking and production operations on the selected Azure hosting. |
| Application database | Azure Database for PostgreSQL Flexible Server | Canonical investigations, permissions, messages, tasks, evidence metadata, claims, source links, and event records. |
| Knowledge engine and graph | Evaluate TrustGraph first, with LightRAG and Graphiti as comparisons | Reuse existing extraction, connected graph, and provenance capabilities; evaluate their actual supported storage backends, integration and licenses. |
| Knowledge retrieval | Knowledge-engine retrieval; Azure AI Search optional | Compare graph, keyword and vector retrieval against appropriate baselines. Do not assume a second index is necessary. |
| Raw data and artifacts | Azure Blob Storage | A separate container per investigation for uploads and artifacts; retain source files where terms permit. |
| Document processing | Evaluate Docling and complementary CSV/spreadsheet parsers | Extract structured content and preserve document locations; verify model licenses and extraction quality. |
| Public research | Azure-hosted web search capability plus a separate retrieval/reading adapter | Search, obtain permitted public pages and scientific sources, and record citations. The exact combination is to be validated. |
| Code execution | Azure Container Apps Sandboxes, subject to availability/security proof of concept | Isolated workspaces for generated tools, code and package installation. GPU/heavy workloads need an additional verified compute backend. |
| Identity and secrets | Microsoft identity platform, managed identities, Azure Key Vault as needed | Approved Microsoft accounts, service-to-service identity and secret management; authorization is enforced by ResearchWeave. |
| Operational visibility | Azure Monitor and Application Insights | Application and infrastructure diagnostics. The user-facing research timeline remains a ResearchWeave feature. |
| Deployment | Bicep compiled to ARM JSON plus a guided Azure portal deployment | Publish a deploy button and setup guidance; model quota, app registration, permissions and costs still require checks. |

These are recommendations, not assurances that all integrations work together
today. No Azure resource or application has been deployed for this proposal.

## 2. System shape

```text
Researcher
    |
    v
React research workspace (English / Hebrew)
    |
    | authenticated requests, live event stream
    v
FastAPI application + authorization
    |
    +-- Research run / event store ----------------------+
    |                                                    |
    +-- Temporal coordinator <--> lead researcher        |
    |      |                    <--> specialists         |
    |      |                    <--> reviewer agents     |
    |      +--> research tools and compute broker         |
    |                 |                                  |
    |                 +--> isolated Azure sandboxes      |
    |                 +--> public web / science APIs     |
    |                 +--> Foundry model endpoints       |
    |                                                    |
    +-- Company brain -----------------------------------+
           |                  |                  |
           v                  v                  v
    Azure Blob          PostgreSQL        Knowledge engine
    files/artifacts     research state    graph + retrieval
```

Operational logs and traces go to Azure Monitor / Application Insights, not
in place of the user-facing research timeline. This diagram does not require
each named responsibility to be a separate application or VM.

## 3. Company brain: what is stored where

The brain is not just a vector database and not just agent conversation
history. It has several complementary, independently accountable parts.

### A. Original evidence and artifacts: Blob Storage

- Each investigation has its own Blob container for uploaded files and
  generated artifacts. Store the original version, content type, owner/run
  reference, checksums, and version or capture metadata.
- Store permitted captures of public sources and extracted text when legally
  and technically possible; otherwise retain reference and access metadata.
- Store reports, code, figures, datasets, and calculation outputs as
  versioned artifacts, not as database fields or only in the agent context.
- Do not assume a Blob mount alone provides per-user authorization. The
  application and compute broker must enforce the selected access policy.

### B. Canonical research state: PostgreSQL

Store structured records for researchers and approvals; investigations and
objective revisions; messages; tasks and attempts; sources and source
versions; findings, claims and hypotheses; evidence links; reviews; budgets;
reports; and a durable event log. Original files stay in Blob Storage.

A claim is not automatically scientific truth. Record its type, source,
supporting or contradicting evidence, relevant conditions, timestamps,
verification state, and revision history. Preserve conflicting claims and
failed attempts rather than silently overwriting them.

### C. Connected knowledge: graph over research records

Represent concepts, research questions, experiments, datasets, methods,
claims, and evidence as entities and typed relationships. For example:

```text
Question -> investigated by -> Investigation
Investigation -> proposes -> Hypothesis
Hypothesis -> supported by / contradicted by -> Evidence
Evidence -> extracted from -> Source version
Experiment -> tests -> Hypothesis
```

Initial recommendation: evaluate TrustGraph's existing ontology, provenance,
and graph-retrieval capabilities against LightRAG and Graphiti. These
projects have different supported graph and object-store backends; do not
assume any of them can use PostgreSQL/AGE and Blob Storage unchanged.
LightRAG's AGE backend is a specific comparison candidate, subject to
concurrent-ingestion and version checks.

The application and selected engine must together model provenance,
validity, contradictions, access, and deletion. Define canonical ownership and
use durable change records to maintain any derived graph projections. Verify
graph backend licensing, integration, and performance before selection.

### D. Retrieval: selected engine, with Azure AI Search as an option

Use the selected engine's graph, keyword, and vector capabilities to retrieve
eligible passages, source metadata, and findings. Compare Azure AI Search as
an optional supplement. Apply authorization and the researcher's selected
prior-investigation filters before returning results. Keep references to
source versions and locations.

Blob Storage holds original files and PostgreSQL holds application state.
Determine authoritative ownership of extracted claims and their provenance
when the engine is selected. Maintain search documents as rebuildable
projections using versioned, retryable indexing events. Handle deletions,
corrections, index lag, and permission changes explicitly; expose indexing
failures instead of treating stale indexes as current.

Use PostgreSQL full-text search and pgvector as one evaluation baseline.
Compare retrieval quality and operational cost on the same test data; do not
provision AI Search merely because it exists. It incurs service costs and is
not open-source application code.

### E. Reuse across investigations

The researcher selects which past investigations to use. Research workers
retrieve evidence and claims from the selected scope, not every piece of
prior research by default. Keep a trace of what was retrieved and used, and
show the original evidence. Define how deleted or corrected sources affect
later findings before implementation.

## 4. How an investigation runs

1. The API persists the research objective, selected model pool, sources,
   limits, uploaded files, and clarification answers.
2. The lead agent proposes its understanding and receives user confirmation.
3. The application starts a durable Temporal workflow for the investigation.
   The lead decomposes the objective into tasks; specialists are created
   dynamically where useful. Specialists receive bounded tools and selected
   models, not general Azure subscription credentials.
4. Activities search public sources, process files, query the company brain,
   run analysis in isolated sandboxes, and persist findings and artifacts.
   Reviewer agents independently check important claims where appropriate.
5. Durable application events update the researcher interface. The live chat
   is processed independently of ongoing work: questions can be answered and
   new instructions or files can trigger task changes without restarting the
   entire run.
6. On pause, failure or completion, the system retains accepted state and
   provides the current report. Recovery resumes safely when possible.

### State and event mechanics

- Persist accepted user messages and objective changes before acknowledging
  them. Record received, applied, rejected, or failed processing states.
- Use a normal HTTP request to send messages and commands, plus a server-to-
  client event stream for progress. Persist ordered events and replay from a
  cursor on reconnect; make duplicate events harmless.
- A durable coordinator receives changes and schedules work asynchronously.
  Keep model calls and external operations in activities, not deterministic
  workflow logic. Divide long work into bounded, restartable steps.
- Treat retries and delivery as potentially at-least-once. Use operation IDs,
  idempotency where supported, and reconciliation for ambiguous external
  side effects. Do not promise exactly-once billing or execution.
- Keep Temporal workflow history bounded using appropriate child workflows
  and continuation patterns. Store large files and payloads outside workflow
  history.

### Agent runtime and Temporal integration

Evaluate AgentScope 2.0 first for runtime-created specialist teams, with
LangGraph / Deep Agents as a comparison. The proposed pattern uses bounded
research-agent activities, with Temporal controlling the durable run and
the application storing canonical research state. The AgentScope/Temporal
integration is custom and untested; wrapping a long-running agent call does
not automatically make its intermediate state recoverable.

If LangGraph is selected, do not make the baseline depend on Temporal's
LangGraph plugin without testing: its integration is documented as public
preview and has specific store and streaming restrictions.

Evaluate whether OpenScientist's application and research loop can be reused
instead of rebuilding them. Its inspected behavior does not establish all of
the required team, steering, enterprise-memory, and recovery features.
AgentScope is a comparison candidate for runtime specialist creation. Select
based on a focused prototype, not by framework popularity.

## 5. Azure decisions and trade-offs

### AKS: not for the initial proposal

Use Azure Container Apps for the web app, API, and ordinary workers initially.
AKS offers greater Kubernetes control but also adds cluster, node, upgrades,
networking, and operational work. Revisit AKS if a validated requirement needs
its scheduling, isolation integrations, GPU fleet control, or workload scale.

This is not a claim that Container Apps automatically satisfies every
Temporal, concurrency, or sandbox requirement. Prove private service
communication, scaling, worker recovery, and durable coordination in an
Azure prototype. Do not expose the Temporal service to the public internet.

### Code and compute: separate from application hosting

Use Azure Container Apps Sandboxes as the first candidate for dynamically
created isolated code workspaces. Microsoft's documentation describes
microVM isolation, snapshots, sandbox lifecycles, and controlled egress.
Verify current release status, region availability, quota, pricing, SDK
compatibility, package installation, and long-running behavior.

Sandbox outbound access is unrestricted without a policy; configure egress
deliberately. Keep Azure control-plane credentials out of generated code.
An independent compute broker authorizes and audits resource creation using
scoped identity and enforced limits. Sandboxes receive only task-specific
access.

For GPU or larger scientific workloads, evaluate a separate Azure Batch/VM
backend behind the same compute interface. The documented sandbox resource
tiers do not establish GPU support. Dynamic provisioning, recovery, cleanup,
quota failures, and charges must be tested. No claim is made that the first
prototype already supplies all GPU or scientific-computing requirements.

### Cosmos DB: not the initial canonical database

Choose PostgreSQL initially because the application has related,
transactional records and benefits from SQL joins and a simpler combined
deployment with Temporal. Use Azure's AGE and pgvector extensions only after
checking compatibility with the chosen PostgreSQL version.

Cosmos DB for NoSQL remains a valid alternative for a proven need for its
distributed-document model, throughput, or multi-region characteristics. Its
partitioning and transaction scope require a different data model; it should
not be added merely because the data is generated by agents. Revisit the
decision with measured workload and cost data.

If the selected knowledge engine uses Cassandra, Azure Managed Instance for
Apache Cassandra and the Cassandra API of Cosmos DB are additional backend
candidates. They are different services; the latter is a compatibility
layer. TrustGraph compatibility, costs and operating behavior are unverified.

### Foundry: yes for models; managed agents are optional

Use Azure-hosted model deployments and an adapter so the researcher can
choose an allowed model pool. Foundry's model endpoint is not the same as
Foundry Agent Service: using the former does not require making the latter
the system's orchestration backbone.

Foundry's web grounding is a candidate for public search and can return cited
results. It has usage charges and documented data-boundary terms. Search
grounding alone is not a complete crawler, PDF reader, scientific database,
or company brain; validate direct page access, source capture, supported
models, availability, and citation behavior. Add explicit page/scientific
source adapters where needed, subject to source terms.

## 6. Identity, permissions, and safety

- Support personal and organizational Microsoft accounts, but allow access
  only to accounts approved by the installation owner.
- Investigations are visible to signed-in users by default. The precise
  control and deletion rights across researchers remain to be confirmed.
- Enforce authorization in application APIs, retrieval, Blob access, event
  streams, graph expansion, and artifacts—not merely by hiding UI buttons.
- Use separate scoped identities for the application, search/indexing,
  compute broker, and any sandbox access. Do not grant the model a raw
  subscription-wide credential.
- Handle prompt injection, harmful or unauthorized actions, SSRF, unsafe
  package sources, network exfiltration, and escaped jobs as explicit threat
  scenarios. Guardrails reduce risk but do not guarantee legal compliance.
- No runtime or spending cap is enabled by default, per the user's choice.
  Show cost estimates and warnings; when enabled, spending limits are
  best-effort because provider billing and in-flight work may be delayed.

## 7. Deployment and GitHub

Propose infrastructure in Bicep and compile the public release template to
ARM JSON for the Azure portal's Deploy to Azure button. The adopter selects
the subscription and region, reviews a cost estimate and required permissions,
approves provisioning, and follows a post-deployment setup/health-check flow.

The button is not proof of a fully automatic installation: identity app
registration and consent, model deployment and quota, service availability,
role assignment, search configuration, image access, and infrastructure
errors must be handled and tested. Offer clear guided fallback steps rather
than hiding failures or claiming literal zero-touch deployment.

Publish the application as open source with pinned dependencies, license and
notice inventory, documentation, tests, accessible UI, security policy,
dependency and secret scanning, container build, and documented upgrades.
Review the existing market study before publication. Do not publish uploads,
secrets, live resource identifiers, or runtime-generated data.

## 8. Proof-of-concept gates before committing to the stack

1. **Brain:** ingest a public source and uploaded PDF/CSV; extract an entity,
   link a claim to its exact source, represent contradictory evidence, and
   retrieve only selected investigation data. Edit and delete a source and
   show how derived search/graph state changes.
2. **Live steering:** while a specialist is working, send a chat message and
   change the objective; persist the revision, update affected tasks, and
   continue unrelated work. Reconnect and verify event replay.
3. **Durability:** interrupt a worker during a tool call and verify state
   recovery, safe retry behavior, and visible ambiguous external side effects.
4. **Azure hosting:** demonstrate private Temporal networking and worker
   communication on the proposed hosting. If unsuitable, compare an
   alternative such as Azure Durable Functions or a different Temporal host.
5. **Sandbox:** run generated code and install a package in an isolated
   environment, exercise allowed and blocked egress, persist artifacts,
   suspend/resume where supported, and verify cleanup. Separately test a
   candidate GPU/heavy-compute backend.
6. **Model and web access:** select model deployments from a user-controlled
   pool, change the pool during a run, search the public web, capture source
   references, and surface unsupported models or access/charging limitations.
7. **User and deployment:** support the agreed Microsoft account types and
   owner approval, deploy to a clean Azure subscription using the published
   flow, and validate sign-in, model availability, Blob access and health.
8. **Operational scale:** establish workload-specific targets before load
   testing; measure concurrent agents, model throughput, costs, retries,
   database/index behavior, and useful research progress. Do not infer
   performance from vendor maxima or framework claims.

## 9. Sources and verification notes

- [Azure container options and AKS](https://learn.microsoft.com/en-us/azure/aks/compare-container-options-with-aks).
- [Azure Container Apps Sandboxes](https://learn.microsoft.com/en-us/azure/container-apps/sandboxes-overview)
  and [sandbox egress policies](https://learn.microsoft.com/en-us/azure/container-apps/sandboxes-egress-policies).
- [Azure Batch best practices](https://learn.microsoft.com/en-us/azure/batch/best-practices).
- [Azure PostgreSQL Apache AGE](https://learn.microsoft.com/en-us/azure/postgresql/azure-ai/generative-ai-age-overview)
  and [pgvector](https://learn.microsoft.com/en-ca/azure/postgresql/flexible-server/how-to-use-pgvector).
- [Azure AI Search hybrid search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)
  and [cost considerations](https://learn.microsoft.com/en-us/azure/search/search-sku-manage-costs).
- [Azure Cosmos DB partitioning](https://learn.microsoft.com/en-us/azure/cosmos-db/partitioning).
- [Foundry model API](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)
  and [web search and its terms](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/web-search).
- [Temporal self-hosting](https://docs.temporal.io/self-hosted-guide),
  [Temporal PostgreSQL visibility](https://docs.temporal.io/self-hosted-guide/visibility/postgresql),
  and [LangGraph integration status](https://docs.temporal.io/develop/python/integrations/langgraph).
- [Docling](https://github.com/docling-project/docling) and
  [LangGraph license](https://github.com/langchain-ai/langgraph/blob/main/LICENSE).
- [Deploy to Azure button](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-to-azure-button).

Documentation was reviewed for this proposal; none of these services or
integrations was tested in the user's subscription. Pricing, region
availability, preview status, and quotas must be checked again before
deployment.
