# Autonomous Scientific Research Systems on Azure

## Source-verified market and open-source research

**Study date:** November 14, 2026  
**Purpose:** Identify reusable systems before choosing an architecture.  
**Validation performed:** Public documentation, papers, repository metadata, current licenses, and selected implementation paths. No candidate was installed, benchmarked, or deployed to Azure in this study.

## Executive findings

**A substantial amount of the required software exists. I could not verify a single open-source product that delivers the full requirement as an integrated, production-proven system.**

The strongest findings are:

1. **Start by evaluating existing applications.** OpenScientist, Asta, and Mimosa-AI deserve examination before implementing a new research loop. Agent Zero and the OpenHands SDK/Agent Canvas deserve separate evaluation as general execution/UI substrates. Their limitations differ: domain scope, host dependence, sequential execution, enterprise memory, or unproven long-running behavior.
2. **Runtime creation is real, but bounded.** AgentScope 2.0 contains inspected code that lets a leader write new specialist roles and initial tasks at runtime. That is not merely routing between fixed agents. Capabilities still come from developer-controlled templates and inherited settings.
3. **The company brain needs a separate evaluation.** TrustGraph, Graphiti, Cognee, and LightRAG offer different combinations of ontology, temporal knowledge, provenance, retrieval, and access controls. None of their reviewed benchmarks establishes reliable operation over an entire large organization's evolving experimental knowledge.
4. **Multi-day operation is an execution/recovery problem as well as an agent problem.** Temporal is a strong open-source durability candidate. LangGraph is useful, but its MIT library must not be confused with the separately licensed production Agent Server. Neither is an autonomous scientist by itself.
5. **The live research interface is not solved by a tracing dashboard.** A useful interface must explain current work, evidence, explored directions, and failures, and accept redirection while other work continues. AgentScope and OpenScientist provide relevant application behavior; AG-UI provides an event interface, not the complete research product.
6. **Azure is feasible to investigate without choosing an Azure-native proprietary agent platform.** Provider adapters and standard deployment building blocks exist. Actual Azure compatibility remains a prototype test, especially for strong sandbox isolation, model APIs, and external scientific services.
7. **License and maintenance checks changed the shortlist.** Public source or an OSS SDK did not imply an open production system. Examples include the Discovery app, LangGraph Agent Server, some memory-service servers, and enterprise-only connector permissions. Some previously popular repositories are now archived or marked unmaintained.

**Recommended decision now:** approve a small set of evidence-driven component and application trials, not a final architecture. The practical shortlist and pass/fail experiments are in Sections 11-12. This report does not select Kubernetes, a graph database, an agent framework, or a model as the final platform.

## 1. Requirements used in the research

The target is not a document chatbot, a fixed sequence of specialist agents, or an ML paper generator alone. It is an autonomous research organization implemented in software:

- Accept an open-ended objective in different fields, including electrical engineering, chemistry, and biology.
- Investigate using both existing organizational knowledge and current internet sources.
- Work with heterogeneous on-premises and cloud sources, not just uploaded PDFs.
- Create or adapt subtasks, specialist agents, analysis tools, and workflows during execution.
- Scale to hundreds or thousands of agents/tasks where the investigation justifies it.
- Retain connected, reusable knowledge across investigations: entities, relationships, provenance, ontology, uncertainty, and historical changes.
- Operate unattended for at least 48 hours and potentially ten days.
- Show progress, directions explored, findings, failures, and supporting evidence through a live interface.
- Accept natural-language questions and redirection without requiring the user to manage every worker.
- Run the system on Microsoft Azure, with open-source code preferred.

No particular Azure service, corpus size, initial research domain, team size, or spending ceiling has been selected. Open-source application code is distinguished from open model weights: the latter is a separate choice, not assumed by this study.

The initial scope is computational investigation and research proposals. Physical experimentation is not assumed to be available merely because an agent can write a laboratory plan.

## 2. How to interpret the evidence

Four evidence levels are used:

1. **Implementation inspected:** Relevant source paths or actual license text were inspected. This is not a successful execution test.
2. **Documented:** The maintainer documents a capability, configuration, or limitation.
3. **Reported result:** A vendor or paper reports an experiment or benchmark. Its workload and limitations still matter.
4. **Unverified:** A claim, compatibility assumption, or required capability was not established.

Important distinctions:

- A public GitHub repository is not necessarily licensed for reuse.
- An MIT SDK does not make its proprietary server open source.
- A configurable concurrency default of one is not a hard limit of one.
- A thousand tasks created over ten days is not a thousand simultaneous tool-using agents.
- Persistent conversation history is not durable recovery of external side effects.
- A temporal knowledge graph is not proof that its extracted statements are scientifically true.
- A local installation command does not establish a production-ready Azure deployment.
- Lack of published evidence is not proof that a system cannot scale.

The comparison deliberately avoids a single numerical score: the candidates solve materially different problems, and no common benchmark measures the complete requirement.

## 3. What the current research does and does not establish

### 3.1 There are reusable scientific applications, not just frameworks

Several projects already implement substantial portions of the investigation loop. OpenScientist, the Asta ecosystem, Mimosa-AI, RD-Agent, Biomni, and other projects below are more relevant starting points than implementing every research behavior from scratch.

However, no reviewed open-source system supplied verified evidence for the entire combination of:

**cross-domain discovery + massive enterprise knowledge + runtime specialist creation + hundreds/thousands of useful agents + ten-day unattended execution + a live, steerable research interface.**

That is a scoped finding from the reviewed evidence, not a claim that no such system exists anywhere.

### 3.2 The difficult gaps are not all model-reasoning gaps

The recurring gaps are:

- Keeping authoritative measurements separate from generated hypotheses.
- Maintaining permissions through retrieval, graph expansion, summaries, caches, and subsequent reuse.
- Incrementally correcting a large, changing corpus without leaving stale conclusions.
- Recovering work after failures without repeating costly or destructive operations.
- Evaluating scientific progress rather than the amount of generated text.
- Making a long-running investigation understandable and steerable.

### 3.3 More agents must be justified empirically

Google Research evaluated 180 agent configurations and found benefits on parallelizable tasks but degradation on sequential tasks. Anthropic's production research write-up similarly describes strong breadth-first research results alongside substantially greater token consumption and coordination problems. These are reasons to support adaptive concurrency, not to assume that 1,000 agents are inherently better. [S1][S2]

Anthropic's separate 1,000-agent mathematics experiment is useful evidence of large-scale coordination, but it had a formal checker, supplied workers and infrastructure, and a restart around hour 18 before completion at 28.7 hours. It is not evidence that a downloadable scientific platform can run any enterprise problem for ten days. [S3]

## 4. Existing scientific and research applications

### 4.1 Main comparison

| Candidate | Actual reusable capability | Dynamic behavior | Existing-knowledge and interface coverage | Important boundary |
|---|---|---|---|---|
| **OpenScientist** | Runnable research application with iterative jobs, a web interface, feedback, reports, budget-related controls, and structured research state | Iterative discovery loop with session resets; one primary agent session per job in the inspected path | Research-state modules cover hypotheses, findings, literature, analysis, and feedback; UI paths include chat, timeline, iterations, and feedback | Biomedical emphasis despite domain-agnostic positioning. Enterprise-wide knowledge ingestion, thousand-agent coordination, and ten-day operation were not demonstrated |
| **Ai2 Asta ecosystem** | Literature/data research tools, plugins, and runtime-planned work items | The assistant plans, executes, reviews, and saves work; the inspected plugin loop is sequential inside a host agent | File/git-backed mission and work history; artifacts and a local indexed library | Plugins, AutoDiscovery, Theorizer, and benchmarks are separate components. Do not combine their features into an imaginary single turnkey product |
| **Mimosa-AI** | Scientific workflows generated from a task, with MCP-provided tools | A workflow factory writes and assembles task-specific workflow code | Bioinformatics/metabolomics examples and workspaces; CLI-oriented interaction | Small, domain-focused project. Generated workflow correctness, companion-service licensing, enterprise ACL, and long-duration behavior need testing |
| **Microsoft RD-Agent** | Research/development iteration, code execution, evaluation, trace management, checkpoint/resume, and a UI | Research-development loops and configurable parallel traces | Optional knowledge base and trace inspection | Demonstrations focus on data science, quantitative finance, model training, and optimization, not general chemistry or electrical engineering |
| **Biomni** | Extensive biomedical tool, data, software, and MCP integration | Inspected A1 path is a generate/execute loop, not a first-class distributed agent organization | Custom data/tools/software can be registered; Gradio interface | Biomedical scope; inspected memory is in-process; execution environment needs additional isolation. Some bundled data has commercial-use restrictions |
| **EvoMaster** | Scientific-agent playgrounds and run-local adaptation/skills | Parallel copies and some conversational orchestration; not equivalent to unrestricted new specialist organizations | MCP/skills and example research presets | Materials preset depends on external Bohrium services and other cloud dependencies. Portability cannot be inferred from Apache-licensed framework code alone |
| **DeepScientist** | Hypothesis/verification/analysis loops, per-project findings memory, and a web studio | Long-horizon optimization within a research quest | Local project state and human takeover interface | Evidence is primarily AI/ML optimization. Reported long timelines were not independently reproduced here |

Primary repositories: [S4]-[S11].

### 4.2 OpenScientist: closest application-shaped prototype candidate

OpenScientist deserves hands-on evaluation because it exposes much of the user experience requested here, rather than only a Python agent API.

At inspected commit `6899fb0f706b3cbe5f141c920a7232b66c3f4fdc`:

- The code license is Apache-2.0.
- The README provides a launch command that starts its application stack.
- Research-state source files include `KnowledgeState`, database-related state modules, and migrations.
- UI source paths include job chat, feedback, timeline, and iteration views.
- The primary discovery loop iterates up to configured limits and periodically resets its session.
- The configurable `max_concurrent_jobs` default is one. That is a default, not a verified scalability ceiling.
- Provider modules exist for Azure OpenAI, Foundry, and other hosted/local providers. Their presence does not establish end-to-end feature parity.

This makes it a promising evaluation target, not a proven production selection. The knowledge-state/database relationship was identified statically; database recovery behavior was not exercised. Co-investigation feedback pauses between iterations in the inspected path; immediate steering of an executing iteration is unverified. [S4]

### 4.3 Asta: useful research process and auditable work products

At inspected `asta-plugins` commit `d1de6f03c1281f887802fce4c80703f5c1f874a1`, the assistant uses a mission document and work-item statuses to choose planning, execution, review, and saving operations.

Completed work is recorded with results and artifacts, indexed in a local work library, and committed when a Git repository is available. That is a concrete, inspectable method of retaining research work beyond a single context window.

But the inspected assistant plugin is not a distributed thousand-agent server. It depends on a host coding agent, and the licensing, authentication, and availability of that host and any remote literature services must be checked separately. A need-input state and repeated failures can stop its loop. [S5]

### 4.4 Mimosa-AI: relevant evidence for runtime-generated workflows

The inspected source contains `WorkflowFactory` and methods for generating prompts and workflow code, validating structure, assembling workflows, and saving the result.

This is substantively different from selecting among a fixed set of agent names. It is relevant to the requested behavior of deciding how to investigate a new task.

The root Apache-2.0 license was verified. The companion Toolomics service was not inspected to the same depth, so its licensing and complete deployment chain remain open checks. README claims about evolutionary workflow mutation were not validated by execution. [S6]

### 4.5 Relevant projects that should not be misclassified

| Project | Why it matters | Why it is not a ready answer |
|---|---|---|
| **AutoScientists** | A public example of agents organizing research around hypotheses, shared coordination, and relaunching workers | No license file was found at the inspected commit. Treat it as unlicensed public source, not open source cleared for reuse. Its BioML profile specifies 8-hour CPU / 16-hour GPU deadlines, not a verified ten-day run |
| **Sakana AI Scientist-v2** | Runnable hypothesis/experiment/analysis/manuscript pipeline | Primarily ML research; custom source-code license with use/disclosure conditions, not simply MIT or Apache |
| **SAGA** | Small-molecule and DNA-design examples; several autonomy modes | Fixed specialist roles and narrow demonstrated tasks |
| **Arbor** | Hypothesis-tree optimization, evaluation, and reuse of findings | Primarily tasks with an inexpensive, scorable objective; not demonstrated as an enterprise scientific knowledge system |
| **AutoSci** | Active research skills for coding-agent hosts | A skills package and host-dependent research workflow, not an independently established enterprise research platform |

These are useful comparison or reference projects, not evidence that the full target has already been solved. [S12]-[S16]

### 4.6 General-purpose systems that should not be overlooked

The absence of a built-in scientific benchmark is not a reason to ignore a useful general agent application. Two additional systems received bounded source inspection.

**Agent Zero**, inspected at `ba9b67df0f54ac78106ae85c552ef5d2458f7c9a`:

- MIT core, Docker/Linux workspace, and an existing web interface.
- A subordinate-agent tool creates or continues agents using named profiles.
- A bundled agent-creation skill can author new profile/prompt files, so specialist definitions need not all be written beforehand by a human.
- Code execution, plugin/skill creation, scheduled-task and goal functionality, and project-specific settings exist.
- Knowledge import and memory use FAISS-based vector storage and project/agent scoping in the inspected implementation.
- An Azure provider is listed for chat and embeddings through LiteLLM.

Important boundaries: automatic use of profile creation, deep delegation behavior, interruption semantics, and multi-day recovery were not exercised. Parallel tool execution is not proof of a parallel research swarm. No ontology, source-document ACL, or enterprise-wide permission model was found in the inspected paths. Plugins and connected files can have substantial execution/data access. [S17]

**OpenHands SDK and Agent Canvas**, inspected at main-repository revision `bca403840de709eea0584da19a288be3d705cdc9` and SDK revision `942deccf8a865ca04db54955ebefe1a5abd10f10`:

- The main repository and software-agent SDK have MIT licenses.
- The current main application is Agent Canvas; the SDK contains the execution engine and agent-server packages. Older descriptions of one monolithic repository are incomplete.
- The SDK supplies Task/Delegate tools, resumable task identifiers, file/code-defined specialist configurations, MCP, scientific-code-capable terminal execution, and per-agent iteration/budget settings.
- The inspected Delegate implementation has a configurable default of five children per delegating agent. That is not a platform-wide total-task ceiling.
- A UI, agent-server interfaces, and local/remote workspace paths exist.

Important boundaries: runtime self-authoring of a new specialist definition was not established; source-defined configurations alone do not prove it. Conversation-state files were found, but recovery semantics and enterprise knowledge management were not verified. Azure inference support was not specifically validated. The separate Enterprise repository uses PolyForm Free Trial terms, not MIT; enterprise multi-user features must not be assumed to be in the open application/SDK. [S18]

**Evaluation implication:** Agent Zero is a useful baseline for how much autonomous behavior and interface functionality can be obtained immediately from a general application. OpenHands is a useful baseline for tool execution, delegation, workspaces, and an extensible UI. Neither was verified as a ten-day, thousand-agent scientific platform or an enterprise company brain.

## 5. The "company brain": enterprise knowledge versus agent memory

### 5.1 These are different kinds of state

The requirement spans at least four distinct meanings of memory:

1. **Source evidence:** Reports, database records, raw measurements, files, web captures, and their versions.
2. **Organizational/scientific meaning:** Entities, identifiers, relationships, units, conditions, and domain schemas.
3. **Investigation state:** Tasks, dependencies, hypotheses, attempts, failures, decisions, and artifacts.
4. **Convenient agent recall:** Summaries and selected information retrieved into a worker's context.

A system that performs well on remembering conversations does not automatically solve the other three.

RAG is not inherently unable to handle large corpora. The harder issues are retrieval quality, multi-hop reasoning, global synthesis, access control, updates, and retaining the right evidence. Graph-based retrieval can help particular workloads, but it adds extraction, entity-resolution, update, and governance costs.

### 5.2 Knowledge-system comparison

| Candidate | Strongest relevant features | Important missing or unverified pieces | Code/license boundary |
|---|---|---|---|
| **TrustGraph** | Explicit ontology-oriented runtime; RDF/OWL/SHACL concepts; PROV-O document/page/chunk/edge lineage; query policy filtering | No verified enterprise-scale throughput result, temporal contradiction mechanism, or scientific-truth model. New policy features need testing; no policies means open mode | Apache-2.0 core; backend licenses vary |
| **Graphiti** | Incremental episodes, typed entities/relationships, temporal validity, contradiction-driven edge invalidation, provenance | Reference servers do not supply production authentication/authorization. Partition IDs are not source-system ACL. Large enterprise-corpus performance unverified | Apache-2.0 core; Zep's managed service is separate; graph backend choices have different terms |
| **Cognee** | Document/data graph pipeline, ontology grounding, dataset permissions, deletion, and some authoritative-source modeling | Dataset permissions are not automatically source-document ACL. Temporal semantics were not fully verified. Production Postgres graph functionality is identified as a licensed product | Apache-2.0 core; paid/hosted pieces and backend dependencies must be separated |
| **LightRAG** | Hybrid graph/vector retrieval, incremental ingestion, document deletion, entity editing/merging, and multiple storage options | No inspected per-document end-user authorization. Workspace isolation is not equivalent to enterprise ACL. No verified massive enterprise workload | MIT core; default file/in-memory stores are not production configurations |
| **OpenSPG/KAG** | Explicit schema modeling, schema-constrained extraction, logical-form-guided reasoning | ACL, correction/deletion, and temporal behavior were not sufficiently established. Slower inspected release cadence; deployment dependencies require review | Apache-2.0 KAG/OpenSPG; database/object-store terms are separate |
| **Microsoft GraphRAG** | Global sensemaking, entity/relationship extraction, community summaries, inspectable outputs | Not a complete memory platform. Maintenance-mode warning, no inspected end-user ACL model, and important update/delete limitations in the inspected path | MIT; hosted Azure dependencies remain services, not OSS code |
| **HippoRAG 2** | Reproducible associative-retrieval method and useful baseline; incremental/delete interfaces | Not an enterprise ontology/governance platform; no authentication in its reference HTTP MCP server | MIT |

Sources: [K1]-[K7]. These are candidate roles, not a selected combination or architecture.

### 5.3 Findings with direct consequences for the target

**Graphiti:** The inspected implementation preserves temporal edge history and can invalidate superseded edges. It also explicitly warns that its reference servers do not enforce authentication or authorization. Its graph-group isolation must not be presented as complete enterprise security. A historical fact changing over time is also not the same thing as determining which conflicting experiment is scientifically reliable. [K2]

**TrustGraph:** The strongest directly relevant features are ontology-guided extraction, detailed provenance, and per-node policy filtering before context assembly. The inspected policy path has an open mode when no policies exist. Whether all graph traversals, summaries, and tools preserve intended permissions at scale is an empirical test, not an established result. [K1]

**Cognee:** Dataset-level access controls and source-authority metadata are useful, but a dataset boundary can be much coarser than SharePoint document permissions or SQL row restrictions. Its documented production Postgres graph-store license boundary matters for an open-source-first system. [K3]

**LightRAG:** Document deletion and reconstruction of affected graph elements are materially useful. However, source deletion, extracted summaries, cached answers, and permission revocation must all be tested together; an API named `delete` alone is not proof of complete information removal. [K4]

**GraphRAG:** Its indexed outputs include Parquet tables; it does not inherently require a graph database. The inspected incremental-update path processes new documents but does not establish complete propagation of modifications and deletions. It is more appropriate as a retrieval/sensemaking method to compare than as the assumed whole-company memory system. [K6]

### 5.4 Conversation-memory products need separate treatment

Mem0, Hindsight, Letta, Supermemory, and MemOS were also considered. They are relevant to retaining agent/user interactions, but their results do not establish enterprise experimental knowledge management.

Examples of boundaries found:

- Current Mem0 documentation separates the OSS library from managed-platform features and benchmark optimizations. OSS APIs include updates and deletions, but the inspected extraction approach is ADD-oriented; that is not automatic scientific contradiction resolution.
- The old Letta server repository is archived; the current code-agent product and hosted offerings must not be confused with that historical server.
- Supermemory's public repository does not establish an open production memory server: its self-hosted server is documented as coming from a separate non-public codebase.
- Hindsight and MemOS are additional candidates, but they were not inspected deeply enough here to rank as the enterprise knowledge foundation.

Sources: [K8]-[K12].

### 5.5 What published benchmarks actually show

The evidence reviewed is much smaller and narrower than "all knowledge accumulated by a large organization":

- The LightRAG paper evaluates corpora around 0.6-5.1 million tokens, with 10-94 documents in its reported domain sets.
- The original GraphRAG work evaluates global sensemaking around million-token datasets.
- HippoRAG 2 reports corpora of approximately 4,000-23,000 passages.
- LongMemEval, LoCoMo, and BEAM primarily evaluate long conversational memory. A synthetic ten-million-token conversation is not a ten-million-document enterprise corpus.
- Some reported scores are for proprietary managed services rather than the publicly runnable code.
- Some comparisons use different metrics or judges; retrieval recall cannot be directly compared with final-answer accuracy.

These findings do not establish an upper limit. They establish that enterprise scale, update correctness, entity-resolution quality, and permission safety remain unproven for this workload.

The required scientific distinction also remains a product gap: a graph edge supported by a report must not automatically become equivalent to a calibrated measurement, a replicated result, or an established causal mechanism.

## 6. Enterprise ingestion and existing organizational information

### 6.1 Reusable ingestion software

| Project | What is reusable | Verified limitation or qualification |
|---|---|---|
| **Docling / Docling Serve** | Local document conversion and service deployment; offline model prefetch; structured document output | MIT code does not imply identical licenses for every model weight. Scientific tables/figures still need extraction-quality validation |
| **Unstructured / unstructured-ingest** | Apache-2.0 extraction and ETL code, local partitioning, source/destination connectors | Maintainer says OSS ingest CLI/library do not actively receive all hosted API feature additions. Its SharePoint connector explicitly excludes on-premises SharePoint |
| **Apache NiFi** | Apache-2.0 dataflow integration and database/file processing | A high-watermark SQL poller is not complete change-data capture or source permission synchronization |
| **Debezium** | Apache-2.0 database snapshots and row-level insert/update/delete events | SQL Server CDC must be enabled. Recovery can emit duplicate events, requiring downstream handling |
| **Onyx** | Actively maintained enterprise search application and connectors; MIT code outside enterprise directories | Source-permission synchronization and some group features are paid. Public connector mode can expose indexed private source documents to all application users |
| **Airweave** | MIT public connector/retrieval code; SharePoint Online delta/ACL documentation exists | The repository was archived when checked. SQL documentation pointed to implementation paths that were not found in the inspected tree |

Sources: [I1]-[I8].

### 6.2 Findings that affect any future implementation

**SharePoint Online and SharePoint Server are not interchangeable.** A connector named SharePoint may support only Microsoft's cloud service. The inspected Unstructured connector states that it does not support on-premises SharePoint. [I3]

**Old authentication examples can already be broken.** Microsoft states that Azure ACS authentication for SharePoint Online retired on April 2, 2026. A repository with an old example that still depends on it is not validated merely because it has a SharePoint logo. This retirement does not have the same scope for on-premises SharePoint Server. [I9]

**Synchronization is more than downloading new files.** It includes modifications, deletions, identity/group changes, permission changes, and removal from derived stores and caches. Microsoft Graph delta APIs provide useful mechanisms, but permission traversal has specific requirements. [I10]

**Raw measurements must remain usable as data.** Time series, images, simulation outputs, spreadsheets, and databases should not be assumed to become scientifically usable solely by embedding textual summaries. This is a scientific/data-modeling requirement rather than a feature claimed for a particular connector.

**Permission-aware ingestion is not the same as permission-aware derived knowledge.** If an agent combines evidence from several restricted sources into a finding, the resulting finding and its later summaries need an explicit access policy. None of the reviewed connector descriptions alone establishes that policy.

## 7. Commercial and managed systems: reference points, not OSS substitutes

| System | Why it remains relevant | Why it does not meet the open-source-first requirement by itself |
|---|---|---|
| **Kosmos / Edison Scientific** | Persistent research, code-writing, internal scientific data, subagents, and vendor-assisted deployments | Current commercial positioning is strongly biopharma-focused. No public licensed equivalent of the complete production platform was verified |
| **Claude Managed Agents** | Explicit runtime inline agents and generated multi-agent workflows; stateful execution environments | Managed/proprietary service. Simple child delegation is documented as one level and at most 25 child threads at a time; workflow runs are a distinct mechanism |
| **Microsoft Discovery** | Long-running objective-driven scientific planning and coordination, institutional knowledge, simulations, and research UI | Cloud engine is not supplied as OSS in the public app repository |
| **Google Co-Scientist** | Goal-driven hypothesis generation and refinement with multiple agents | Restricted preview; documented specialist roles; not a self-hostable OSS platform |
| **Google Antigravity /teamwork** | Recent reference for long-horizon science/engineering, fresh contexts, verification roles, and adaptive patterns | The reviewed November 13 announcement does not provide an OSS enterprise platform portable into the user's Azure subscription |

Sources: [C1]-[C6].

### Important correction: the Microsoft Discovery repository

The public `microsoft/discovery` repository is MIT-licensed, but its contribution documentation explicitly says the desktop application's source is not in that repository.

It contains catalog content, documentation, utilities, and installer links. A downloadable client, an MIT catalog, and an open-source cloud engine are three different things. The app requires a GitHub Copilot subscription for the documented experience. It should not be selected as a fully open-source base on the strength of the repository's license badge. [C4]

The current Discovery Bookshelf documentation also describes curated corpora and size tiers up to less than 1 GB of text per knowledge base, without incremental indexing. This is not an organization-wide storage limit for the whole platform, but it does limit the claim that Bookshelf alone is an automatically maintained enterprise brain. [C5]

## 8. Azure portability findings, without prescribing an architecture

Azure is not the principal conceptual obstacle. Several reviewed applications already expose Azure-related provider options, and standard Python services, Linux containers, databases, and worker services can be considered for Azure deployment.

However, the following must be distinguished:

| Question | What the research establishes | What remains to test |
|---|---|---|
| Model API portability | Azure OpenAI v1 supports the OpenAI client with an Azure endpoint | Tool-call schemas, structured output, token accounting, context handling, streaming, retries, and embedding compatibility for the selected project/model pair |
| Scientific compute | Ordinary containerized analysis can be evaluated on Azure compute | CUDA, GPUs, MPI, local disk, dataset licenses, external SaaS dependencies, and scientific-software licenses |
| Strong sandboxing | AKS documents Kata-based per-pod VM isolation | Exact node/OS/hardware support and the chosen sandbox project's compatibility |
| On-premises data | Existing connectors and database capture tools reduce custom implementation | Source-specific authentication, network routing, permissions, deletions, and SharePoint Server coverage |
| Very high agent counts | Model quotas distinguish token and request throughput | Useful active concurrency, rate-limit behavior, worker saturation, and coordination overhead |
| Open-source deployment | Many reviewed components have permissive core licenses | Paid server features, source-available databases, proprietary coding-agent hosts, model weights, and managed APIs |

Official AKS documentation requires Azure Linux for the inspected Kata feature, an appropriate generation-2 VM with nested-virtualization support, and documents restrictions including ARM64, FIPS/Trusted Launch combinations, and I/O considerations. A Docker-oriented sandbox should not be declared AKS-compatible without checking its actual execution backend. [A1]

The Azure OpenAI v1 API reduces some provider-specific client changes; it does not guarantee feature parity for every external agent project. [A2]

At hundreds or thousands of workers, inference rate limits can become the bottleneck before local agent-process capacity. Bursts can be rate-limited even when minute-average traffic appears below quota. [A3]

No Azure resources were created, no quota was requested, and no compatibility deployment was executed in this research.

## 9. Dynamic agents, durable execution, and sandbox operations

### 9.1 AgentScope 2.0: the clearest inspected runtime-specialist mechanism

AgentScope 2.0 is a particularly relevant runtime candidate because the leader's tool calls can create a team and new members during an investigation.

At inspected revision `27d8359`, the `TeamCreate` and `AgentCreate` paths allow a leader to supply a new member's name, role description, and first task. The description becomes part of that worker's system prompt. This is actual prompt-level specialist creation, rather than only selecting a predefined agent.

The boundary is equally important:

- Tool access, permission rules, working directories, and other settings are inherited or supplied by developer-defined templates.
- Model settings are copied from the session in the inspected path.
- The inspected organization is a leader with team members, not an unrestricted recursive hierarchy.
- Session-state persistence, a multiprocess message bus, cooperative steering, and a web UI example exist.
- Deterministic workflow replay, external-side-effect idempotency, and automatic recovery of a partially completed reasoning loop were not established.
- Background-task record retention in one inspected path is 24 hours; ten-day investigation/audit behavior needs explicit testing.

The source also suggests potentially increasing roster-lookup work as teams grow. That is a static-code concern, not a measured bottleneck.

The older AgentScope million-agent result must not be confused with current-code, thousand-worker scientific research. That paper used a short game, small numbers of model calls per agent, and a legacy actor/RPC code path. A separate very fast result used dummy model calls. Neither demonstrates a thousand concurrent, sandboxed, tool-using researchers retaining enterprise knowledge over days. [R1]

AgentScope Runtime has a maintainer notice that its capabilities have moved into AgentScope 2.0 and it is being superseded. It should not be evaluated as an independent new foundation without accounting for that migration.

### 9.2 Runtime and durability comparison

| Candidate | Verified useful behavior | Important limits | License/product boundary |
|---|---|---|---|
| **AgentScope 2.0** | Runtime-created member personas/tasks; team communication; app-server state and cooperative steering; web UI example | Durable journal/replay and interrupted-loop recovery unverified. Large current-code research workload not demonstrated | Apache-2.0 |
| **LangGraph / Deep Agents** | Stateful agent graphs, checkpoints, subgraphs/fan-out, interrupts, context compaction, and tool-output offloading | Node re-execution can repeat external effects. Some asynchronous subagent, multitasking, and server-notification features depend on Agent Server | MIT libraries; `langgraph-api` Agent Server is Elastic-2.0 with license/validation requirements in inspected docs |
| **Temporal** | Durable workflow execution, task queues, child workflows, signals/updates, cancellation, and OSS operational UI | Does not provide scientific reasoning or context management. Activities need idempotency. History growth and upgrades need design and tests | MIT server, SDKs, UI, and inspected AI integrations; Temporal Cloud is separate |
| **DBOS Transact** | Persistent workflow steps, queues, fan-out, rate/concurrency limits, messaging, and timeouts | OSS-only multi-executor recovery and all requested control behaviors were not fully established | MIT libraries; Conductor and Console are proprietary |
| **Microsoft Agent Framework** | Workflow checkpoints, external-input requests, events, and Azure/AG-UI/A2A integrations | Runtime-authored specialists beyond builder-defined paths and a complete distributed scheduler were not verified | MIT core; optional cloud stores/services remain separate |
| **CrewAI** | Multi-agent/flow abstractions and task-level checkpointing | Inspected writes are best-effort; complete distributed scheduling, cancellation, and budget control were not established | MIT core; managed offering assessed separately |
| **Restate** | Journal-based durable execution, parallel invocation, messaging, operational controls, and a UI | Not strictly open source under the current server license. AI workload scale remains unverified | MIT SDKs; BUSL 1.1 server with an additional-use grant and future conversion |

Sources: [R1]-[R7]. These are alternatives at different layers, not a proposal to deploy all of them.

### 9.3 Why "it has checkpoints" is insufficient for ten days

A research loop may fail after a tool has finished but before the result has been durably recorded. A retry can repeat an API call, generate another expensive simulation, or duplicate a data write.

The inspected LangGraph documentation explicitly discusses idempotency around interrupts and node replay. Temporal likewise requires external activities to be implemented with their delivery/retry semantics in mind.

Long-running execution also creates accumulating histories and checkpoints. Temporal documents per-execution history constraints and recommends appropriate child-workflow and Continue-As-New practices. Its guidance not to put more than 1,000 child workflows under a single parent is not a platform-wide limit of 1,000 workflows.

Temporal's existing AI integrations reduce integration work, but the inspected LangGraph integration is public preview and has limitations on supported checkpoint/store and streaming behaviors. It is not evidence that combining the two is automatically the best choice.

No reviewed open-source deployment supplied independently verified results for the complete ten-day scientific workload in this request. That conclusion does not dispute general durable-workflow use in other long-running applications. [R2][R3]

### 9.4 Sandboxes and dynamic compute provisioning

| Candidate | Existing mechanism | What is not established |
|---|---|---|
| **OpenSandbox** | Docker execution and Kubernetes-oriented control plane; pools; runtime isolation options; egress/credential controls | Production HA and thousand-sandbox research operation were not verified. One published warm-template admission test is only on a two-node cluster with 20 slots |
| **Kubernetes SIG agent-sandbox** | Sandbox custom resources, claims/templates/warm pools, identity/storage lifecycle, and delegation to isolation runtimes | A thousand-claims-per-second roadmap goal is not a measured result. It does not provide research planning or an evidence store |
| **E2B runtime / Embed** | Open runtime code, microVM execution and snapshots; useful sandbox APIs | Documented open Embed path is single-machine; a supported multi-node OSS deployment was not established. Hosted concurrency/runtime limits do not prove self-hosted performance |
| **Daytona public code** | Historical sandbox implementation | The inspected repository says core development moved to a private codebase and the public version is frozen/archived |

Sources: [R8]-[R11].

The OpenSandbox test is worth reading rather than quoting a headline latency: the documented 10-way test succeeded for 100/100 create attempts, while the 20-way test succeeded for 51/100, with rate-limit rejections and a timeout. That characterizes one configuration, not the system's ultimate capacity, and it is not evidence for 1,000 concurrent workers.

Provisioning an execution sandbox is different from authorizing arbitrary subscription-wide infrastructure changes. The reviewed software does not eliminate the need for externally enforced resource and identity boundaries.

### 9.5 Live progress, explanations, and natural-language steering

The requested interface has two distinct functions:

1. **Observe:** Show active tasks, dependencies, attempts, findings, sources, costs, failures, and changes since the last visit.
2. **Control:** Ask questions, change priorities, stop a direction, add evidence, and redirect selected work while unrelated workers continue.

Langfuse and Opik provide useful tracing/evaluation interfaces. They should not be mistaken for the complete research-control application. Langfuse's MIT core is also distinct from its enterprise features, including some governance and retention controls. Phoenix's main server license is Elastic-2.0; some client packages use different licenses.

AG-UI is an MIT-licensed event protocol with lifecycle, text, tool, state, activity, and subagent events. It can reduce front-end integration work, but it does not supply investigation persistence, replay, or scientific progress summaries.

The interface should expose observable actions, evidence, concise decision explanations, and uncertainty. It should not depend on obtaining a model provider's private internal chain-of-thought.

OpenScientist's application UI and AgentScope's team/steering functionality are therefore relevant prototype references alongside tracing tools, not alternatives to all observability. [R1][R12]-[R14]

## 10. License and maintenance findings that affect selection

This is a technical selection screen, not legal advice. Production licensing should be reviewed against the exact versions and intended distribution/service model.

| Finding | Selection consequence |
|---|---|
| OpenScientist, Asta plugins, Mimosa-AI, AgentScope, Temporal, and several graph/retrieval projects have permissive core licenses | They are credible code-reuse candidates, subject to complete dependency review |
| AutoScientists had no license in the inspected revision | Do not treat it as open source cleared for reuse |
| Discovery's public MIT repository does not contain the desktop app source | A downloadable app is not a forkable OSS base |
| LangGraph's MIT library differs from the Elastic-2.0 Agent Server | Decide whether to use the library, obtain server rights, or evaluate another runtime; do not assume all documented hosted/server features are in MIT code |
| Restate server is BUSL; Phoenix server is Elastic-2.0 | Treat as source-available alternatives, not equivalent to permissive OSS |
| Onyx source-ACL sync, some Langfuse governance, and other features are paid | A free local demonstration may not contain the security/operations features needed for enterprise use |
| Biomni datasets and Docling model weights can have different terms from their application code | Review the selected data/model artifacts, not just repository badges |
| Airweave and Daytona public repositories, and historical Letta/AutoGen server lines, have archival or maintainer discontinuation notices | Avoid selecting by an old blog post or star count; verify the exact active replacement |
| Supported graph/database backends include different license families | Graphiti/Cognee/LightRAG being permissive does not make every supported graph store permissive |

Inspected dependencies include permissively licensed options as well as GPL/AGPL, SSPL, BUSL, and proprietary services. These are not interchangeable legal categories. Redis licensing also varies materially by version. Some example stacks reference archived MinIO code or floating dependency tags.

Do not conclude that a component is unusable merely because it has copyleft terms; conclude that its obligations and the intended deployment/distribution must be understood. Likewise, do not call SSPL, BUSL, or Elastic-2.0 OSI open source.

## 11. Practical evaluation shortlist, not a selected architecture

These are candidates to test against specific requirements. They are deliberately not wired together into a proposed stack.

### A. Application-level trials

1. **OpenScientist:** Test the research UI, knowledge-state persistence, unattended execution, and ability to consume external organizational evidence. Closest reviewed application-shaped starting point, with early-project and biomedical-scope caveats.
2. **Asta:** Test whether its research tools and explicit work artifacts improve literature/data investigation and cross-investigation reuse. Separate host-agent dependence from the OSS plugin.
3. **Mimosa-AI:** Test runtime-generated workflow correctness and whether its mechanism transfers beyond the bundled scientific tools. Resolve companion-service dependencies first.

Run **Agent Zero** as a general-purpose application baseline and compare **OpenHands SDK/Agent Canvas** where execution/workspace extensibility is central. This prevents spending months rebuilding capabilities that are not unique to scientific agents. Their scientific and enterprise-knowledge gaps remain explicit.

### B. Dynamic-team and durability trials

4. **AgentScope 2.0:** Test actual runtime creation of new specialists and live steering. Explicitly measure leader overload, recovery, and side-effect handling.
5. **Temporal:** Test durable execution and messaging as an independent capability. It is a durability candidate, not an agent-science application.
6. **LangGraph / Deep Agents:** Test stateful agent behavior and context management while separating MIT-library capabilities from Agent Server features and terms.

### C. Company-brain trials

7. **TrustGraph:** Test ontology/provenance/policy functionality, including open-mode defaults and policy enforcement through graph expansion.
8. **Graphiti:** Test temporally changing facts, contradictory sources, source removal, and external authorization.
9. **Cognee or LightRAG:** Compare ontology/data-ingestion and retrieval/update behavior, with paid-feature and ACL boundaries visible.

RD-Agent and Biomni are useful domain-specific reference/tool candidates, not substitutes for the entire cross-domain system. HippoRAG 2, hybrid search, and conventional retrieval should remain comparison baselines rather than assuming graphs always win.

### What should not decide the shortlist

- Number of advertised agents.
- GitHub stars.
- A benchmark score from a different domain.
- An impressive demonstration with no code/license.
- A successful local launch without source-permission tests.
- A public SDK for a proprietary server.
- Ten days of uptime without evidence of useful scientific progress.

## 12. Experiments to complete before selecting an architecture

**These are proposed validation gates, not tests already run.** Thresholds and workload sizes need to be agreed using representative data; they are not vendor performance promises.

| Gate | What to exercise | Required evidence |
|---|---|---|
| Open objective | Give a goal without a prepared task graph | System-created task tree, changes after discoveries, clear stopping/uncertainty behavior |
| Runtime specialists | Require an unforeseen research subtask | Newly authored role/task, inherited permissions made explicit, no false claim that a predefined route is a new agent |
| Cross-source research | Combine reports, database records, raw data, and current web evidence | Correct entity joins, numerical results, provenance to exact source versions, conflicting evidence retained |
| Scientific correctness | Use held-out tasks from multiple domains | Reproducible calculations, expert-scored findings, negative/inconclusive results permitted, no reliance only on persuasive prose |
| Evolving knowledge | Modify, retract, and delete sources during an investigation | Correct propagation into graphs, retrieval, caches, summaries, and later investigations |
| Permission safety | Use synthetic departments and deliberately restricted sources | No restricted content or derived conclusions exposed through search, graph traversal, summaries, or artifacts |
| Fan-out | Progress from small teams to hundreds and, if justified, 1,000 active workers | Separate total agents, active agents, simultaneous model requests, sandbox counts, queue delays, and useful output |
| Failure recovery | Stop processes/services during analysis and external tool calls | No lost accepted findings; completed work recognized; external effects deduplicated; operator-visible failure state |
| Long soak | Run a representative 48-hour workload, then a ten-day workload | Memory/history growth, storage growth, recovery time, useful progress, context integrity, and error accumulation measured |
| Live interaction | Ask for a 48-hour summary and redirect a running branch | Source-backed progress summary; steering reaches intended work; unrelated work continues; reconnecting UI recovers events |
| Context pressure | Exceed ordinary context-window size | Original evidence retained; critical constraints survive summarization; findings do not silently become established facts |
| Resource governance | Trigger rate limits, retry storms, and resource exhaustion in a controlled environment | Bounded retries, persisted budgets/limits, graceful pausing/cancellation, sandbox cleanup |
| Azure portability | Run the chosen application/model/sandbox combinations on Azure | Actual end-to-end results, not just a Docker image or an adapter filename |
| Licensing | Inventory exact application, server, UI, database, model, and dataset versions | A documented, reviewable software/data/model bill of materials |

For domain coverage, the first evaluation should include at least distinct electrical/engineering, chemistry/materials, and biological data-analysis tasks. They should be computational or retrospective tasks with safe, reproducible evaluation, not unsupervised novel physical procedures.

Existing suites can provide part of the evidence:

- **AstaBench:** Broad scientific-agent evaluation across literature, code, data analysis, and discovery-related tasks.
- **ScienceAgentBench:** Scientific program-generation tasks derived from published work; useful but not a test of ten-day research.
- **CORE-Bench:** Reproducing computational results, not inventing new science.
- **GraphRAG/retrieval benchmarks:** Compare graph-based and non-graph retrieval on the same questions and evidence.

Historical benchmark scores must be attached to their model, scaffold, split, and grading method. Some use deterministic EM/F1 or execution tests; others use LLM judges. They cannot be treated as interchangeable measures of scientific validity. [S16][K7]

## 13. Research conclusion

The project is feasible to pursue as an engineering and scientific-validation program on Azure. There is enough existing code to avoid beginning with a blank agent loop, a blank document pipeline, or a blank graph engine.

The evidence does **not** justify claiming that assembling popular components already yields a general autonomous scientist with an enterprise brain.

The largest remaining product-level work is:

1. Connected enterprise evidence with trustworthy semantic meaning and source permissions.
2. A scientific investigation process that distinguishes observations, hypotheses, simulations, and established results.
3. Recoverable, bounded execution across long-running and dynamically created work.
4. A coherent user-facing research record and non-blocking natural-language steering.
5. Demonstrated quality and scale on the actual cross-domain workload.

The next step should be a bounded comparative validation of the shortlist, followed by architecture selection using the results. No final architecture, service sizing, implementation plan, or deployment commitment is prescribed by this report.

## Source register: scientific systems and research evidence

- **[S1]** Google Research, [Towards a science of scaling agent systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/).
- **[S2]** Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system).
- **[S3]** Anthropic, [Safely scaling multi-agent teams](https://claude.dev/blog/safely-scaling-multi-agent-teams-with-fable-5-2/).
- **[S4]** [OpenScientist, inspected commit](https://github.com/openscientist-io/openscientist/tree/6899fb0f706b3cbe5f141c920a7232b66c3f4fdc). Relevant paths: `LICENSE`, `README.md`, `src/openscientist/knowledge_state.py`, `knowledge_state_db.py`, `settings.py`, `orchestrator/discovery.py`, `providers/`, and `webapp_components/pages/`.
- **[S5]** [Asta plugins, inspected commit](https://github.com/allenai/asta-plugins/tree/d1de6f03c1281f887802fce4c80703f5c1f874a1); [Asta AutoDiscovery](https://github.com/allenai/asta-autodiscovery); [Asta Theorizer](https://github.com/allenai/asta-theorizer). Plugin loop: `plugins/asta-assistant/skills/run/SKILL.md`; persistence: `save-work/SKILL.md`.
- **[S6]** [Mimosa-AI, inspected commit](https://github.com/HolobiomicsLab/Mimosa-AI/tree/c9bbf0738cdffa6da351995698771114eb008073). Relevant paths: `LICENSE`, `sources/core/workflow_factory.py`, workflow runner/selection modules, and workflow prompts.
- **[S7]** [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent), inspected revision `484776c`, release v1.0.0.
- **[S8]** [Biomni](https://github.com/snap-stanford/Biomni), inspected revision `400c1f3`; see `license_info.md` and the A1 execution implementation.
- **[S9]** [EvoMaster](https://github.com/sjtu-sai-agents/EvoMaster), inspected revision `50dc000`.
- **[S10]** [DeepScientist](https://github.com/ResearAI/DeepScientist), inspected revision `b366244`.
- **[S11]** [SAGA](https://github.com/btyu/SAGA).
- **[S12]** [AutoScientists, inspected commit](https://github.com/mims-harvard/AutoScientists/tree/c71a92343b9a488ed10134be805845b9473ad18f); see `runbook.md` and `task-biomlbench/LAUNCH.md`.
- **[S13]** [AI Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2), including its current custom `LICENSE`.
- **[S14]** [Arbor](https://github.com/RUC-NLPIR/Arbor).
- **[S15]** [AutoSci](https://github.com/PKU-DAIR/AutoSci).
- **[S16]** [AstaBench](https://github.com/allenai/asta-bench), [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench), and [CORE-Bench](https://github.com/siegelz/core-bench).
- **[S17]** [Agent Zero, inspected commit](https://github.com/agent0ai/agent-zero/tree/ba9b67df0f54ac78106ae85c552ef5d2458f7c9a). Relevant paths: `LICENSE`, `tools/call_subordinate.py`, `skills/a0-create-agent/SKILL.md`, `plugins/_memory/README.md`, `docs/guides/projects.md`, and `conf/model_providers.yaml`.
- **[S18]** [OpenHands main application](https://github.com/OpenHands/OpenHands/tree/bca403840de709eea0584da19a288be3d705cdc9), [software-agent SDK](https://github.com/OpenHands/software-agent-sdk/tree/942deccf8a865ca04db54955ebefe1a5abd10f10), and [Enterprise license](https://github.com/OpenHands/enterprise/blob/main/LICENSE). SDK source paths include `openhands-tools/openhands/tools/delegate/`, `openhands-tools/openhands/tools/task/`, and `openhands-sdk/openhands/sdk/subagent/`.

## Source register: knowledge and memory

- **[K1]** [TrustGraph](https://github.com/trustgraph-ai/trustgraph/tree/17e5d742), [ontology documentation](https://docs.trustgraph.ai/learn/ontologies.html); inspected policy and provenance modules/specifications.
- **[K2]** [Graphiti](https://github.com/getzep/graphiti/tree/ed231965), including the current README, temporal edge maintenance, and reference-server warnings; [Zep public repository scope](https://github.com/getzep/zep).
- **[K3]** [Cognee](https://github.com/topoteretes/cognee), [ontology support](https://docs.cognee.ai/guides/ontology-support), [permissions](https://docs.cognee.ai/core-concepts/multi-user-mode/permissions-system/overview), and [forget operation](https://docs.cognee.ai/core-concepts/main-operations/forget).
- **[K4]** [LightRAG](https://github.com/HKUDS/LightRAG/tree/d83362bd), including API-server documentation, storage implementations, and document deletion/entity editing code.
- **[K5]** [KAG](https://github.com/OpenSPG/KAG), [OpenSPG](https://github.com/OpenSPG/openspg), and [KAG paper](https://arxiv.org/abs/2409.13731).
- **[K6]** [Microsoft GraphRAG](https://github.com/microsoft/graphrag/tree/34b2b67a), including current maintenance notice, indexing methods/outputs, and incremental update implementation.
- **[K7]** [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG), [HippoRAG 2 paper](https://arxiv.org/abs/2502.14802), and [GraphRAG-Bench](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark).
- **[K8]** [Mem0](https://github.com/mem0ai/mem0), particularly OSS/platform and migration documentation; [memory benchmarks](https://github.com/mem0ai/memory-benchmarks).
- **[K9]** [Letta archived server](https://github.com/letta-ai/letta/tree/archive) and [Letta Code](https://github.com/letta-ai/letta-code).
- **[K10]** [Supermemory self-hosting scope](https://supermemory.ai/docs/self-hosting/overview).
- **[K11]** [Hindsight](https://github.com/vectorize-io/hindsight).
- **[K12]** [MemOS](https://github.com/MemTensor/MemOS).

## Source register: runtime, durability, sandboxes, and interaction

- **[R1]** [AgentScope 2.0, inspected revision](https://github.com/agentscope-ai/agentscope/tree/27d8359), particularly `src/agentscope/app/_tool/_agent_create.py` and `_team_create.py`; [AgentScope Runtime migration notice](https://github.com/agentscope-ai/agentscope-runtime); [legacy large-agent simulation paper](https://arxiv.org/abs/2407.17789).
- **[R2]** [LangGraph](https://github.com/langchain-ai/langgraph), [Deep Agents](https://github.com/langchain-ai/deepagents), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [Agent Server deployment](https://docs.langchain.com/langsmith/deploy-standalone-server), [async subagents](https://docs.langchain.com/oss/python/deepagents/async-subagents), and [`langgraph-api` package metadata](https://pypi.org/pypi/langgraph-api/json).
- **[R3]** [Temporal server](https://github.com/temporalio/temporal), [Temporal UI](https://github.com/temporalio/ui), [AI integrations](https://github.com/temporalio/ai-integrations), [execution limits](https://docs.temporal.io/workflow-execution/limits), and [child workflow guidance](https://docs.temporal.io/child-workflows).
- **[R4]** [DBOS Transact Python](https://github.com/dbos-inc/dbos-transact-py), [workflow semantics](https://docs.dbos.dev/python/tutorials/workflow-tutorial), and [Conductor self-hosting/license](https://docs.dbos.dev/conductor/self-hosting/hosting-conductor).
- **[R5]** [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) and [workflow checkpoint documentation](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints?pivots=programming-language-python).
- **[R6]** [CrewAI](https://github.com/crewAIInc/crewAI) and [checkpointing documentation](https://docs.crewai.com/v1.15.41/en/concepts/checkpointing).
- **[R7]** [Restate server license](https://github.com/restatedev/restate/blob/main/LICENSE) and [Python SDK](https://github.com/restatedev/sdk-python).
- **[R8]** [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox), [small-scale admission test](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/architecture/fast-sandbox/performance.md), and [HA notes](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/architecture/fast-sandbox/ha.md).
- **[R9]** [Kubernetes SIG agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) and [roadmap](https://github.com/kubernetes-sigs/agent-sandbox/blob/main/roadmap.md).
- **[R10]** [E2B runtime](https://github.com/e2b-dev/runtime) and [open Embed deployment scope](https://github.com/e2b-dev/runtime/tree/main/embed).
- **[R11]** [Daytona public repository and maintenance notice](https://github.com/daytonaio/daytona).
- **[R12]** [Langfuse core/enterprise license boundary](https://github.com/langfuse/langfuse/blob/main/LICENSE) and [self-hosted feature licensing](https://langfuse.com/self-hosting/license-key).
- **[R13]** [Opik](https://github.com/comet-ml/opik) and [Phoenix license](https://github.com/Arize-ai/phoenix/blob/main/LICENSE).
- **[R14]** [AG-UI](https://github.com/ag-ui-protocol/ag-ui) and [event specification](https://docs.ag-ui.com/concepts/events).

## Source register: ingestion, Azure, and commercial references

- **[I1]** [Docling](https://github.com/docling-project/docling/tree/6d3bb9ee1bffaee73f2dddfda10dc0f1c438a643), [Docling Serve](https://github.com/docling-project/docling-serve), and [offline/remote-service options](https://docling-project.github.io/docling/usage/advanced_options/).
- **[I2]** [Unstructured](https://github.com/Unstructured-IO/unstructured), [unstructured-ingest](https://github.com/Unstructured-IO/unstructured-ingest), and [ingestion documentation and maintenance qualification](https://docs.unstructured.io/open-source/ingestion/overview).
- **[I3]** [Unstructured SharePoint connector requirements](https://docs.unstructured.io/open-source/ingestion/source-connectors/sharepoint).
- **[I4]** [Apache NiFi](https://github.com/apache/nifi) and [QueryDatabaseTableRecord](https://nifi.apache.org/components/org.apache.nifi.processors.standard.QueryDatabaseTableRecord/).
- **[I5]** [Debezium](https://github.com/debezium/debezium) and [SQL Server CDC documentation](https://debezium.io/documentation/reference/stable/connectors/sqlserver.html).
- **[I6]** [Onyx licenses](https://github.com/onyx-dot-app/onyx/blob/main/LICENSE), [enterprise license](https://github.com/onyx-dot-app/onyx/blob/main/backend/ee/LICENSE), and [connector permissions](https://docs.onyx.app/admins/connectors/overview).
- **[I7]** [Airweave repository](https://github.com/airweave-ai/airweave), checked through the GitHub API: archived; latest default-branch commit `1ebe1af2dbfb90f3334410721e69997e4f02b320`, June 5, 2026.
- **[I8]** [Airweave SharePoint Online connector documentation](https://github.com/airweave-ai/airweave/blob/main/fern/docs/pages/connectors/sharepoint_online/main.mdx).
- **[I9]** [Microsoft: Azure ACS retirement in Microsoft 365](https://learn.microsoft.com/en-us/sharepoint/dev/sp-add-ins/retirement-announcement-for-azure-acs).
- **[I10]** [Microsoft Graph drive delta](https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0).
- **[A1]** [AKS Pod sandboxing requirements and limitations](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing).
- **[A2]** [Azure OpenAI v1 API](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).
- **[A3]** [Azure OpenAI quota management](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/quota).
- **[C1]** [Edison Scientific's current product/deployment positioning](https://edisonscientific.com/) and [How We Built Kosmos](https://advances.edisonscientific.com/research/how-we-built-kosmos/).
- **[C2]** [Claude Managed Agents multi-agent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration).
- **[C3]** [Microsoft Discovery Engine](https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-discovery-engine).
- **[C4]** [Discovery public repository](https://github.com/microsoft/discovery/tree/d424c9e7e6b769fdfdbe0c63bea4ad8ff7a82ecf), especially `CONTRIBUTING.md`, `README.md`, and `docs/discovery-app/install.md`.
- **[C5]** [Discovery Bookshelf capabilities and limits](https://learn.microsoft.com/en-us/azure/microsoft-discovery/concept-bookshelf-knowledge-bases).
- **[C6]** [Google Co-Scientist](https://docs.cloud.google.com/gemini/enterprise/docs/co-scientist) and [Antigravity /teamwork research announcement](https://research.google/blog/advancing-science-engineering-with-antigravitys-teamwork-feature/).
