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


def search_arxiv_live(query: str, max_results: int = 3, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Search ArXiv Atom API for mathematics, physics, astronomy, computer science, and quantitative biology papers."""
    # Extract ASCII / English scientific terms first so Hebrew prompts with English acronyms (e.g. JWST, DESI, Lambda-CDM) work cleanly
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,24}", query)
    if ascii_tokens:
        words = ascii_tokens[:5]
    else:
        clean_q = re.sub(r"[^\w\s-]", " ", query).strip()
        words = [w for w in clean_q.split() if len(w) > 2][:5]
    if not words:
        return []
    search_query = "+AND+".join(f"all:{urllib.parse.quote(w)}" for w in words)
    url = f"https://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results={max_results}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "ResearchWeave-OpenScientist/0.2"}
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
                    }
                )
        return papers
    except Exception:
        return []
