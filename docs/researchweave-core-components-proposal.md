# ResearchWeave: core components proposal

Status: architecture discussion draft. Recommendations are starting points
for integration tests, not claims that the whole system already works.

The [product specification](research-system-specification-draft.md) defines
the desired behavior. The [company brain proposal](researchweave-company-brain-proposal.md)
covers knowledge-engine and graph comparisons separately.

## 1. Overall system

```text
Researcher / research workspace
    |
    | chat, progress, evidence, steering
    v
Application API + identity + event history
    |
    v
Durable investigation coordinator  <---->  Company brain
    |
    +-- Lead research agent
    |     +-- dynamically created specialist agents
    |     +-- independent reviewer agents
    |
    +-- Model adapter -> Azure-hosted model pool
    +-- Web/science tools -> public sources and user links
    +-- Document/data tools -> PDFs, text, spreadsheets, CSV
    +-- Compute broker -> isolated code workspaces / heavier compute
    |
    +-- Durable research state, evidence, artifacts, and reports
```

Core components must communicate without making the chosen framework or
cloud service the sole owner of research evidence and user-visible history.

## 2. Research application: reuse an existing base first

### First evaluation: OpenScientist

[OpenScientist](https://github.com/openscientist-io/openscientist) is an
Apache-2.0 research application with a discovery loop, research-state
concepts, reports, an interface, and Azure-related provider code. Evaluate
running and extending it before building the full research application from
scratch.

The inspected path uses one primary agent session per job. Immediate steering
of a running iteration, dynamic teams, broad cross-domain research,
enterprise-scale memory, and long-duration recovery were not established by
the market study. It may be a reusable application base, a source of
particular code or patterns, or a comparison baseline; do not assume it
already integrates with the other recommendations.

Compare its interface and execution capabilities with
[Agent Zero](https://github.com/agent0ai/agent-zero) and
[OpenHands](https://github.com/OpenHands/OpenHands) where their existing
execution and UI features could reduce custom work. Review each component's
license and host/service requirements before reuse.

### ResearchWeave-specific work

Whether extending an application or building its missing pieces, provide the
confirmed multi-user sign-in, English/Hebrew UI, selected model pool,
per-investigation Blob storage, live lead-agent chat, user-directed objective
changes, connected evidence, and accessible deployment. Do not fork an
application merely to preserve a UI that prevents these behaviors.

## 3. Agent teams and research behavior

### First evaluation: AgentScope 2.0

[AgentScope 2.0](https://docs.agentscope.io/en/versions/2.0.11/deploy/agent-team)
is the first candidate for dynamic research teams. Its documented team
mechanism lets a lead agent create and coordinate worker agents; the market
study inspected runtime-generated role descriptions and initial tasks.
Its core is Apache-2.0.

This is a better initial match for dynamically created specialist roles than
assuming a fixed workflow provides that behavior automatically. It does not
establish unlimited recursive delegation, scientific correctness, or
production-scale research. In the inspected implementation, tool permissions
and other settings come from developer-controlled templates, and model
settings are inherited from the session. The user-selected model pool and
per-agent assignment therefore need an explicit integration and tests.

### Alternative: LangGraph / Deep Agents

The [LangGraph library](https://github.com/langchain-ai/langgraph) is MIT
and is a strong alternative for stateful agent graphs, fan-out and
interrupts. ResearchWeave would still need to establish how genuinely
runtime-created specialist roles, distributed coordination, nonblocking
steering, and model-pool selection work. The MIT library is distinct from
the separately licensed Agent Server.

Do not install both frameworks merely because both are popular. Select the
runtime based on the same research and live-steering tests.

### ResearchWeave-specific work

Implement or adapt the scientific investigation loop: clarify a goal,
develop and revise research directions, request useful specialists, gather
evidence, propose and test hypotheses, independently review important
findings, and maintain an evidence-backed research record. Agent personas
or a growing task count alone do not prove scientific progress.

## 4. Durable investigation coordination

### First evaluation: self-hosted Temporal

[Temporal](https://docs.temporal.io/self-hosted-guide) provides an
open-source durable workflow server and SDKs. Use it as a candidate for
persisting investigation lifecycle, dispatching bounded work, handling
signals from the live UI, retrying failed steps, and resuming work.
Temporal is not an autonomous scientist and does not replace the company
brain.

Proposed integration: the durable coordinator manages deterministic workflow
state and schedules bounded activities that invoke the chosen agent runtime.
Persist checkpoints and outputs outside long-running model calls as needed.
Live messages become durable commands; independent workers can continue
while the coordinator handles steering.

This AgentScope/Temporal integration is **custom and untested**. A generic
long-running agent call is not automatically resumable because it is wrapped
in a Temporal activity. Design step boundaries, cancellation, state
persistence, heartbeats where appropriate, and retry behavior explicitly.
External effects may occur more than once unless the destination supports
idempotency; show ambiguous outcomes and reconcile them.

Temporal's documented LangGraph plugin is in public preview and has
limitations. Do not make the baseline rely on it without a separate
compatibility test. Temporal's private networking, service deployment,
database setup, upgrades, and operating costs on the chosen Azure host also
require a proof of concept.

### Azure-managed alternative

Compare [Azure Durable Functions](https://learn.microsoft.com/en-us/azure/durable-task/common/durable-task-orchestrations)
if self-hosting Temporal makes deployment or operations unnecessarily
complex. The trade-off includes Azure coupling, runtime behavior,
durability, operational simplicity, and compatibility with the chosen agent
runtime. Do not run both orchestration systems without a demonstrated need.

## 5. Live interface, chat, and steering

### Starting proposal

Evaluate the existing application UI first. If it cannot meet the interaction
requirements, build or extend a React/TypeScript interface and a
Python/FastAPI application layer. The UI presents a clean overview, with
expandable tasks, agents, evidence, history, and settings. It supports
English and Hebrew, including right-to-left layouts.

Use the [AG-UI protocol](https://github.com/ag-ui-protocol/ag-ui) as a
candidate for standard agent-to-UI events. It is an event protocol, not a
database, research application, or durable message queue.

### How live interaction works

1. Persist an incoming message or instruction with its research run and
   acknowledge receipt.
2. Deliver a durable command to the coordinator. A normal question does not
   automatically change the objective.
3. The lead agent responds and, when needed, changes the investigation plan
   or objective in the same run. Record objective versions and affected tasks.
4. The coordinator decides which affected work to continue, adjust or stop;
   unrelated workers continue. Honor configured human-approval settings.
5. Stream persisted progress and decision events to the browser. Reconnect
   using event identifiers, replay missed events, and handle duplicates.

The system must distinguish message received, processed, applied, rejected,
and failed; it must not claim a direction change occurred before it is
actually applied. Independent research continues while chat is processed
where technically possible.

## 6. Models and internet research

### Models

Use Azure-hosted model deployments through a provider adapter. The
researcher chooses the permitted pool and can change it during a run;
the system assigns suitable models from that pool to agents. Define what
happens to calls already in flight and unavailable or rate-limited models.

Verify model support for required tool calls, structured output, streaming,
embeddings, regions, quota, and pricing. Azure-hosted model access does not
require using a managed agent product as the orchestration backbone.

### Public research

Evaluate Azure/Foundry web search as one source-discovery tool. Also provide
a controlled reader/fetcher for user-supplied public links and appropriate
scientific sources, such as a selected literature API. A cited web-search
answer is not equivalent to ingesting the original full paper or dataset.

Record source URLs, capture/version information, extraction status, and
citations. Respect provider terms, paywalls, rate limits, and authorization.
Foundry web grounding has separate data-boundary and usage terms; account for
them in setup and documentation.

## 7. Files, analysis, and isolated compute

### Ingestion

Use Azure Blob Storage for a separate container per investigation. Evaluate
[Docling](https://github.com/docling-project/docling) for parsing PDF and
other document types, together with appropriate spreadsheet/CSV tooling.
Keep original files, tables and numerical data accessible with provenance;
do not reduce every dataset to text embeddings.

Docling's code is MIT, but its model artifacts can have separate licenses.
Document extraction, OCR, figures, tables, equations and Hebrew/English
quality require tests.

### Isolated code execution

Evaluate [Azure Container Apps Sandboxes](https://learn.microsoft.com/en-us/azure/container-apps/sandboxes-overview)
for isolated agent-created code and tools. Configure network egress rather
than relying on defaults, and keep cloud-management credentials out of
sandboxed code. Use a separate, scoped compute broker for resource requests,
auditing, limits, and lifecycle cleanup.

User-authorized agents can create tools and install appropriate packages
inside their workspaces. Public web access must remain possible through
appropriately controlled tools and network policy. Evaluate
[OpenSandbox](https://github.com/opensandbox-group/OpenSandbox), whose core is
Apache-2.0, as an open-source alternative; its Azure backend and isolation
deployment must be validated rather than assumed.

Heavier CPU or GPU jobs require a separately evaluated backend, for example
Azure Batch/VM compute, behind the same controlled interface. Model
availability, region, compute quota, costs, and dynamic provisioning are
real constraints.

## 8. Reports, observability, security, and deployment

- **Reports:** maintain an explicitly incomplete live draft; generate PDF,
  Word, and Markdown/text with citations, charts, equations and artifacts as
  appropriate. Test Hebrew, right-to-left text and mathematical rendering.
- **Research history:** persist the user-facing event timeline and evidence
  as application data. Azure Monitor/Application Insights and tools such as
  Langfuse are operational observability candidates, not substitutes for the
  research record.
- **Identity:** support approved personal and organizational Microsoft
  accounts; multiple researchers share an installation, and investigations
  are visible by default. Control/deletion rights still require clarification.
- **Secrets and permissions:** use scoped identities, avoid committing
  secrets, and enforce authorization for APIs, data, graph traversal and
  artifacts. Follow source licenses and respect access restrictions.
- **Deployment:** propose Bicep compiled to an ARM JSON template for the
  Azure portal deploy button, followed by guided identity, model, quota and
  health setup. Validate feasibility rather than promise zero manual steps.
  Provide costs and require explicit provisioning approval.

## 9. Cross-component integration gates

1. Use a source and an uploaded dataset to start an investigation. Confirm
   the lead can create a previously unspecified specialist, assign a model
   from the user's pool, and obtain source-linked evidence.
2. While a worker is active, ask the lead a question, upload new data, and
   change the objective. Confirm affected work adapts and unrelated work
   continues; reconnect and recover the event timeline.
3. Interrupt a worker and a tool invocation. Confirm durable recovery,
   visible ambiguous effects, and safe retries without claiming universal
   exactly-once execution.
4. Run generated code and install a package inside an isolated workspace.
   Verify access restrictions, evidence/artifact persistence, network
   controls and cleanup.
5. Exercise the company brain's evidence, contradiction, scope, deletion,
   indexing and scale gates on the same workload.
6. Produce a cited report in the requested language and formats. Validate
   Hebrew/RTL, charts, equations, and truthful partial-results behavior.
7. Deploy to a clean Azure environment; verify sign-in, model availability,
   graph/queue connectivity, Blob uploads, safe identities and health checks.
   State every manual prerequisite and charge.

No Azure testing, model deployment, or project implementation has been
performed yet. Agree on representative workloads and cost approval before
running large tests.
