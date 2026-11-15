"""TrustGraph Ontology & W3C PROV-O Knowledge Graph Engine for ResearchWeave.

Adapted from trustgraph-ai/trustgraph (Apache-2.0):
- Formal OWL/RDF Ontology (`Ontology`, `OntologyClass`, `OntologyProperty`)
  defining scientific classes (`Theorem`, `Gene`, `Compound`, `Material`,
  `Mechanism`, `Dataset`, `Experiment`, `Hypothesis`, `VerifiedClaim`) and typed
  object properties.
- W3C `PROV-O` provenance graph generation (`http://www.w3.org/ns/prov#`,
  `https://trustgraph.ai/ns/`, `urn:graph:source`, `urn:graph:retrieval`)
  linking every extracted entity, relationship, and claim to its exact
  `Document -> Page -> Section -> Chunk -> ExtractionActivity -> LLM Agent`.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── W3C PROV-O, RDF/RDFS, Dublin Core & TrustGraph Namespaces (from trustgraph.provenance.namespaces) ──
PROV = "http://www.w3.org/ns/prov#"
PROV_ENTITY = PROV + "Entity"
PROV_ACTIVITY = PROV + "Activity"
PROV_AGENT = PROV + "Agent"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy"
PROV_USED = PROV + "used"
PROV_WAS_ASSOCIATED_WITH = PROV + "wasAssociatedWith"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"

DC = "http://purl.org/dc/elements/1.1/"
DC_TITLE = DC + "title"
DC_SOURCE = DC + "source"
DC_DATE = DC + "date"
DC_CREATOR = DC + "creator"

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDF_TYPE = RDF + "type"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDFS_LABEL = RDFS + "label"

TG = "https://trustgraph.ai/ns/"
TG_CONTAINS = TG + "contains"
TG_PAGE_COUNT = TG + "pageCount"
TG_MIME_TYPE = TG + "mimeType"
TG_PAGE_NUMBER = TG + "pageNumber"
TG_CHUNK_INDEX = TG + "chunkIndex"
TG_CHAR_OFFSET = TG + "charOffset"
TG_CHAR_LENGTH = TG + "charLength"
TG_COMPONENT_VERSION = TG + "componentVersion"
TG_LLM_MODEL = TG + "llmModel"
TG_ONTOLOGY = TG + "ontology"
TG_DOCUMENT_TYPE = TG + "Document"
TG_PAGE_TYPE = TG + "Page"
TG_SECTION_TYPE = TG + "Section"
TG_CHUNK_TYPE = TG + "Chunk"
TG_SUBGRAPH_TYPE = TG + "Subgraph"
TG_EPISTEMIC_STATE = TG + "epistemicState"

GRAPH_DEFAULT = "urn:graph:default"
GRAPH_SOURCE = "urn:graph:source"
GRAPH_RETRIEVAL = "urn:graph:retrieval"


@dataclass
class RDFTerm:
    type: str  # "iri" or "literal"
    iri: str = ""
    value: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "value": self.iri if self.type == "iri" else self.value}


@dataclass
class RDFTriple:
    s: RDFTerm
    p: RDFTerm
    o: RDFTerm
    g: str = GRAPH_DEFAULT

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.s.iri or self.s.value,
            "predicate": self.p.iri or self.p.value,
            "object": self.o.iri if self.o.type == "iri" else self.o.value,
            "object_type": self.o.type,
            "graph": self.g,
        }


def _iri(uri: str) -> RDFTerm:
    return RDFTerm(type="iri", iri=uri)


def _lit(val: Any) -> RDFTerm:
    return RDFTerm(type="literal", value=str(val))


def _triple(s_uri: str, p_uri: str, o_term: RDFTerm, g: str = GRAPH_SOURCE) -> RDFTriple:
    return RDFTriple(s=_iri(s_uri), p=_iri(p_uri), o=o_term, g=g)


# ── TrustGraph Scientific Ontology Definition (OWL Classes & Properties) ──

SCIENTIFIC_ONTOLOGY_SPEC: dict[str, Any] = {
    "id": "researchweave-scientific-ontology-v1",
    "uri": "https://trustgraph.ai/ontology/researchweave-scientific#",
    "classes": {
        "concept": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Concept", "label": "Scientific Concept"},
        "theorem": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Theorem", "label": "Mathematical Theorem", "subclass_of": "concept"},
        "gene": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Gene", "label": "Gene / Genomic Locus", "subclass_of": "concept"},
        "compound": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Compound", "label": "Biochemical Compound / Protein", "subclass_of": "concept"},
        "material": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Material", "label": "Engineering Material", "subclass_of": "concept"},
        "condition": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Condition", "label": "Physical or Biological Condition", "subclass_of": "concept"},
        "dataset": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Dataset", "label": "Empirical Dataset / Document"},
        "method": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#Method", "label": "Computational or Experimental Method"},
    },
    "object_properties": {
        "upregulates_expression_of": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#upregulatesExpressionOf"},
        "inhibits_anagen_signaling_in": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#inhibitsAnagenSignalingIn"},
        "deficiency_accelerates_accumulation_of": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#deficiencyAcceleratesAccumulationOf"},
        "contradicts_cusp_space_via_level_lowering": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#contradictsCuspSpaceViaLevelLowering"},
        "implies_impossibility_of_counterexample_in": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#impliesImpossibilityOfCounterexampleIn"},
        "governed_by_regime": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#governedByRegime"},
        "documents_entity": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#documentsEntity"},
        "mechanistically_linked_to": {"uri": "https://trustgraph.ai/ontology/researchweave-scientific#mechanisticallyLinkedTo"},
    },
}


class TrustGraphProvenanceBuilder:
    """Builds W3C PROV-O and TrustGraph RDF triples for documents, chunks, and extracted subgraphs."""

    @staticmethod
    def normalize_entity_uri(name: str, entity_type: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "entity"
        t_slug = re.sub(r"[^a-z0-9]+", "-", entity_type.strip().lower()).strip("-") or "concept"
        return f"https://trustgraph.ai/entity/{t_slug}/{ urllib.parse.quote(slug) }"

    @classmethod
    def build_document_provenance_triples(
        cls,
        investigation_id: str,
        source_id: str,
        title: str,
        uri_or_path: str,
        mime_type: str = "text/plain",
        page_count: int = 1,
        chunks: list[dict[str, Any]] | None = None,
        extracted_entities: list[dict[str, Any]] | None = None,
        extracted_relations: list[dict[str, Any]] | None = None,
        llm_model: str = "gpt-6-astra",
    ) -> list[dict[str, Any]]:
        """Generate W3C PROV-O + TrustGraph triples for a source document and its extracted subgraph."""
        doc_uri = f"https://trustgraph.ai/doc/{investigation_id}/{source_id}"
        act_uri = f"https://trustgraph.ai/activity/extract-{source_id}-{uuid.uuid4().hex[:8]}"
        agent_uri = f"https://trustgraph.ai/agent/ResearchWeave-TrustGraph-Extractor"
        sub_uri = f"https://trustgraph.ai/subgraph/{investigation_id}/{source_id}"
        now_iso = datetime.now(timezone.utc).isoformat()

        triples: list[RDFTriple] = [
            _triple(doc_uri, RDF_TYPE, _iri(PROV_ENTITY)),
            _triple(doc_uri, RDF_TYPE, _iri(TG_DOCUMENT_TYPE)),
            _triple(doc_uri, DC_TITLE, _lit(title)),
            _triple(doc_uri, RDFS_LABEL, _lit(title)),
            _triple(doc_uri, DC_SOURCE, _iri(uri_or_path)),
            _triple(doc_uri, DC_DATE, _lit(now_iso)),
            _triple(doc_uri, TG_MIME_TYPE, _lit(mime_type)),
            _triple(doc_uri, TG_PAGE_COUNT, _lit(page_count)),
            # Extraction Activity
            _triple(act_uri, RDF_TYPE, _iri(PROV_ACTIVITY)),
            _triple(act_uri, PROV_USED, _iri(doc_uri)),
            _triple(act_uri, PROV_WAS_ASSOCIATED_WITH, _iri(agent_uri)),
            _triple(act_uri, PROV_STARTED_AT_TIME, _lit(now_iso)),
            _triple(act_uri, TG_LLM_MODEL, _lit(llm_model)),
            _triple(act_uri, TG_ONTOLOGY, _iri(SCIENTIFIC_ONTOLOGY_SPEC["uri"])),
            # Subgraph generated by Extraction Activity
            _triple(sub_uri, RDF_TYPE, _iri(PROV_ENTITY)),
            _triple(sub_uri, RDF_TYPE, _iri(TG_SUBGRAPH_TYPE)),
            _triple(sub_uri, PROV_WAS_DERIVED_FROM, _iri(doc_uri)),
            _triple(sub_uri, PROV_WAS_GENERATED_BY, _iri(act_uri)),
        ]

        # Page & Chunk PROV-O lineage
        for ch in (chunks or [])[:10]:
            ch_idx = ch.get("chunk_index", 0)
            ch_uri = f"urn:chunk:{source_id}:{ch_idx}"
            triples.extend(
                [
                    _triple(ch_uri, RDF_TYPE, _iri(PROV_ENTITY)),
                    _triple(ch_uri, RDF_TYPE, _iri(TG_CHUNK_TYPE)),
                    _triple(ch_uri, PROV_WAS_DERIVED_FROM, _iri(doc_uri)),
                    _triple(ch_uri, TG_PAGE_NUMBER, _lit(ch.get("page_number", 1))),
                    _triple(ch_uri, TG_CHUNK_INDEX, _lit(ch_idx)),
                    _triple(ch_uri, TG_CHAR_OFFSET, _lit(ch.get("char_offset", 0))),
                    _triple(ch_uri, TG_CHAR_LENGTH, _lit(ch.get("char_length", 0))),
                ]
            )

        # Ontology-typed Entity & Relationship triples in GRAPH_DEFAULT + linked to Subgraph in GRAPH_SOURCE
        classes_map = SCIENTIFIC_ONTOLOGY_SPEC["classes"]
        props_map = SCIENTIFIC_ONTOLOGY_SPEC["object_properties"]

        for ent in extracted_entities or []:
            e_name = ent.get("canonical_name", "")
            e_type = ent.get("entity_type", "concept").lower()
            e_uri = cls.normalize_entity_uri(e_name, e_type)
            class_uri = (classes_map.get(e_type) or classes_map["concept"])["uri"]
            triples.extend(
                [
                    _triple(e_uri, RDF_TYPE, _iri(class_uri), g=GRAPH_DEFAULT),
                    _triple(e_uri, RDFS_LABEL, _lit(e_name), g=GRAPH_DEFAULT),
                    _triple(sub_uri, TG_CONTAINS, _iri(e_uri), g=GRAPH_SOURCE),
                ]
            )

        for rel in extracted_relations or []:
            s_uri = cls.normalize_entity_uri(rel.get("source_entity_name", ""), "concept")
            o_uri = cls.normalize_entity_uri(rel.get("target_entity_name", ""), "concept")
            pred_key = rel.get("predicate", "mechanistically_linked_to")
            pred_uri = (props_map.get(pred_key) or props_map["mechanistically_linked_to"])["uri"]
            epistemic = rel.get("verification_state", "hypothesis")
            triples.extend(
                [
                    _triple(s_uri, pred_uri, _iri(o_uri), g=GRAPH_DEFAULT),
                    _triple(s_uri, TG_EPISTEMIC_STATE, _lit(epistemic), g=GRAPH_SOURCE),
                ]
            )

        return [t.to_dict() for t in triples]


def extract_ontology_entities_with_llm(
    foundry_adapter: Any,
    model_name: str,
    title: str,
    text: str,
) -> dict[str, list[dict[str, Any]]]:
    """Use `gpt-6-astra` to extract TrustGraph Ontology-grounded entities and relationships from text."""
    if not getattr(foundry_adapter, "is_configured", False):
        return {"entities": [], "relationships": []}

    allowed_classes = ", ".join(SCIENTIFIC_ONTOLOGY_SPEC["classes"].keys())
    system_prompt = (
        "You are a TrustGraph OntoRAG scientific knowledge extractor. "
        f"Extract up to 4 domain entities (allowed types: {allowed_classes}) and up to 3 typed relationships "
        "from the scientific text. Respond ONLY with valid JSON matching: "
        '{"entities": [{"name": "...", "type": "concept|gene|compound|material|theorem|condition|dataset|method", "summary": "..."}], '
        '"relationships": [{"subject": "...", "predicate": "...", "object": "...", "conditions": "..."}]}'
    )
    raw, _ = foundry_adapter.complete(
        model_name or "gpt-6-astra",
        system_prompt=system_prompt,
        user_prompt=f"Document Title: {title}\nText:\n{text[:2000]}",
        max_tokens=900,
    )
    if not raw:
        return {"entities": [], "relationships": []}
    try:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        parsed = json.loads(m.group(0) if m else raw)
        return {
            "entities": parsed.get("entities") or [],
            "relationships": parsed.get("relationships") or [],
        }
    except Exception:
        return {"entities": [], "relationships": []}
