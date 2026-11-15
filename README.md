# ResearchWeave

**Autonomous Scientific & Engineering Research Platform on Microsoft Azure**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Froie9876%2Fresearchweave%2Fmain%2Finfra%2Fazuredeploy.json)

ResearchWeave is an open-source autonomous research organization in software with a clean, bilingual (**English / Hebrew RTL**) graphical workspace. Engineers and researchers can submit open-ended scientific, mathematical, or engineering problems—such as **Fermat's Last Theorem & modular generalizations**, **genetic hair loss (androgenetic alopecia) pathways**, or **Parkinson's disease (GBA1/α-synuclein) kinetics**—and let a dynamically assembled team of specialist agents investigate, run isolated calculations, connect evidence in a persistent **Company Brain**, and produce cited reports in **PDF, Word (`.docx`), and Markdown**.

---

## Key Capabilities

1. **Pre-Run Clarification & Confirmation Gate:** Before starting a multi-day or deep investigation, the Lead Research Coordinator asks domain-specific clarifying questions and presents the objective, model pool, and stopping conditions for confirmation.
2. **Dynamic Specialist Agent Creation:** Spawns domain-tailored specialist agents at runtime (literature explorer, quantitative sandbox analyst, hypothesis synthesizer, and an independent epistemic reviewer) and assigns models from the researcher's editable Azure Foundry model pool.
3. **Persistent Company Brain & Knowledge Graph:** Extracts entities, typed relationships, and source-linked claims with SHA-256 provenance. Enforces strict cross-investigation scope selection and propagates source deletions cleanly across derived graph nodes and claims.
4. **Epistemic Integrity (Verified Results vs. Hypotheses):** Automatically runs an Independent Reviewer Agent to separate verified calculations and source-backed observations (`REVIEWED_VERIFIED`) from unverified preclinical or theoretical hypotheses (`HYPOTHESIS`).
5. **Per-Investigation Azure Blob Container:** Automatically provisions an isolated container (`rw-inv-...`) per research run for uploaded datasets (`.csv`, `.txt`, `.md`) and generated calculation artifacts.
6. **Live Conversation & Non-Blocking Mid-Run Steering:** Converse with the Lead Research Coordinator while research is running. Ordinary questions are answered without interrupting workers; new directions record an Objective Revision within the same investigation and spawn a dedicated specialist branch.
7. **Progressive-Disclosure Bilingual Interface (EN / HE RTL):** Modern dark UI designed to prevent cognitive overload—showing core progress first and revealing deep agent graphs, Company Brain paths, Blob uploads, and live settings on demand.

---

## High-Level System Architecture & Layered Stack

![ResearchWeave High-Level Layered Architecture](docs/architecture-overview.svg)

### 1. Open-Source Software & Frameworks Used

ResearchWeave integrates source-verified open-source software across its scientific discovery loop, multi-agent runtime, ontology/provenance knowledge graph, and cloud-native compute layers:

| Layer | Open-Source Project / Package | License | Status & Role in ResearchWeave |
| :--- | :--- | :--- | :--- |
| **Multi-Agent Team Runtime** | **[AgentScope 2.0 (`agentscope>=2.0.0`)](https://github.com/agentscope-ai/agentscope)** | Apache-2.0 | **Active in `pyproject.toml` & `agentscope_runtime.py`:** Instantiates genuine `agentscope.agent.Agent` specialist instances (`Literature`, `Computation`, `Hypothesis`, `Independent Reviewer`) backed by `FoundryAgentScopeChatModel` (`ChatModelBase`) routing across **`gpt-6.1-sol`** and **`gpt-6-astra`**. |
| **Scientific Discovery Loop & Citation Verification** | **[OpenScientist](https://github.com/openscientist-io/openscientist)** | Apache-2.0 | **Active in `openscientist_engine.py`:** Implements OpenScientist's iterative `KnowledgeState` (`hypotheses` `H001+`, `findings` `F001+` with abstract-snippet `validate_citation`, `literature` `L001+`, `analysis_log`) plus live **NCBI PubMed E-utilities** and **ArXiv Atom API** retrieval. |
| **Company Brain Ontology & Provenance** | **[TrustGraph](https://github.com/trustgraph-ai/trustgraph)** (+ **Apache Cassandra 5.0** & **Qdrant** on AKS) | Apache-2.0 | **Active in `trustgraph_brain.py` & `infra/k8s-trustgraph-openscientist.yaml`:** Enforces the OWL/RDF Scientific Ontology (`researchweave-scientific-ontology-v1`) and generates W3C `PROV-O` (`http://www.w3.org/ns/prov#`, `https://trustgraph.ai/ns/`) lineage triples (`Document -> Page -> Chunk -> ExtractionActivity -> Subgraph -> Entity/Relation`) with live `gpt-6-astra` extraction. |
| **Data Validation & Schemas** | **[Pydantic v2](https://github.com/pydantic/pydantic)** | MIT | **Active in `pyproject.toml` & `models.py`:** Validates all investigation models, objective revisions, specialist personas, epistemic claim states (`REVIEWED_VERIFIED` vs. `HYPOTHESIS`), and HTTP payloads. |
| **Azure Auth, Blob & Model SDKs** | **[azure-identity](https://github.com/Azure/azure-sdk-for-python)**, **[azure-storage-blob](https://github.com/Azure/azure-sdk-for-python)**, **[openai](https://github.com/openai/openai-python)** | MIT / Apache-2.0 | **Active in `pyproject.toml`:** Keyless `DefaultAzureCredential` (`get_bearer_token_provider`) authentication for Microsoft Foundry (`gpt-6.1-sol` / `gpt-6-astra`), Azure AI Content Understanding, and per-investigation Blob containers (`blob_store.py`). |
| **Relational & Durable State** | **[PostgreSQL 16](https://www.postgresql.org/)** (+ `pgvector` / `Apache AGE`) & **[SQLite 3](https://www.sqlite.org/)** | PostgreSQL / Public Domain | **Active (`brain.py` SQLite locally; `infra/aks-main.bicep` Azure PostgreSQL Flexible Server in cloud):** Canonical durable persistence for investigations, tasks, sources, entities, relations, and claims. |
| **MicroVM Sandbox Isolation** | **[Kata Containers](https://katacontainers.io/)** (`KataMshvVmIsolation` on AKS) + **AST Guardrails (`sandbox.py`)** | Apache-2.0 | **Active in `sandbox.py` & `infra/aks-main.bicep`:** Static Python AST safety validation paired with hypervisor-isolated Kata microVM pods and zero-trust `NetworkPolicy` on the AKS `sandboxpool`. |

---

### 2. Microsoft Azure Services & Compute Architecture

| Azure Service | IaC Definition (`infra/aks-main.bicep` & `infra/main.bicep`) | Role in ResearchWeave |
| :--- | :--- | :--- |
| **Azure Kubernetes Service (AKS)** | `Microsoft.ContainerService/managedClusters` (`infra/aks-main.bicep`) | **Primary Production Compute Cluster** with **4 specialized node pools**:<br>• `apppool` (`Standard_D4s_v5`): OpenScientist UI/API & AgentScope 2.0 specialist workers<br>• `brainpool` (`Standard_E8s_v5` + Premium SSD v2 CSI): TrustGraph StatefulSets (Cassandra 5.0 + Qdrant)<br>• `sandboxpool` (`KataMshvVmIsolation`): Hypervisor microVM-isolated pods for untrusted agent Python code<br>• `gpupool` (`Standard_NC4as_T4_v3`, auto-scales `0..4`): Scale-to-zero GPU nodes for heavy scientific simulations |
| **Microsoft Foundry / Azure AI Services** | `Microsoft.CognitiveServices/accounts` (`kind: 'AIServices'`) | Hosts the **`gpt-6.1-sol`** (`2026-09-29`, `GlobalStandard`, cap 100 — Lead Coordinator, Computation, Independent Reviewer) and **`gpt-6-astra`** (`2026-09-03`, `GlobalStandard`, cap 100 — Literature Explorer, TrustGraph Ontology & Hypothesis Architect) deployments with `disableLocalAuth: true`. |
| **Azure AI Content Understanding / Document Intelligence** | Enabled on `Microsoft.CognitiveServices/accounts` (`content_understanding.py`) | Extracts structured Markdown, scientific tables, section hierarchies, and exact page/character-offset locators (`prebuilt-layout:analyze`) via keyless Entra RBAC before indexing into TrustGraph. |
| **Azure Database for PostgreSQL Flexible Server** | `Microsoft.DBforPostgreSQL/flexibleServers` (`infra/aks-main.bicep`) | Managed PostgreSQL 16 (`Standard_D2ds_v5`, Entra ID authentication enabled) for canonical multi-user OpenScientist and workflow state. |
| **Azure Blob Storage** | `Microsoft.Storage/storageAccounts` (`blob_store.py`) | Automatically provisions an isolated container (`rw-inv-<id>`) per investigation for raw uploaded PDFs/CSVs and generated sandbox calculation artifacts with SHA-256 provenance. |
| **User-Assigned Managed Identity & Workload Identity** | `Microsoft.ManagedIdentity/userAssignedIdentities` + Federated OIDC | Keyless authentication (`Storage Blob Data Contributor`, `Cognitive Services OpenAI User`, `Cognitive Services User`) for both AKS pods (`researchweave-sa`) and Container Apps. |
| **Azure Container Apps** *(Lightweight Single-Click Option)* | `Microsoft.App/containerApps` (`infra/main.bicep` & `infra/azuredeploy.json`) | Fast serverless deployment profile for running the unified ResearchWeave workspace without provisioning a full AKS cluster. |
| **Azure Log Analytics & Application Insights** | `Microsoft.OperationalInsights/workspaces` & `Microsoft.Insights/components` | Captures AKS/Container Apps operational telemetry and container logs (`PerGB2018`, 30-day retention). |

---

## Azure Deployment Options

### Option A: Production AKS + TrustGraph + PostgreSQL + Foundry Stack (`infra/aks-main.bicep`)

Deploys the full **AKS cluster** (4 node pools including Kata microVM sandboxes and scale-to-zero GPU pool), **Azure Database for PostgreSQL Flexible Server**, **Microsoft Foundry (`gpt-6.1-sol` + `gpt-6-astra` + Content Understanding)**, **Azure Blob Storage**, and **Workload Identity**:

```bash
az group create --name rg-researchweave-aks --location swedencentral --tags SecurityControl=Ignore
az deployment group create \
  --resource-group rg-researchweave-aks \
  --template-file infra/aks-main.bicep \
  --parameters appPrefix=rweave
```

Then apply the TrustGraph (Qdrant + Cassandra) and OpenScientist/AgentScope Kubernetes manifests:

```bash
az aks get-credentials --resource-group rg-researchweave-aks --name <aksClusterName>
kubectl apply -f infra/k8s-trustgraph-openscientist.yaml
```

### Option B: Lightweight One-Click Container Apps Deployment (`infra/main.bicep` & `infra/azuredeploy.json`)

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Froie9876%2Fresearchweave%2Fmain%2Finfra%2Fazuredeploy.json)

```bash
az group create --name rg-researchweave --location swedencentral --tags SecurityControl=Ignore
az deployment group create \
  --resource-group rg-researchweave \
  --template-file infra/main.bicep \
  --parameters appPrefix=rweave
```

---

## Quick Start (Local Run)

```bash
PYTHONPATH=src python3 -m researchweave.server
```

Then open **http://localhost:8080** in your browser.

### Running the Verification & Acceptance Suite

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

---

## Architecture & Market Research Documentation

- [Engineering Rebuild & Integration Progress Tracker](PROGRESS.md)
- [Source-Verified Market & Open-Source Study](docs/autonomous-research-market-study-2026-11-14.md)
- [Product Specification](docs/research-system-specification-draft.md)
- [System Architecture Proposal](docs/researchweave-architecture-proposal.md)
- [Company Brain Technical Design](docs/researchweave-company-brain-proposal.md)
- [Core Components & Integration Gates](docs/researchweave-core-components-proposal.md)
- [Security & Autonomous Guardrails](SECURITY.md)

## License

Licensed under the [Apache License 2.0](LICENSE).
