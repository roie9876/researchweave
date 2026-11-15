"""OpenScientist Discovery Loop, KnowledgeState & Live Scientific Literature Engine.

Adapted from openscientist-io/openscientist (Apache-2.0):
- KnowledgeState: iterative tracking of hypotheses (H001+), findings (F001+) with
  abstract-snippet citation validation, literature (L001+), analysis_log, and
  iteration summaries.
- Live scientific literature retrieval from NCBI PubMed E-utilities (esearch + efetch XML)
  and ArXiv Atom API (export.arxiv.org), with automatic offline resilience.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any


class OpenScientistKnowledgeState:
    """OpenScientist-compatible KnowledgeState tracking iterative scientific discovery."""

    def __init__(self, job_id: str, research_question: str, max_iterations: int = 5) -> None:
        self.data: dict[str, Any] = {
            "config": {
                "job_id": job_id,
                "research_question": research_question,
                "max_iterations": max_iterations,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "engine": "OpenScientist-Discovery-Loop",
            },
            "data_summary": {},
            "iteration": 1,
            "hypotheses": [],
            "findings": [],
            "literature": [],
            "analysis_log": [],
            "iteration_summaries": [],
            "feedback_history": [],
            "agent_status": "initializing",
            "agent_status_updated_at": datetime.now(timezone.utc).isoformat(),
            "consensus_answer": None,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OpenScientistKnowledgeState":
        cfg = payload.get("config") or {}
        inst = cls(
            job_id=cfg.get("job_id", "unknown"),
            research_question=cfg.get("research_question", ""),
            max_iterations=int(cfg.get("max_iterations", 5)),
        )
        inst.data.update(payload)
        return inst

    def to_dict(self) -> dict[str, Any]:
        return self.data

    def add_hypothesis(self, statement: str, proposed_by: str = "agent") -> str:
        hypothesis_id = f"H{len(self.data['hypotheses']) + 1:03d}"
        self.data["hypotheses"].append(
            {
                "id": hypothesis_id,
                "iteration_proposed": self.data["iteration"],
                "statement": statement,
                "status": "pending",
                "proposed_by": proposed_by,
                "tested_at_iteration": None,
                "test_code": None,
                "result": None,
                "spawned_hypotheses": [],
            }
        )
        return hypothesis_id

    def update_hypothesis(self, hypothesis_id: str, updates: dict[str, Any]) -> None:
        for hyp in self.data["hypotheses"]:
            if hyp["id"] == hypothesis_id:
                hyp.update(updates)
                return

    def validate_citation(self, citation: dict[str, str]) -> dict[str, str]:
        """OpenScientist citation validator: verifies citation snippets against retrieved abstracts."""
        result = dict(citation)
        paper_id = str(result.get("pmid") or result.get("paper_id") or "")
        snippet = result.get("snippet", "")

        abstract = None
        for lit in self.data["literature"]:
            if str(lit.get("pmid")) == paper_id or str(lit.get("id")) == paper_id:
                abstract = lit.get("abstract", "")
                break

        if abstract is None:
            result["validation_status"] = "unchecked"
        elif not snippet:
            result["validation_status"] = "mismatch"
        elif snippet in abstract:
            result["validation_status"] = "verified"
        else:
            def _norm(s: str) -> str:
                s = re.sub(r"\s+", " ", s.lower().strip())
                return s.strip(".,;:!?\"'()[]{}")

            if _norm(snippet) and _norm(snippet) in _norm(abstract):
                result["validation_status"] = "verified_normalized"
            else:
                result["validation_status"] = "mismatch"
        return result

    def add_finding(
        self,
        title: str,
        evidence: str,
        supporting_hypotheses: list[str] | None = None,
        literature_support: list[str] | None = None,
        citations: list[dict[str, str]] | None = None,
        biological_or_physical_interpretation: str = "",
    ) -> str:
        finding_id = f"F{len(self.data['findings']) + 1:03d}"
        validated_citations = [self.validate_citation(c) for c in (citations or [])]
        self.data["findings"].append(
            {
                "id": finding_id,
                "iteration_discovered": self.data["iteration"],
                "title": title,
                "evidence": evidence,
                "supporting_hypotheses": supporting_hypotheses or [],
                "literature_support": literature_support or [],
                "biological_interpretation": biological_or_physical_interpretation,
                "citations": validated_citations,
            }
        )
        return finding_id

    def add_literature(
        self,
        pmid: str,
        title: str,
        abstract: str,
        authors: str = "",
        year: str = "",
        uri: str = "",
        source_db: str = "pubmed",
        search_query: str | None = None,
    ) -> str:
        literature_id = f"L{len(self.data['literature']) + 1:03d}"
        self.data["literature"].append(
            {
                "id": literature_id,
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "uri": uri,
                "source_db": source_db,
                "retrieved_at_iteration": self.data["iteration"],
                "search_query": search_query,
            }
        )
        return literature_id

    def log_analysis(self, action: str, code: str | None = None, output: str | None = None) -> None:
        self.data["analysis_log"].append(
            {
                "iteration": self.data["iteration"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "code": code,
                "output": output,
            }
        )


def search_pubmed_live(query: str, max_results: int = 3, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Search NCBI PubMed E-utilities (adapted from openscientist.literature.search_pubmed)."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"}
    )
    try:
        req = urllib.request.Request(
            f"{base_url}/esearch.fcgi?{params}",
            headers={"User-Agent": "ResearchWeave-OpenScientist/0.2"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json

            search_data = json.loads(resp.read().decode("utf-8"))
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        fetch_params = urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
        )
        fetch_req = urllib.request.Request(
            f"{base_url}/efetch.fcgi?{fetch_params}",
            headers={"User-Agent": "ResearchWeave-OpenScientist/0.2"},
        )
        with urllib.request.urlopen(fetch_req, timeout=timeout) as fetch_resp:
            xml_text = fetch_resp.read().decode("utf-8", errors="replace")
        return _parse_pubmed_xml(xml_text)
    except Exception:
        return []


def _parse_pubmed_xml(xml_text: str) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            pmid = (pmid_elem.text or "").strip() if pmid_elem is not None else "Unknown"
            title_elem = article.find(".//ArticleTitle")
            title = "".join(title_elem.itertext()).strip() if title_elem is not None else "No title"
            abstract_elems = article.findall(".//AbstractText")
            abstract = " ".join(
                "".join(e.itertext()).strip() for e in abstract_elems if "".join(e.itertext()).strip()
            )
            author_elems = article.findall(".//Author/LastName")
            authors = ", ".join(e.text for e in author_elems if e.text)
            year_elem = article.find(".//PubDate/Year")
            year = (year_elem.text or "").strip() if year_elem is not None else ""
            if title and abstract:
                papers.append(
                    {
                        "pmid": pmid,
                        "title": f"{title} ({authors}, {year})".strip(" (,)") if authors or year else title,
                        "abstract": abstract[:900],
                        "authors": authors,
                        "year": year,
                        "uri": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "source_db": "pubmed",
                    }
                )
    except Exception:
        return []
    return papers


def search_arxiv_live(query: str, max_results: int = 8, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search ArXiv Atom API for mathematics, physics, astronomy, electrical/CS, and quantitative biology papers."""
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,24}", query)
    if ascii_tokens:
        words = ascii_tokens[:6]
    else:
        clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
        words = [w for w in clean_q.split() if len(w) > 2][:6]
    if not words:
        return []
    search_query = "+AND+".join(f"all:{urllib.parse.quote(w)}" for w in words)
    url = f"https://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results={max_results}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", ns):
            id_elem = entry.find("atom:id", ns)
            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            published_elem = entry.find("atom:published", ns)
            authors = [
                (a.find("atom:name", ns).text or "").strip()
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None
            ]
            uri = (id_elem.text or "").strip() if id_elem is not None else ""
            arxiv_id = uri.rsplit("/", 1)[-1] if uri else "arxiv"
            title = re.sub(r"\s+", " ", (title_elem.text or "").strip()) if title_elem is not None else ""
            abstract = re.sub(r"\s+", " ", (summary_elem.text or "").strip()) if summary_elem is not None else ""
            year = (published_elem.text or "")[:4] if published_elem is not None else ""
            if title and abstract:
                papers.append(
                    {
                        "pmid": f"arXiv:{arxiv_id}",
                        "title": f"{title} ({', '.join(authors[:3])}, {year})".strip(" (,)"),
                        "abstract": abstract[:900],
                        "authors": ", ".join(authors[:4]),
                        "year": year,
                        "uri": uri or f"https://arxiv.org/abs/{arxiv_id}",
                        "source_db": "arxiv",
                        "citations": 0,
                    }
                )
        return papers
    except Exception:
        return []


def _reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_map: dict[int, str] = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for p in positions:
                if isinstance(p, int) and p < 400:
                    pos_map[p] = word
    if not pos_map:
        return ""
    return " ".join(pos_map[idx] for idx in sorted(pos_map.keys()))


def search_openalex_live(query: str, max_results: int = 10, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search OpenAlex (250M+ works across IEEE, ACS, RSC, APS, Nature, Science, Elsevier, Springer, NEJM)."""
    import json

    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    if not clean_q:
        return []
    params = urllib.parse.urlencode(
        {
            "search": clean_q,
            "per-page": max_results,
            "mailto": "researcher@researchweave.org",
        }
    )
    url = f"https://api.openalex.org/works?{params}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3 (mailto:researcher@researchweave.org)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        papers: list[dict[str, Any]] = []
        for item in data.get("results") or []:
            title = (item.get("display_name") or item.get("title") or "").strip()
            if not title:
                continue
            abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
            if not abstract:
                concepts = [c.get("display_name", "") for c in (item.get("concepts") or [])[:6] if c.get("display_name")]
                abstract = f"Peer-reviewed work indexed in OpenAlex. Key concepts: {', '.join(concepts)}."
            authorships = item.get("authorships") or []
            authors = [
                (a.get("author") or {}).get("display_name", "")
                for a in authorships[:4]
                if (a.get("author") or {}).get("display_name")
            ]
            year = str(item.get("publication_year") or "")
            cited_by = int(item.get("cited_by_count") or 0)
            doi = item.get("doi") or item.get("id") or ""
            oa_id = (item.get("id") or "").rsplit("/", 1)[-1]
            venue = ((item.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
            venue_tag = f" [{venue}]" if venue else ""
            papers.append(
                {
                    "pmid": f"OpenAlex:{oa_id}",
                    "title": f"{title}{venue_tag} ({', '.join(authors[:3])}, {year}; Citations: {cited_by})".strip(" (,)"),
                    "abstract": abstract[:900],
                    "authors": ", ".join(authors),
                    "year": year,
                    "uri": doi or f"https://openalex.org/{oa_id}",
                    "source_db": "openalex",
                    "citations": cited_by,
                }
            )
        return papers
    except Exception:
        return []


def search_semanticscholar_live(query: str, max_results: int = 8, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search Semantic Scholar Academic Graph (IEEE, ACM, Chemistry, Physics, Materials, Medicine)."""
    import json

    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    if not clean_q:
        return []
    params = urllib.parse.urlencode(
        {
            "query": clean_q,
            "limit": max_results,
            "fields": "title,abstract,year,authors,citationCount,venue,url,externalIds",
        }
    )
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        papers: list[dict[str, Any]] = []
        for item in data.get("data") or []:
            title = (item.get("title") or "").strip()
            abstract = (item.get("abstract") or "").strip()
            if not title or not abstract:
                continue
            authors = [a.get("name", "") for a in (item.get("authors") or [])[:4] if a.get("name")]
            year = str(item.get("year") or "")
            cited_by = int(item.get("citationCount") or 0)
            venue = (item.get("venue") or "").strip()
            ext_ids = item.get("externalIds") or {}
            doi = ext_ids.get("DOI")
            uri = f"https://doi.org/{doi}" if doi else (item.get("url") or "https://www.semanticscholar.org/")
            pid = (item.get("paperId") or "")[:10]
            venue_tag = f" [{venue}]" if venue else ""
            papers.append(
                {
                    "pmid": f"S2:{pid}",
                    "title": f"{title}{venue_tag} ({', '.join(authors[:3])}, {year}; Citations: {cited_by})".strip(" (,)"),
                    "abstract": abstract[:900],
                    "authors": ", ".join(authors),
                    "year": year,
                    "uri": uri,
                    "source_db": "semanticscholar",
                    "citations": cited_by,
                }
            )
        return papers
    except Exception:
        return []


def search_europepmc_live(query: str, max_results: int = 8, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search Europe PMC (PubMed + PMC full-text + medRxiv/bioRxiv + biochemistry/pharmacology, sorted by citations)."""
    import json

    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    if not clean_q:
        return []
    params = urllib.parse.urlencode(
        {
            "query": clean_q,
            "format": "json",
            "pageSize": max_results,
            "resultType": "core",
        }
    )
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        results = ((data.get("resultList") or {}).get("result")) or []
        papers: list[dict[str, Any]] = []
        for item in results:
            title = (item.get("title") or "").strip()
            abstract = re.sub(r"<[^>]+>", " ", (item.get("abstractText") or "")).strip()
            if not title or not abstract:
                continue
            authors = (item.get("authorString") or "").strip()
            year = str(item.get("pubYear") or "")
            cited_by = int(item.get("citedByCount") or 0)
            pmid = item.get("pmid") or item.get("id") or "EPMC"
            doi = item.get("doi")
            uri = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/MED/{pmid}"
            journal = (item.get("journalTitle") or "").strip()
            j_tag = f" [{journal}]" if journal else ""
            papers.append(
                {
                    "pmid": f"EPMC:{pmid}",
                    "title": f"{title}{j_tag} ({authors[:50]}, {year}; Citations: {cited_by})".strip(" (,)"),
                    "abstract": abstract[:900],
                    "authors": authors[:80],
                    "year": year,
                    "uri": uri,
                    "source_db": "europepmc",
                    "citations": cited_by,
                }
            )
        return papers
    except Exception:
        return []


def search_crossref_live(query: str, max_results: int = 6, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search Crossref DOI Registry (150M+ journal articles across IEEE, ACS, RSC, Elsevier, Springer, Wiley)."""
    import json

    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    if not clean_q:
        return []
    params = urllib.parse.urlencode({"query": clean_q, "rows": max_results})
    url = f"https://api.crossref.org/works?{params}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3 (mailto:researcher@researchweave.org)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        items = ((data.get("message") or {}).get("items")) or []
        papers: list[dict[str, Any]] = []
        for item in items:
            titles = item.get("title") or []
            title = titles[0].strip() if titles else ""
            if not title:
                continue
            doi = (item.get("DOI") or "").strip()
            abstract_raw = item.get("abstract") or ""
            abstract = re.sub(r"<[^>]+>", " ", abstract_raw).strip()
            container = item.get("container-title") or []
            journal = container[0] if container else "Peer-Reviewed Journal"
            cited_by = int(item.get("is-referenced-by-count") or 0)
            authors_list = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in (item.get("author") or [])[:4]
            ]
            issued = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
            year = str(issued[0] or "")
            if not abstract:
                abstract = f"Published in {journal} ({year}). DOI: {doi}. Referenced by {cited_by} peer-reviewed works."
            papers.append(
                {
                    "pmid": f"DOI:{doi}" if doi else "Crossref",
                    "title": f"{title} [{journal}] ({', '.join(a for a in authors_list if a)}, {year}; Citations: {cited_by})",
                    "abstract": abstract[:900],
                    "authors": ", ".join(a for a in authors_list if a),
                    "year": year,
                    "uri": f"https://doi.org/{doi}" if doi else "https://www.crossref.org/",
                    "source_db": "crossref",
                    "citations": cited_by,
                }
            )
        return papers
    except Exception:
        return []


def search_pubchem_live(query: str, max_results: int = 4, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search NIH PubChem PUG REST API for chemical compounds, molecular formulas, IUPAC names, and properties."""
    import json

    # Extract candidate chemical/compound/material names (English tokens)
    tokens = [
        t
        for t in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,28}", query)
        if t.lower() not in {"the", "and", "for", "with", "from", "how", "why", "what", "study", "analyze", "effect", "reaction", "synthesis", "chemistry", "chemical"}
    ]
    results: list[dict[str, Any]] = []
    for chem in tokens[: max_results]:
        url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(chem)}"
            "/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES/JSON"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            props = ((data.get("PropertyTable") or {}).get("Properties")) or []
            if props:
                p = props[0]
                cid = p.get("CID")
                formula = p.get("MolecularFormula", "")
                mw = p.get("MolecularWeight", "")
                iupac = p.get("IUPACName", "")
                smiles = p.get("CanonicalSMILES", "")
                results.append(
                    {
                        "pmid": f"PubChem-CID:{cid}",
                        "title": f"PubChem Compound Record: {chem} (CID {cid} — Formula: {formula}, MW: {mw} g/mol)",
                        "abstract": f"Chemical Compound {chem} (PubChem CID {cid}): Molecular Formula={formula}, Molecular Weight={mw} g/mol, IUPAC Name={iupac}, Canonical SMILES={smiles}.",
                        "authors": "NIH NCBI PubChem Database",
                        "year": "2026",
                        "uri": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                        "source_db": "pubchem",
                        "citations": 50,
                    }
                )
        except Exception:
            continue
    return results


def search_clinicaltrials_live(query: str, max_results: int = 5, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Search ClinicalTrials.gov API v2 for human clinical studies, interventions, and outcomes."""
    import json

    clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
    if not clean_q:
        return []
    params = urllib.parse.urlencode({"query.term": clean_q, "pageSize": max_results})
    url = f"https://clinicaltrials.gov/api/v2/studies?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.3"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        papers: list[dict[str, Any]] = []
        for st in data.get("studies") or []:
            proto = st.get("protocolSection") or {}
            ident = proto.get("identificationModule") or {}
            status_mod = proto.get("statusModule") or {}
            desc_mod = proto.get("descriptionModule") or {}
            nct_id = ident.get("nctId", "NCT")
            title = ident.get("officialTitle") or ident.get("briefTitle") or ""
            summary = desc_mod.get("briefSummary") or ""
            overall_status = status_mod.get("overallStatus") or ""
            if title and summary:
                papers.append(
                    {
                        "pmid": nct_id,
                        "title": f"[ClinicalTrial {nct_id}] {title} (Status: {overall_status})",
                        "abstract": re.sub(r"\s+", " ", summary)[:900],
                        "authors": "ClinicalTrials.gov Registry",
                        "year": "",
                        "uri": f"https://clinicaltrials.gov/study/{nct_id}",
                        "source_db": "clinicaltrials",
                        "citations": 15,
                    }
                )
        return papers
    except Exception:
        return []


def search_federated_scientific_literature(
    queries: list[str],
    domain: str,
    timeout: float = 6.5,
) -> list[dict[str, Any]]:
    """Federated, uncapped multi-database scientific search across OpenAlex, Semantic Scholar, Crossref, ArXiv, Europe PMC, PubMed, PubChem, and ClinicalTrials.gov.

    Executes all sub-queries across all relevant scientific databases in parallel,
    deduplicates by URI/title, and sorts by citation impact + relevance without an artificial paper cap.
    """
    import concurrent.futures

    tasks_to_run: list[tuple[str, Any, str, int]] = []
    for q in queries:
        if not q.strip():
            continue
        # Universal scientific databases (cover ALL fields: Chemistry, Electrical Eng, Materials, Physics, Math, Medicine, CS)
        tasks_to_run.append(("openalex", search_openalex_live, q, 8))
        tasks_to_run.append(("semanticscholar", search_semanticscholar_live, q, 6))
        tasks_to_run.append(("crossref", search_crossref_live, q, 5))

        # Domain-specialized databases
        if domain in ("mathematics_fermat", "mathematics", "cosmology_astrophysics", "engineering", "electrical_engineering", "general_science"):
            tasks_to_run.append(("arxiv", search_arxiv_live, q, 6))
        if domain in ("chemistry", "materials_science", "genetics", "neurology", "medicine_health", "general_science"):
            tasks_to_run.append(("europepmc", search_europepmc_live, q, 6))
            tasks_to_run.append(("pubmed", search_pubmed_live, q, 5))
        if domain in ("chemistry", "materials_science", "genetics", "neurology", "medicine_health"):
            tasks_to_run.append(("pubchem", search_pubchem_live, q, 3))
        if domain in ("genetics", "neurology", "medicine_health"):
            tasks_to_run.append(("clinicaltrials", search_clinicaltrials_live, q, 4))

    collected: list[dict[str, Any]] = []
    if not tasks_to_run:
        return collected

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, len(tasks_to_run))) as pool:
        future_map = [
            (db_name, q_str, pool.submit(fn, q_str, limit, timeout))
            for db_name, fn, q_str, limit in tasks_to_run
        ]
        for db_name, q_str, fut in future_map:
            try:
                res_list = fut.result(timeout=timeout + 1.5)
                for item in res_list:
                    item["query"] = q_str
                    collected.append(item)
            except Exception:
                continue

    # Deduplicate by normalized URI and normalized title, and score lexical relevance against the sub-queries
    query_terms = {
        w.lower()
        for q in queries
        for w in re.findall(r"[A-Za-z0-9]{3,}", q)
        if w.lower() not in {"the", "and", "for", "with", "from", "how", "why", "what", "study", "analysis", "model", "between", "using", "into"}
    }

    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for p in collected:
        title_str = (p.get("title") or "").strip()
        abs_str = (p.get("abstract") or "").strip()
        norm_title = re.sub(r"[^a-z0-9]+", "", title_str.lower())[:65]
        norm_uri = (p.get("uri") or "").strip().lower().rstrip("/")
        key = norm_uri or norm_title
        if not key or key in seen_keys or (norm_title and norm_title in seen_keys):
            continue

        # Relevance filter: ensure the paper matches at least one query term (or is a direct PubChem/ArXiv hit)
        combined_lower = f"{title_str} {abs_str}".lower()
        matched_terms = sum(1 for qt in query_terms if qt in combined_lower) if query_terms else 1
        if query_terms and matched_terms == 0 and p.get("source_db") in ("crossref", "openalex", "europepmc"):
            continue

        seen_keys.add(key)
        if norm_title:
            seen_keys.add(norm_title)
        p["relevance_matches"] = matched_terms
        p["rank_score"] = (matched_terms * 50) + min(500, int(p.get("citations") or 0))
        deduped.append(p)

    # Sort by combined relevance + citation impact
    deduped.sort(key=lambda x: int(x.get("rank_score") or 0), reverse=True)
    return deduped
