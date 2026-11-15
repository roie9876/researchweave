"""Durable state store and Company Brain engine for ResearchWeave.

Provides:
1. Canonical persistence for investigations, objective history, tasks, specialist agents,
   conversation messages, timeline events, and reports.
2. Company Brain knowledge graph: ontology-guided entity & relation extraction,
   PROV-O-style source provenance, contradiction tracking, source deletion propagation,
   and scoped multi-hop graph + keyword retrieval across selected investigations.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import (
    BrainEntity,
    BrainRelation,
    ClaimRecord,
    ConversationMessage,
    ResearchTask,
    SourceRecord,
    SpecialistAgent,
    TimelineEvent,
    VerificationState,
    utc_now_iso,
)


class ResearchWeaveStore:
    """Thread-safe SQLite-backed durable state and Company Brain knowledge graph."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS approved_users (
                    email TEXT PRIMARY KEY,
                    role TEXT NOT NULL DEFAULT 'researcher',
                    approved_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    language TEXT NOT NULL,
                    report_language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    autonomy_mode TEXT NOT NULL,
                    approval_policy_json TEXT NOT NULL,
                    stopping_conditions_json TEXT NOT NULL,
                    model_pool_json TEXT NOT NULL,
                    reference_links_json TEXT NOT NULL,
                    reused_investigation_ids_json TEXT NOT NULL,
                    collaborators_json TEXT NOT NULL,
                    objective_history_json TEXT NOT NULL,
                    clarifying_questions_json TEXT NOT NULL,
                    clarification_answers TEXT NOT NULL DEFAULT '',
                    blob_container TEXT NOT NULL,
                    estimated_spend_usd REAL NOT NULL DEFAULT 0.0,
                    runtime_seconds REAL NOT NULL DEFAULT 0.0,
                    draft_report_markdown TEXT NOT NULL DEFAULT '',
                    pause_reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    deleted INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS brain_entities (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    canonical_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS brain_relations (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    verification_state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            # Ensure default installation owner is approved
            conn.execute(
                """
                INSERT OR IGNORE INTO approved_users (email, role, approved_by, created_at)
                VALUES (?, ?, ?, ?)
                """,
                ("researcher@researchweave.local", "owner", "system-bootstrap", utc_now_iso()),
            )
            conn.commit()

    # ── Approved Microsoft Accounts ───────────────────────────────────────

    def approve_user(self, email: str, role: str = "researcher", approved_by: str = "owner") -> dict[str, str]:
        normalized = email.strip().lower()
        now = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO approved_users (email, role, approved_by, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (normalized, role, approved_by, now),
            )
            conn.commit()
        return {"email": normalized, "role": role, "approved_by": approved_by, "created_at": now}

    def list_approved_users(self) -> list[dict[str, str]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT email, role, approved_by, created_at FROM approved_users ORDER BY created_at ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def is_user_approved(self, email: str) -> bool:
        normalized = email.strip().lower()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM approved_users WHERE email = ?", (normalized,)
            ).fetchone()
        return row is not None

    # ── Investigations & Single-Active-Run Enforcement ────────────────────

    def get_running_investigation_for_owner(
        self, owner: str, exclude_id: str | None = None
    ) -> dict[str, Any] | None:
        normalized = owner.strip().lower()
        with self._lock, self._connect() as conn:
            if exclude_id:
                row = conn.execute(
                    "SELECT * FROM investigations WHERE lower(owner) = ? AND status = 'running' AND id != ? LIMIT 1",
                    (normalized, exclude_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM investigations WHERE lower(owner) = ? AND status = 'running' LIMIT 1",
                    (normalized,),
                ).fetchone()
        return self._deserialize_investigation(row) if row else None

    def save_investigation(self, inv: dict[str, Any]) -> dict[str, Any]:
        inv["updated_at"] = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO investigations (
                    id, title, objective, owner, language, report_language, status,
                    autonomy_mode, approval_policy_json, stopping_conditions_json,
                    model_pool_json, reference_links_json, reused_investigation_ids_json,
                    collaborators_json, objective_history_json, clarifying_questions_json,
                    clarification_answers, blob_container, estimated_spend_usd,
                    runtime_seconds, draft_report_markdown, pause_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inv["id"],
                    inv["title"],
                    inv["objective"],
                    inv["owner"],
                    inv["language"],
                    inv["report_language"],
                    inv["status"],
                    inv["autonomy_mode"],
                    json.dumps(inv["approval_policy"]),
                    json.dumps(inv["stopping_conditions"]),
                    json.dumps(inv["model_pool"]),
                    json.dumps(inv["reference_links"]),
                    json.dumps(inv["reused_investigation_ids"]),
                    json.dumps(inv.get("collaborators", [])),
                    json.dumps(inv["objective_history"]),
                    json.dumps(inv["clarifying_questions"]),
                    inv.get("clarification_answers", ""),
                    inv["blob_container"],
                    float(inv.get("estimated_spend_usd", 0.0)),
                    float(inv.get("runtime_seconds", 0.0)),
                    inv.get("draft_report_markdown", ""),
                    inv.get("pause_reason", ""),
                    inv["created_at"],
                    inv["updated_at"],
                ),
            )
            conn.commit()
        return inv

    def _deserialize_investigation(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "objective": row["objective"],
            "owner": row["owner"],
            "language": row["language"],
            "report_language": row["report_language"],
            "status": row["status"],
            "autonomy_mode": row["autonomy_mode"],
            "approval_policy": json.loads(row["approval_policy_json"]),
            "stopping_conditions": json.loads(row["stopping_conditions_json"]),
            "model_pool": json.loads(row["model_pool_json"]),
            "reference_links": json.loads(row["reference_links_json"]),
            "reused_investigation_ids": json.loads(row["reused_investigation_ids_json"]),
            "collaborators": json.loads(row["collaborators_json"]),
            "objective_history": json.loads(row["objective_history_json"]),
            "clarifying_questions": json.loads(row["clarifying_questions_json"]),
            "clarification_answers": row["clarification_answers"],
            "blob_container": row["blob_container"],
            "estimated_spend_usd": row["estimated_spend_usd"],
            "runtime_seconds": row["runtime_seconds"],
            "draft_report_markdown": row["draft_report_markdown"],
            "pause_reason": row["pause_reason"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_investigation(self, investigation_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
            ).fetchone()
        return self._deserialize_investigation(row) if row else None

    def list_investigations(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM investigations ORDER BY updated_at DESC"
            ).fetchall()
        return [self._deserialize_investigation(r) for r in rows]

    def delete_investigation(self, investigation_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM investigations WHERE id = ?", (investigation_id,))
            for table in (
                "agents",
                "tasks",
                "sources",
                "brain_entities",
                "brain_relations",
                "claims",
                "messages",
                "timeline_events",
            ):
                conn.execute(f"DELETE FROM {table} WHERE investigation_id = ?", (investigation_id,))
            conn.commit()
        return cur.rowcount > 0

    # ── Agents, Tasks, Messages, Timeline ─────────────────────────────────

    def upsert_agent(self, agent: SpecialistAgent) -> SpecialistAgent:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agents (id, investigation_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (agent.id, agent.investigation_id, agent.model_dump_json(), agent.created_at),
            )
            conn.commit()
        return agent

    def list_agents(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM agents WHERE investigation_id = ? ORDER BY created_at ASC",
                (investigation_id,),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def upsert_task(self, task: ResearchTask) -> ResearchTask:
        task.updated_at = utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks (id, investigation_id, status, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task.id, task.investigation_id, task.status.value, task.model_dump_json(), task.updated_at),
            )
            conn.commit()
        return task

    def list_tasks(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM tasks WHERE investigation_id = ? ORDER BY updated_at ASC",
                (investigation_id,),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def add_message(self, msg: ConversationMessage) -> ConversationMessage:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages (id, investigation_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (msg.id, msg.investigation_id, msg.model_dump_json(), msg.created_at),
            )
            conn.commit()
        return msg

    def list_messages(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM messages WHERE investigation_id = ? ORDER BY created_at ASC",
                (investigation_id,),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def append_event(
        self,
        investigation_id: str,
        event_type: str,
        actor: str,
        summary: str,
        details: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        now = utc_now_iso()
        details_dict = details or {}
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO timeline_events (investigation_id, event_type, actor, summary, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (investigation_id, event_type, actor, summary, json.dumps(details_dict), now),
            )
            event_id = int(cur.lastrowid or 0)
            conn.commit()
        return TimelineEvent(
            id=event_id,
            investigation_id=investigation_id,
            event_type=event_type,
            actor=actor,
            summary=summary,
            details=details_dict,
            created_at=now,
        )

    def list_events(self, investigation_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, investigation_id, event_type, actor, summary, details_json, created_at
                FROM timeline_events
                WHERE investigation_id = ? AND id > ?
                ORDER BY id ASC
                """,
                (investigation_id, after_id),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "investigation_id": r["investigation_id"],
                "event_type": r["event_type"],
                "actor": r["actor"],
                "summary": r["summary"],
                "details": json.loads(r["details_json"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ── Company Brain: Sources, Knowledge Graph, Claims & Provenance ─────

    def add_source(self, source: SourceRecord) -> SourceRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sources (id, investigation_id, deleted, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.investigation_id,
                    1 if source.deleted else 0,
                    source.model_dump_json(),
                    source.created_at,
                ),
            )
            conn.commit()
        return source

    def list_sources(
        self, investigation_id: str, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            if include_deleted:
                rows = conn.execute(
                    "SELECT payload_json FROM sources WHERE investigation_id = ? ORDER BY created_at ASC",
                    (investigation_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM sources WHERE investigation_id = ? AND deleted = 0 ORDER BY created_at ASC",
                    (investigation_id,),
                ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def upsert_entity(self, entity: BrainEntity) -> BrainEntity:
        """Conservatively merge by canonical name within an investigation or insert new."""
        existing = self.find_entity_by_name(entity.investigation_id, entity.canonical_name)
        if existing:
            merged_sources = sorted(set(existing["source_ids"]) | set(entity.source_ids))
            merged_aliases = sorted(set(existing["aliases"]) | set(entity.aliases))
            updated = BrainEntity(
                id=existing["id"],
                investigation_id=entity.investigation_id,
                canonical_name=existing["canonical_name"],
                entity_type=existing["entity_type"],
                summary=entity.summary or existing["summary"],
                aliases=merged_aliases,
                source_ids=merged_sources,
                created_at=existing["created_at"],
            )
            entity = updated

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO brain_entities (
                    id, investigation_id, canonical_name, entity_type, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.investigation_id,
                    entity.canonical_name,
                    entity.entity_type,
                    entity.model_dump_json(),
                    entity.created_at,
                ),
            )
            conn.commit()
        return entity

    def find_entity_by_name(self, investigation_id: str, canonical_name: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM brain_entities
                WHERE investigation_id = ? AND lower(canonical_name) = lower(?)
                LIMIT 1
                """,
                (investigation_id, canonical_name.strip()),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_entities(self, investigation_ids: list[str]) -> list[dict[str, Any]]:
        if not investigation_ids:
            return []
        placeholders = ",".join("?" for _ in investigation_ids)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM brain_entities WHERE investigation_id IN ({placeholders}) ORDER BY created_at ASC",
                tuple(investigation_ids),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def add_relation(self, rel: BrainRelation) -> BrainRelation:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO brain_relations (
                    id, investigation_id, source_entity_id, target_entity_id, predicate, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.id,
                    rel.investigation_id,
                    rel.source_entity_id,
                    rel.target_entity_id,
                    rel.predicate,
                    rel.model_dump_json(),
                    rel.valid_from,
                ),
            )
            conn.commit()
        return rel

    def list_relations(self, investigation_ids: list[str]) -> list[dict[str, Any]]:
        if not investigation_ids:
            return []
        placeholders = ",".join("?" for _ in investigation_ids)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM brain_relations WHERE investigation_id IN ({placeholders}) ORDER BY created_at ASC",
                tuple(investigation_ids),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def upsert_claim(self, claim: ClaimRecord) -> ClaimRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO claims (
                    id, investigation_id, verification_state, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    claim.id,
                    claim.investigation_id,
                    claim.verification_state.value,
                    claim.model_dump_json(),
                    claim.created_at,
                ),
            )
            conn.commit()
        return claim

    def list_claims(self, investigation_ids: list[str]) -> list[dict[str, Any]]:
        if not investigation_ids:
            return []
        placeholders = ",".join("?" for _ in investigation_ids)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT payload_json FROM claims WHERE investigation_id IN ({placeholders}) ORDER BY created_at ASC",
                tuple(investigation_ids),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def delete_source_and_propagate(
        self, investigation_id: str, source_id: str
    ) -> dict[str, Any]:
        """Delete a source and propagate removal across entities, relations, and claims.

        Satisfies the company-brain correctness gate: deleting a source removes its
        attributable search/graph items while retaining independent evidence from
        other sources.
        """
        removed_entities = 0
        removed_relations = 0
        downgraded_claims = 0

        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sources WHERE id = ? AND investigation_id = ?",
                (source_id, investigation_id),
            ).fetchone()
            if not row:
                return {"deleted": False, "reason": "source_not_found"}

            src_data = json.loads(row["payload_json"])
            src_data["deleted"] = True
            conn.execute(
                "UPDATE sources SET deleted = 1, payload_json = ? WHERE id = ?",
                (json.dumps(src_data), source_id),
            )

            # Propagate to entities
            ent_rows = conn.execute(
                "SELECT id, payload_json FROM brain_entities WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchall()
            for er in ent_rows:
                ent = json.loads(er["payload_json"])
                if source_id in ent.get("source_ids", []):
                    ent["source_ids"] = [s for s in ent["source_ids"] if s != source_id]
                    if not ent["source_ids"]:
                        conn.execute("DELETE FROM brain_entities WHERE id = ?", (er["id"],))
                        removed_entities += 1
                    else:
                        conn.execute(
                            "UPDATE brain_entities SET payload_json = ? WHERE id = ?",
                            (json.dumps(ent), er["id"]),
                        )

            # Propagate to relations
            rel_rows = conn.execute(
                "SELECT id, payload_json FROM brain_relations WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchall()
            for rr in rel_rows:
                rel = json.loads(rr["payload_json"])
                supp = [s for s in rel.get("supporting_source_ids", []) if s != source_id]
                contra = [s for s in rel.get("contradicting_source_ids", []) if s != source_id]
                if not supp and not contra:
                    conn.execute("DELETE FROM brain_relations WHERE id = ?", (rr["id"],))
                    removed_relations += 1
                else:
                    rel["supporting_source_ids"] = supp
                    rel["contradicting_source_ids"] = contra
                    conn.execute(
                        "UPDATE brain_relations SET payload_json = ? WHERE id = ?",
                        (json.dumps(rel), rr["id"]),
                    )

            # Propagate to claims
            clm_rows = conn.execute(
                "SELECT id, payload_json FROM claims WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchall()
            for cr in clm_rows:
                clm = json.loads(cr["payload_json"])
                if source_id in clm.get("supporting_source_ids", []):
                    clm["supporting_source_ids"] = [
                        s for s in clm["supporting_source_ids"] if s != source_id
                    ]
                    if not clm["supporting_source_ids"]:
                        clm["verification_state"] = VerificationState.UNRESOLVED.value
                        clm["reviewer_notes"] = (
                            (clm.get("reviewer_notes") or "")
                            + f" [Supporting source {source_id} was deleted; downgraded to unresolved.]"
                        ).strip()
                        downgraded_claims += 1
                    conn.execute(
                        "UPDATE claims SET verification_state = ?, payload_json = ? WHERE id = ?",
                        (clm["verification_state"], json.dumps(clm), cr["id"]),
                    )

            conn.commit()

        return {
            "deleted": True,
            "source_id": source_id,
            "removed_entities": removed_entities,
            "removed_relations": removed_relations,
            "downgraded_claims": downgraded_claims,
        }

    def query_company_brain(
        self,
        investigation_id: str,
        query: str = "",
        include_reused: bool = True,
    ) -> dict[str, Any]:
        """Retrieve scoped knowledge graph entities, relations, claims, and multi-hop connections.

        Strictly enforces investigation scope: only returns items from `investigation_id`
        plus explicitly selected `reused_investigation_ids`.
        """
        inv = self.get_investigation(investigation_id)
        if not inv:
            return {"entities": [], "relations": [], "claims": [], "sources": [], "paths": []}

        allowed_ids = [investigation_id]
        if include_reused:
            for rid in inv.get("reused_investigation_ids", []):
                if rid not in allowed_ids:
                    allowed_ids.append(rid)

        entities = self.list_entities(allowed_ids)
        relations = self.list_relations(allowed_ids)
        claims = self.list_claims(allowed_ids)

        sources: list[dict[str, Any]] = []
        for aid in allowed_ids:
            sources.extend(self.list_sources(aid, include_deleted=False))

        q_terms = [
            t.lower()
            for t in re.split(r"\W+", query.strip())
            if len(t) >= 2
        ]

        if q_terms:
            matched_entities = [
                e
                for e in entities
                if any(
                    term in e["canonical_name"].lower()
                    or term in e.get("summary", "").lower()
                    or term in e["entity_type"].lower()
                    for term in q_terms
                )
            ]
            matched_ent_ids = {e["id"] for e in matched_entities}
            # Include 1-hop and 2-hop graph neighborhood around matched entities
            hop_relations = [
                r
                for r in relations
                if r["source_entity_id"] in matched_ent_ids
                or r["target_entity_id"] in matched_ent_ids
                or any(term in r["predicate"].lower() for term in q_terms)
            ]
            neighbor_ids = set(matched_ent_ids)
            for r in hop_relations:
                neighbor_ids.add(r["source_entity_id"])
                neighbor_ids.add(r["target_entity_id"])

            filtered_entities = [e for e in entities if e["id"] in neighbor_ids]
            filtered_claims = [
                c
                for c in claims
                if any(
                    term in c["statement"].lower()
                    or term in (c.get("conditions") or "").lower()
                    for term in q_terms
                )
            ]
            filtered_sources = [
                s
                for s in sources
                if any(
                    term in s["title"].lower() or term in s.get("excerpt", "").lower()
                    for term in q_terms
                )
            ]
        else:
            filtered_entities = entities
            hop_relations = relations
            filtered_claims = claims
            filtered_sources = sources

        # Compute 2-hop connection paths for discovery synthesis
        paths: list[dict[str, Any]] = []
        by_src: dict[str, list[dict[str, Any]]] = {}
        for r in hop_relations:
            by_src.setdefault(r["source_entity_id"], []).append(r)

        for r1 in hop_relations:
            mid_id = r1["target_entity_id"]
            for r2 in by_src.get(mid_id, []):
                if r2["target_entity_id"] != r1["source_entity_id"]:
                    paths.append(
                        {
                            "path": (
                                f"{r1['source_entity_name']} --[{r1['predicate']}]--> "
                                f"{r1['target_entity_name']} --[{r2['predicate']}]--> "
                                f"{r2['target_entity_name']}"
                            ),
                            "CrossInvestigation": r1["investigation_id"] != r2["investigation_id"],
                            "supporting_sources": sorted(
                                set(r1.get("supporting_source_ids", []))
                                | set(r2.get("supporting_source_ids", []))
                            ),
                        }
                    )

        return {
            "allowed_scope_ids": allowed_ids,
            "entities": filtered_entities,
            "relations": hop_relations,
            "claims": filtered_claims,
            "sources": filtered_sources,
            "paths": paths[:25],
        }
