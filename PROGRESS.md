# ResearchWeave — Engineering Rebuild & Integration Progress Tracker

> **Goal:** Replace custom prototype mockups with a production-grade scientific research platform built on **OpenScientist (Apache-2.0)**, **AgentScope 2.0 (Apache-2.0)**, **TrustGraph Ontology/PROV-O Knowledge Graph (Apache-2.0)**, **Microsoft Azure AI Content Understanding**, **Microsoft Foundry (`gpt-6.1-sol` & `gpt-6-astra`)**, **Azure Blob Storage**, and **AKS + Azure PostgreSQL**.

---

## Status Summary

| Phase | Component / Milestone | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Environment & Network Unblocking** | ✅ **DONE** | Resolved `files.pythonhosted.org` TLS SNI reset by configuring `~/.config/pip/pip.conf` (`https://mirrors.aliyun.com/pypi/simple/`); configured Copilot SDK subagent model to `gemini-4-argon` in `~/.copilot/settings.json` and agent YAML definitions. |
| **Phase 1** | **OpenScientist Core & Real Literature Discovery** | ✅ **DONE** | Integrated `OpenScientistKnowledgeState` (`hypotheses` `H001+`, `findings` `F001+` with abstract-snippet citation validation, `literature` `L001+`, `analysis_log`) and live PubMed E-utilities + ArXiv Atom XML retrieval in `src/researchweave/openscientist_engine.py`. |
| **Phase 2** | **Dynamic Specialist Teams (`agentscope==2.0.11`)** | ✅ **DONE** | Installed `agentscope==2.0.11` and built `src/researchweave/agentscope_runtime.py` (`FoundryAgentScopeChatModel` subclassing `agentscope.model.ChatModelBase` + `AgentScopeTeamRuntime` spawning real `agentscope.agent.Agent` instances bound to `gpt-6.1-sol` and `gpt-6-astra`). |
| **Phase 3** | **Azure AI Content Understanding & Document Ingestion** | ✅ **DONE** | Built `src/researchweave/content_understanding.py` calling the Foundry `AIServices` Document Intelligence / Content Understanding layout API (`prebuilt-layout:analyze`) with keyless `DefaultAzureCredential` + structured table/section/page locators stored in per-run Blob containers (`rw-inv-*`). |
| **Phase 4** | **TrustGraph Ontology & PROV-O Company Brain** | ✅ **DONE** | Built `src/researchweave/trustgraph_brain.py` implementing TrustGraph's OWL/RDF Scientific Ontology (`researchweave-scientific-ontology-v1`), W3C `PROV-O` (`http://www.w3.org/ns/prov#`, `https://trustgraph.ai/ns/`, `urn:graph:source`), and `gpt-6-astra` ontology entity/relationship extraction. |
| **Phase 5** | **AKS + PostgreSQL + Kata Sandbox Infrastructure (`infra/`)** | ✅ **DONE** | Authored `infra/aks-main.bicep` (verified with `az bicep build`) and `infra/k8s-trustgraph-openscientist.yaml` defining the 4 AKS node pools (`apppool`, `brainpool` for TrustGraph/Qdrant/Cassandra, `sandboxpool` with `KataMshvVmIsolation` microVMs, and scale-to-zero `gpupool`), Azure Database for PostgreSQL Flexible Server, Foundry (`gpt-6.1-sol` & `gpt-6-astra`), and Blob Storage. |
| **Phase 6** | **End-to-End Verification & Azure Redeployment** | 🔄 **IN PROGRESS** | All 6 local acceptance tests passing (`1.077s`); pushing to `origin/main` and verifying live Azure execution with `agentscope==2.0.11`, OpenScientist, TrustGraph PROV-O, and `gpt-6.1-sol` / `gpt-6-astra`. |

---

## Detailed Task Checklist

### Phase 0 — Environment & Tooling Setup
- [x] **0.1 Diagnose `files.pythonhosted.org` failure:** Identified TLS `ClientHello` SNI reset (`Recv failure: Socket is not connected`) on local network path while `pypi.org` and `github.com` remained reachable.
- [x] **0.2 Configure working PyPI Mirror:** Configured `/Users/roie9876/.config/pip/pip.conf` to use `https://mirrors.aliyun.com/pypi/simple/` (verified downloading `agentscope-2.0.11` at 1.3 MB/s).
- [x] **0.3 Fix Copilot SDK Subagent Model:** Created `/Users/roie9876/.copilot/settings.json` and updated `task.agent.yaml` & `explore.agent.yaml` to prioritize `gemini-4-argon` over `gpt-5.6-luna`.
- [x] **0.4 Provision Azure Foundry Models:** Deployed **`gpt-6.1-sol`** (`2026-09-29`, `GlobalStandard`, cap 100) and **`gpt-6-astra`** (`2026-09-03`, `GlobalStandard`, cap 100) on `rweave-4vfkm7-foundry` (`swedencentral`).

### Phase 1 — OpenScientist Foundation & Real Scientific Literature Engine
- [x] **1.1 Clone & Inspect OpenScientist (`openscientist-io/openscientist`):** Inspected OpenScientist's discovery loop, `KnowledgeState` schema, iteration runner, and PubMed/literature tools.
- [x] **1.2 Integrate OpenScientist Discovery Loop & Real Literature APIs (ArXiv + PubMed):** Implemented `src/researchweave/openscientist_engine.py` with live queries to ArXiv API (`export.arxiv.org`) and NCBI PubMed E-utilities (`eutils.ncbi.nlm.nih.gov`) plus OpenScientist's `KnowledgeState` and `validate_citation`.
- [x] **1.3 Wire Live `gpt-6.1-sol` and `gpt-6-astra` Reasoning:** Assigned `gpt-6-astra` to literature synthesis & hypothesis generation and `gpt-6.1-sol` to Lead Coordinator planning, quantitative computation, and Independent Epistemic Review.

### Phase 2 — Real AgentScope 2.0 (`agentscope==2.0.11`) Multi-Agent Integration
- [x] **2.1 Install & Wire `agentscope` in `pyproject.toml` and Runtime:** Installed `agentscope==2.0.11` and built `src/researchweave/agentscope_runtime.py` (`FoundryAgentScopeChatModel` + `AgentScopeTeamRuntime`).

### Phase 3 — Microsoft Azure AI Content Understanding & Per-Run Blob Ingestion
- [x] **3.1 Build Azure AI Content Understanding Adapter (`content_understanding.py`):** Connected to the Microsoft Foundry `AIServices` endpoint (`documentintelligence/documentModels/prebuilt-layout:analyze`) using `DefaultAzureCredential` to parse uploaded scientific PDFs, CSVs, and documents into structured sections, tables, and page/locator metadata stored in the run's Azure Blob container (`rw-inv-*`).

### Phase 4 — TrustGraph Ontology & PROV-O Company Brain
- [x] **4.1 Inspect & Integrate TrustGraph (`trustgraph-ai/trustgraph`) Ontology & PROV-O Schema:** Built `src/researchweave/trustgraph_brain.py` incorporating TrustGraph's RDF/OWL ontology definitions and W3C `PROV-O` provenance graph structure (`Document -> Page/Chunk -> ExtractionActivity -> Subgraph -> Entity/Relation`), powered by live `gpt-6-astra` extraction.

### Phase 5 — AKS + PostgreSQL + TrustGraph + Kata Sandbox Infrastructure (`infra/`)
- [x] **5.1 Author `infra/aks-main.bicep` & Kubernetes Manifests (`infra/k8s-trustgraph-openscientist.yaml`):** Defined the production AKS cluster (`apppool`, `brainpool` for TrustGraph/Qdrant/Cassandra, `sandboxpool` Kata Containers microVMs, and scale-to-zero `gpupool`), Azure Database for PostgreSQL Flexible Server, Microsoft Foundry, and Azure Blob Storage.

### Phase 6 — Verification, Testing & Live Azure Deployment
- [ ] **6.1 Run Full Verification Suite & Live Azure Test:** Verify real ArXiv/PubMed literature ingestion, LLM-generated Python sandbox code execution, TrustGraph ontology/PROV-O extraction, and `gpt-6.1-sol` / `gpt-6-astra` coordination both locally and on Azure.
