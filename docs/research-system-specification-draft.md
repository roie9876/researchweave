# ResearchWeave: autonomous research system specification draft

Status: working draft for discussion. Requirements reflect the conversation;
technical design choices and unverified capabilities are not final.

See the [architecture proposal](researchweave-architecture-proposal.md) for
recommended Azure services, core components, and company-brain design.
The [core components proposal](researchweave-core-components-proposal.md)
details reuse, integration gaps, and validation outside the company brain.

## 1. Product vision

Create an open-source research system with a modern graphical interface for
individual engineers and researchers. Given an open-ended objective, it
clarifies the task, independently investigates it using public and uploaded
information, adapts its approach, and reports what it found.

The system should make useful progress on difficult problems, but it must not
claim that a mathematical conjecture is proved or a scientific or medical
problem is solved without adequate evidence. A well-supported partial result
is a valid outcome.

Use the [market study](../../../researchweave/docs/autonomous-research-market-study-2026-11-14.md)
to identify existing software worth reusing; add custom code where necessary.
Neither a particular framework nor a from-scratch implementation is required.

## 2. Initial user and scope

- Initial users: individual researchers or engineers. Multiple researchers
  can sign in to the same installation, each with their own investigations.
  Investigations are visible to signed-in researchers by default; determine
  who may sign in and who may control or delete another person's work.
- Deployment: each adopter can install their own instance in their own Azure
  subscription. Users sign in to access the interface using personal or
  organizational Microsoft accounts approved by the installation owner.
  Validate the selected identity configuration and subscription prerequisites.
- Research domains are not restricted to one discipline. Examples include
  mathematics, engineering, genetics, and disease research.
- The first version focuses on computational research. Physical experiments,
  laboratory control, and clinical use are not established requirements.
- Search the public web and relevant scientific sources, accept user-provided
  public links, and analyze user-uploaded documents and datasets.
- Start private data ingestion with Azure Blob Storage; add other
  organizational connectors later.
- Start with Azure-hosted models and design the model integration so other
  providers can be added later. The researcher selects an allowed pool of
  models, and the system assigns models from that pool to agents as needed.
  The researcher can change the pool while an investigation is running.
- Initially allow one actively running investigation at a time per
  researcher. A paused investigation does not prevent starting another.
  If another run is active when a paused one is resumed, explain the conflict
  and let the researcher pause the current run or cancel the resume.
- Select agent counts dynamically based on the investigation and available
  resources. Large-scale operation is a goal to validate, not a fixed initial
  concurrency promise.
- Plan for an eventual knowledge corpus on the order of 100,000 to 1 million
  items, including documents, datasets, and research artifacts. This is a
  user-provided planning range, not a measured dataset or a proven limit.

## 3. Research workflow

1. The researcher enters a free-text objective, optionally adds public
   reference links, and uploads relevant files.
2. The system asks clarifying questions when needed and presents its
   understanding of the objective, proposed settings, and stopping
   conditions for confirmation before starting.
3. After confirmation, the system plans, searches, reads, reasons, generates
   and tests ideas, creates specialist agents and tasks when useful, and
   executes code and analyzes data where appropriate.
4. The system adapts the investigation to discoveries and failures rather than
   requiring a fixed, user-authored task graph.
5. While work continues, the researcher can converse with the agent
   responsible for the investigation, ask questions, provide new information,
   redirect work, pause, or stop the investigation.
6. On completion or pause, the system presents findings, evidence, uncertainty,
   and available artifacts. If it has not solved the problem, it says so.

### Input and evidence

- Public web search and pages, scientific papers and preprints, public
  scientific databases and datasets, and explicit user-provided links are
  intended sources. Specific supported services and access terms remain to
  be selected.
- Internet research is essential, and paid search or data access is
  acceptable where needed. Choose the mechanism during the architecture and
  services discussion; Microsoft Foundry capabilities are a candidate to
  evaluate, not an already selected or verified solution.
- Users can upload PDF and text documents, spreadsheets, and CSV datasets.
- Create a separate Azure Blob container per research run for user uploads.
  Specify container creation, authorization, lifecycle, errors, and deletion
  as part of implementation design.
- Store source references and associate findings with their supporting
  evidence. Distinguish source statements, observations, calculations, agent
  hypotheses, and verified results.
- Respect source access terms and applicable permissions. Public availability
  does not guarantee automated access to every paper, patent, or database.

### Autonomy and interaction

- Default product goal: minimal human intervention after the initial
  clarification and confirmation.
- Each investigation offers an autonomous mode and a human-approval mode.
  The specific approval granularity and the minimum technical safeguards
  must be designed and made visible to the researcher.
- Agents must not carry out illegal actions. Enforceable authorization,
  execution safeguards, and reporting of blocked actions need explicit
  design; the software cannot guarantee legal compliance.
- Isolate agent-executed code and protect credentials, private data, and
  external systems. Define permitted network and data access explicitly.
- Agents may write and run new research code or tools and install appropriate
  third-party packages within the isolated environment, subject to licensing
  and safety checks.
- The system may request additional types of Azure compute when needed,
  subject to availability, quota, configured guardrails, and the selected
  approval mode. It must surface resource requests and estimated charges.
  Use narrowly scoped cloud identities and audit provisioning actions;
  determine cleanup and recovery behavior before implementation.
- Present observable actions, evidence, and concise explanations of decisions;
  do not rely on access to model providers' private chain-of-thought.

### Live conversation and steering

- Provide a persistent conversation with a lead research agent throughout
  the investigation, not only before it starts or after it completes.
- The researcher can ask about the current objective, status, active work,
  findings, and evidence, and supply new information, links, instructions, or
  uploaded files while the investigation is running.
- The lead agent assesses incoming information and decides whether and how to
  update the investigation, its priorities, or its tasks. In autonomous mode,
  it may make those changes without asking for routine confirmation.
- The researcher may change the main objective within the same investigation.
  Keep the history of earlier objectives, decisions, findings, and sources
  so that results are not silently attributed to the wrong objective.
- When direction changes, the lead agent decides which active tasks to
  continue, adjust, or stop, subject to the selected approval settings.
- Show when an input has been received and how it affected the work. Record
  material changes and their reasons in the investigation timeline.
- Ordinary questions should not inadvertently change the research objective.
  If a requested change is unclear, the lead agent may seek clarification.
- Interaction should not require stopping and restarting the entire
  investigation or block unrelated work. Persist messages and decisions so
  reconnecting users and resumed runs can recover the conversation.
- Honor the selected human-approval settings and safety boundaries while
  processing new instructions; define behavior for changes that conflict
  with in-flight work.

### Controls and stopping conditions

- The researcher can configure maximum runtime, a spending limit, success or
  evidence criteria, and failure or lack-of-progress conditions; manual stop
  is available.
- Runtime and spending caps are optional and disabled by default.
- Show current runtime, spending estimates, selected conditions, status, and
  uncertainty in the interface.
- On reaching a configured limit before completion, preserve progress, show a
  partial report and reason for stopping, and allow the researcher to adjust
  limits and resume.
- Spending controls must account for billing delays, in-flight work, and
  charges not directly visible to the application. No exact hard billing cap
  may be promised without validated provider support.
- Failures and repeated retries must be visible. Recovery must avoid silently
  repeating costly or external side effects.

## 4. Outputs and quality

Each investigation should produce, as applicable:

- A direct answer or proposed solution, or an explicit statement that the
  objective remains unresolved.
- A detailed report explaining the research steps and evidence-backed
  reasoning, with links to original sources.
- Structure reports with a concise summary first, followed by detailed
  methods, findings, sources, and limitations.
- Support tables, plots, mathematical notation, images or diagrams, and
  step-by-step calculations where appropriate to the investigation.
- Alternative approaches or hypotheses and an explanation of uncertainty.
- Supporting code, calculations, datasets, and other reproducible artifacts
  that the system can lawfully retain and provide.
- Downloadable reports in PDF, Word, and Markdown or plain-text formats. The
  researcher chooses the language of each investigation's responses and report.
- Clear distinctions between a proposed idea, a tested result, and a
  verified conclusion. A proposed medical hypothesis is not a validated
  treatment, and a plausible mathematical argument is not necessarily a proof.
- Automatically perform independent checks of important findings, including
  claims, calculations, and source references where applicable. Record what
  was checked and its limitations; a second agent is not proof of correctness.
- Maintain an evolving draft report during a run, clearly labeled incomplete.

Define evaluation methods by task type. Possible indicators include evidence
gathered, hypotheses tested, calculations reproduced, failed approaches, and
unresolved questions. Activity counts alone are not proof of progress.

## 5. User interface

The interface should be modern, approachable, and visually clean for a broad
audience. Show essential information first; reveal advanced configuration,
details, and technical views through deliberate user actions.

Required capabilities:

- Support English and Hebrew, including appropriate right-to-left presentation
  in Hebrew. Validate both interface and exported report rendering.
- Conversational objective definition, clarifications, and confirmation, plus
  ongoing conversation with the lead research agent during a live run.
- A clear overview of investigation status and meaningful progress.
- On-demand views of active agents, tasks, dependencies, and relationships.
- Sources, emerging findings, supporting evidence, and uncertainty.
- A timeline of actions, decisions, failures, and progress.
- Runtime, estimated spending, stopping conditions, and relevant controls.
- Ask questions, add context, redirect, pause, stop, and resume.
- View the final or partial report and download available artifacts.
- Show all notifications and attention requests in the interface initially.
  Email and other external notification channels can be added later.

Exact screens, accessibility criteria, report-language defaults, event update
behavior, and visual identity are design work, not yet approved.

## 6. Persistence and knowledge

- Preserve uploaded files and research results until the researcher deletes
  them. Define what deletion means for source files, derived knowledge,
  reports, caches, backups, and audit records.
- Preserve research state and evidence across interruptions so a paused or
  failed investigation can recover or resume where technically possible.
- The researcher selects which earlier investigations to reuse as knowledge
  for a new investigation. Define how shared evidence and findings are
  presented, traced, updated, and removed.
- In the optional human-approval mode, the researcher configures which
  categories of actions require approval.
- An evidence store and investigation state are distinct from an agent's
  context or conversation summaries. Do not treat generated summaries as
  authoritative measurements.

## 7. Deployment and GitHub readiness

- Publish a professionally structured open-source repository with a clear
  README, setup and deployment instructions, license, contribution guidance,
  security reporting process, and tests.
- Recommend a permissive project license after reviewing exact component
  licenses, third-party notices, and compatibility. MIT and Apache 2.0 both
  permit broad use; the final selection is not yet made.
- Provide an accessible automated Azure deployment flow for users without
  cloud expertise. Evaluate a deployment button or guided equivalent rather
  than assuming Azure authentication, quotas, permissions, and configuration
  can be eliminated.
- Explain prerequisites, target subscription, required permissions, region,
  model availability, estimated recurring and usage-based costs, and
  configuration before provisioning. Require explicit provisioning approval.
- Automatically create suitable Azure model deployments where possible,
  subject to model availability, quota, permissions, and user approval.
  Surface setup failures and any required manual steps clearly.
- Do not commit credentials, private uploads, generated secrets, or live
  subscription details. Use appropriate Azure identity and secret management.
- Include the existing market study in the future public repository after
  reviewing it for publication, privacy, and third-party license issues.
- Include automated tests, dependency and license review, and secret
  detection suitable for a public repository.
- Actual Azure provisioning and GitHub publication require a separate,
  informed approval; the current work is specification and planning only.

## 8. Architecture investigation

### Proposed functional boundaries

These are responsibilities, not a commitment to separate services or
particular products:

1. **Research interface:** bilingual, progressively disclosed views for
   starting and steering investigations, live status, evidence, and reports.
2. **Application and identity:** authenticated access, investigation
   lifecycle, settings, uploads, report access, and authorization.
3. **Lead research coordinator:** understands the objective, manages
   clarifications and live conversation, tracks changes, and delegates and
   adapts tasks using the researcher's selected model pool.
4. **Workers and tools:** dynamically assigned specialist tasks, public
   search and source access, analysis, and isolated code execution.
5. **Durable state and events:** persist objectives, messages, tasks, results,
   decisions, failure information, and progress; support recovery and live
   interface updates without relying solely on model context.
6. **Evidence and knowledge:** ingest and retrieve public and uploaded
   material, retain source links and research artifacts, and allow selection
   of prior investigations as knowledge sources.
7. **Storage and operations:** use a run-specific Blob container for uploads;
   track configurable limits and approximate costs; manage deployment,
   secrets, monitoring, and cleanup.

The interface communicates with application APIs; the coordinator works with
durable state, workers, and evidence. Exact process boundaries, messaging,
databases, and scaling mechanisms require component selection and testing.

### Candidate evaluation

No final stack has been selected. Compare existing components against the
workflow and acceptance criteria before implementation:

- Application starting points: OpenScientist and other candidates from the
  market study versus building only the missing application-specific pieces.
- Agent orchestration: LangGraph, AgentScope, and alternatives where their
  verified capabilities support dynamic research rather than only fixed flows.
- Durable execution: evaluate Temporal or another recovery mechanism for
  interruptions, retries, and long-running work.
- Research knowledge and retrieval: compare appropriate approaches and the
  reviewed open-source candidates. The knowledge-sharing policy comes first.
- Execution isolation, public search, scientific-source access, Azure-hosted
  model integration, storage, and the graphical interface each require
  explicit component evaluation.

Do not assume these candidates should all be combined. Verify the licenses
and actual versions of libraries, servers, UI, models, data, and services.
In particular, test live steering, recovery during tool execution, selected
model-pool use, evidence traceability, and Blob integration before selecting
a base application or orchestration framework.

## 9. Initial acceptance scenarios

1. A signed-in researcher starts a run with a free-text objective, a public
   link, and uploaded files. The system creates the run's Blob container and
   records the objective and references.
2. The system asks for needed clarification and presents the objective and
   settings for confirmation before autonomous work begins.
3. The run searches suitable public sources, creates and coordinates tasks
   dynamically, and executes an appropriate data analysis in an isolated
   environment. Its findings link back to accessible supporting evidence.
4. While other work continues, the researcher asks the lead agent about
   progress and changes the research objective or supplies new evidence.
   The system records the input and objective history, explains its effect,
   updates relevant work without restarting the run, and keeps unrelated work
   running. The lead agent decides how to handle affected active tasks.
5. An interrupted or paused run retains its accepted state and can resume;
   repeating expensive side effects is handled explicitly.
6. A configured runtime or spending limit pauses the run, shows its partial
   results, and allows a continuation. Cost controls acknowledge any
   unobservable or delayed charges.
7. An unresolved research question produces a useful partial result with
   explicit uncertainty, not a fabricated definitive answer.
8. A prospective adopter can follow the documented Azure deployment flow,
   review its prerequisites and costs, and access an authenticated interface.
   The actual flow must be tested rather than assumed to be one-click.
9. A repository and deployment review finds no committed credentials or
   accidentally published user data; third-party licensing is documented.

These are functional scenarios, not measured performance or accuracy
thresholds. Define representative tasks, evidence, and thresholds with the
user before treating the specification as implementation-ready.

## 10. Open decisions

- Initial exact public search and scientific-data sources and their terms.
- Model deployments and Azure availability; model/provider extension contract.
- Sign-in authorization and control or deletion permissions for shared
  investigations within one installation.
- Cross-investigation knowledge implementation and controls, including source
  provenance and handling of updates, contradictions, and deletion.
- How the interface presents model-pool choices and handles model changes
  for calls already in flight.
- Human-approval behavior, enforceable agent safeguards, and escalation.
- How success criteria and lack of progress are assessed without false claims.
- Exact UI flows, accessibility requirements, and visual design.
- Resource, availability, and deployment assumptions; cost estimation and
  budget enforcement capabilities; safe, auditable dynamic compute
  provisioning and lifecycle management.
- Component choices, project license, repository structure, and development
  milestones based on the actual dependencies and tests.
