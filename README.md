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

## One-Click Azure Deployment

Anyone can deploy their own instance of ResearchWeave into their own Azure subscription:

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Froie9876%2Fresearchweave%2Fmain%2Finfra%2Fazuredeploy.json)

### What the Template Provisions (`infra/main.bicep` & `infra/azuredeploy.json`)

- **User-Assigned Managed Identity** (`Microsoft.ManagedIdentity/userAssignedIdentities`) — zero hardcoded keys or passwords.
- **Azure Storage Account** (`Microsoft.Storage/storageAccounts`) — backs per-investigation Blob containers with `Storage Blob Data Contributor` RBAC.
- **Microsoft Foundry / Azure AI Services** (`Microsoft.CognitiveServices/accounts`) — model pool endpoint with `disableLocalAuth: true` and `Cognitive Services OpenAI User` RBAC.
- **Azure Container Apps Environment & App** (`Microsoft.App/containerApps`) — hosts the ResearchWeave web workspace and API.
- **Log Analytics & Application Insights** — operational telemetry.

### CLI Deployment Option

```bash
az group create --name rg-researchweave --location eastus2 --tags SecurityControl=Ignore
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

- [Source-Verified Market & Open-Source Study](docs/autonomous-research-market-study-2026-11-14.md)
- [Product Specification](docs/research-system-specification-draft.md)
- [System Architecture Proposal](docs/researchweave-architecture-proposal.md)
- [Company Brain Technical Design](docs/researchweave-company-brain-proposal.md)
- [Core Components & Integration Gates](docs/researchweave-core-components-proposal.md)
- [Security & Autonomous Guardrails](SECURITY.md)

## License

Licensed under the [Apache License 2.0](LICENSE).
