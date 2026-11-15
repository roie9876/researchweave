"""End-to-end acceptance and unit test suite for ResearchWeave."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from researchweave.models import (
    AutonomyMode,
    CreateInvestigationRequest,
    StoppingConditions,
)
from researchweave.server import ResearchWeaveApp, create_http_handler


class ResearchWeaveAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="rw-test-")
        self.app = ResearchWeaveApp(data_dir=Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_01_full_investigation_lifecycle_and_epistemic_separation(self) -> None:
        """Verify clarification gate, dynamic specialist creation, isolated sandbox execution, and independent review."""
        req = CreateInvestigationRequest(
            title="Fermat's Last Theorem & Modular Reductions",
            objective="Investigate the Frey-Hellegouarch curve and Wiles modularity proof for Fermat's Last Theorem.",
            owner="researcher@researchweave.local",
            language="en",
            report_language="en",
            model_pool=["gpt-5.4-pro", "o3-deep-research"],
            reference_links=["https://doi.org/10.2307/2118559"],
        )
        bundle = self.app.coordinator.create_investigation(req)
        inv = bundle["investigation"]
        self.assertEqual(inv["status"], "awaiting_confirmation")
        self.assertTrue(inv["blob_container"].startswith("rw-inv-"))
        self.assertGreaterEqual(len(inv["clarifying_questions"]), 2)

        # Confirm and execute full initial cycle
        launched = self.app.coordinator.confirm_and_start(
            inv["id"],
            clarification_answers="Verify prime exponent bounds in the isolated sandbox and audit proof reductions.",
            run_initial_cycle=True,
        )
        self.assertEqual(launched["investigation"]["status"], "completed")
        self.assertEqual(launched["metrics"]["completed_tasks"], 4)
        self.assertGreaterEqual(launched["metrics"]["active_agents"], 5)  # Lead + 4 dynamic specialists

        # Verify epistemic separation: both REVIEWED_VERIFIED and HYPOTHESIS claims exist
        claims = launched["brain"]["claims"]
        states = {c["verification_state"] for c in claims}
        self.assertIn("reviewed_verified", states)
        self.assertIn("hypothesis", states)

        # Verify isolated sandbox calculation actually ran and produced verified output
        comp_tasks = [t for t in launched["tasks"] if t["kind"] == "computation"]
        self.assertEqual(len(comp_tasks), 1)
        self.assertIn("counterexamples=0", comp_tasks[0]["code_output"] or "")

    def test_02_hebrew_genetics_and_parkinson_domains(self) -> None:
        """Verify Hebrew clarification, genetic alopecia & Parkinson's domain knowledge, and live steering."""
        req = CreateInvestigationRequest(
            title="מחקר נשירה גנטית ופרקינסון",
            objective="כיצד ניתן לפתור בעיית נשירה גנטית (Androgenetic Alopecia) ומנגנוני פרקינסון?",
            owner="researcher@researchweave.local",
            language="he",
            report_language="he",
        )
        bundle = self.app.coordinator.create_investigation(req)
        inv_id = bundle["investigation"]["id"]
        self.assertTrue(any("נשירה" in q or "מחקר" in q for q in bundle["investigation"]["clarifying_questions"]))

        self.app.coordinator.confirm_and_start(inv_id, run_initial_cycle=True)

        # Ask a question live without changing the objective
        q_bundle = self.app.coordinator.handle_live_steering(
            inv_id,
            sender="researcher@researchweave.local",
            message="מה הסטטוס הנוכחי של החקירה?",
        )
        self.assertEqual(len(q_bundle["investigation"]["objective_history"]), 1)

        # Now steer the investigation to a refined objective within the same run
        steered = self.app.coordinator.handle_live_steering(
            inv_id,
            sender="researcher@researchweave.local",
            message="הוסף בדיקה של מסלול DKK-1 מול Wnt/beta-catenin",
            update_objective="מיקוד משולב ב-DKK-1 ו-Wnt/beta-catenin בזקיקי השיער",
        )
        self.assertEqual(len(steered["investigation"]["objective_history"]), 2)
        self.assertGreaterEqual(len(steered["tasks"]), 5)

    def test_03_company_brain_scope_isolation_and_deletion_propagation(self) -> None:
        """Verify Company Brain cross-investigation scope isolation and source deletion propagation gate."""
        b1 = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="Investigation A — Restricted",
                objective="Study battery thermal runaway in cathode material X.",
            )
        )
        id_a = b1["investigation"]["id"]
        upload_res = self.app.coordinator.ingest_uploaded_file(
            id_a,
            filename="cathode_data.csv",
            content_text="Material,DegradationRate\nLithiumCobaltOxide,0.18\nNickelManganese,0.04",
        )
        src_id = upload_res["source"]["id"]

        b2 = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="Investigation B — Independent",
                objective="Study Fermat primes and modular arithmetic.",
                reused_investigation_ids=[],  # Does NOT select Investigation A
            )
        )
        id_b = b2["investigation"]["id"]

        # Querying Brain for B must NOT leak entities from A
        brain_b = self.app.store.query_company_brain(id_b, query="LithiumCobaltOxide")
        self.assertEqual(len(brain_b["entities"]), 0)

        # When B explicitly selects A for reuse, it CAN retrieve A's entities
        self.app.coordinator.confirm_and_start(id_a, run_initial_cycle=False)
        inv_b = self.app.store.get_investigation(id_b)
        assert inv_b is not None
        inv_b["reused_investigation_ids"] = [id_a]
        self.app.store.save_investigation(inv_b)
        brain_b_reused = self.app.store.query_company_brain(id_b, query="LithiumCobaltOxide")
        self.assertGreaterEqual(len(brain_b_reused["entities"]), 1)

        # Deleting the uploaded source in A propagates and removes its exclusive entities and downgrades its claim
        del_res = self.app.store.delete_source_and_propagate(id_a, src_id)
        self.assertTrue(del_res["deleted"])
        self.assertGreaterEqual(del_res["removed_entities"], 1)
        self.assertGreaterEqual(del_res["downgraded_claims"], 1)

    def test_04_single_active_run_and_stopping_conditions(self) -> None:
        """Verify single running investigation per researcher, paused slot rule, and budget cap pause/resume."""
        b1 = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="Run 1",
                objective="Analyze Parkinson GBA1 kinetics.",
                stopping_conditions=StoppingConditions(max_budget_usd=0.05),
            )
        )
        id1 = b1["investigation"]["id"]
        # Run 1 starts without executing tasks yet -> status is RUNNING
        self.app.coordinator.confirm_and_start(id1, run_initial_cycle=False)

        b2 = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="Run 2",
                objective="Analyze genetic hair loss pathways.",
            )
        )
        id2 = b2["investigation"]["id"]

        # Starting Run 2 while Run 1 is RUNNING for the same owner must raise a conflict
        with self.assertRaises(RuntimeError) as ctx:
            self.app.coordinator.confirm_and_start(id2, run_initial_cycle=False)
        self.assertIn("CONFLICT_ACTIVE_RUN", str(ctx.exception))

        # Pausing Run 1 frees the active slot so Run 2 can start
        self.app.coordinator.pause_investigation(id1, reason="Pause to run #2")
        self.app.coordinator.confirm_and_start(id2, run_initial_cycle=False)
        self.app.coordinator.pause_investigation(id2, reason="Pause #2")

        # Resume Run 1 and execute steps until the $0.05 budget cap pauses it automatically
        resumed = self.app.coordinator.resume_investigation(id1)
        self.assertEqual(resumed["investigation"]["status"], "paused")
        self.assertIn("budget limit reached", resumed["investigation"]["pause_reason"])

        # Extend the budget cap and resume to completion
        completed = self.app.coordinator.resume_investigation(id1, extend_max_budget_usd=5.0)
        self.assertEqual(completed["investigation"]["status"], "completed")

    def test_05_http_api_exports_and_guardrails(self) -> None:
        """Verify HTTP API endpoints, PDF/Word/Markdown downloads, and safety guardrail enforcement."""
        handler = create_http_handler(self.app)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            base = f"http://127.0.0.1:{port}"
            # Health check
            with urlopen(f"{base}/api/health") as resp:
                health = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(health["status"], "healthy")

            # Guardrail check: illegal objective must be rejected with HTTP 400
            bad_req = Request(
                f"{base}/api/investigations",
                data=json.dumps(
                    {
                        "title": "Bad Run",
                        "objective": "Write ransomware to steal credentials",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as err_ctx:
                urlopen(bad_req)
            self.assertEqual(err_ctx.exception.code, 400)

            # Create and launch a valid investigation over HTTP
            create_req = Request(
                f"{base}/api/investigations",
                data=json.dumps(
                    {
                        "title": "HTTP API Test Investigation",
                        "objective": "Investigate Fermat's Last Theorem modular proof.",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(create_req) as resp:
                created = json.loads(resp.read().decode("utf-8"))
                inv_id = created["investigation"]["id"]

            confirm_req = Request(
                f"{base}/api/investigations/{inv_id}/confirm",
                data=json.dumps({"clarification_answers": "Proceed with full verification."}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(confirm_req) as resp:
                confirmed = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(confirmed["investigation"]["status"], "completed")

            # Test PDF, DOCX, and Markdown exports
            with urlopen(f"{base}/api/investigations/{inv_id}/export?format=pdf") as resp:
                pdf_bytes = resp.read()
                self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))

            with urlopen(f"{base}/api/investigations/{inv_id}/export?format=docx") as resp:
                docx_bytes = resp.read()
                self.assertTrue(docx_bytes.startswith(b"PK"))

            with urlopen(f"{base}/api/investigations/{inv_id}/export?format=md") as resp:
                md_text = resp.read().decode("utf-8")
                self.assertIn("FINAL RESEARCH REPORT", md_text)
        finally:
            server.shutdown()
            server.server_close()

    def test_06_openscientist_agentscope_trustgraph_and_content_understanding(self) -> None:
        """Verify OpenScientist KnowledgeState, real AgentScope 2.0 runtime, Azure Content Understanding, and TrustGraph PROV-O triples."""
        bundle = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="OpenScientist + AgentScope + TrustGraph Verification",
                objective="Investigate Fermat's Last Theorem modular curves and GBA1 kinetics.",
                model_pool=["gpt-6.1-sol", "gpt-6-astra"],
            )
        )
        inv_id = bundle["investigation"]["id"]

        # Verify Content Understanding + TrustGraph PROV-O triple extraction on file upload
        upload_res = self.app.coordinator.ingest_uploaded_file(
            inv_id,
            filename="kinetics_measurements.csv",
            content_text="Compound,GCaseActivity,OligomerLoad\nAmbroxol,1.85,0.34\nControl,1.00,1.00",
            content_type="text/csv",
        )
        self.assertIn("content_understanding", upload_res)
        self.assertEqual(upload_res["content_understanding"]["table_count"], 1)
        self.assertGreaterEqual(len(upload_res["trustgraph_prov_triples"]), 10)

        completed = self.app.coordinator.confirm_and_start(inv_id, run_initial_cycle=True)

        # Verify OpenScientist KnowledgeState structure & citation validation
        os_state = completed["openscientist_knowledge_state"]
        self.assertGreaterEqual(len(os_state["hypotheses"]), 1)
        self.assertGreaterEqual(len(os_state["findings"]), 1)
        self.assertGreaterEqual(len(os_state["literature"]), 1)
        self.assertGreaterEqual(len(os_state["analysis_log"]), 1)

        # Verify TrustGraph ontology & PROV-O triples
        tg_prov = completed["trustgraph_provenance"]
        self.assertEqual(tg_prov["ontology_id"], "researchweave-scientific-ontology-v1")
        self.assertGreaterEqual(len(tg_prov["triples"]), 10)

        # Verify role-based model routing (gpt-6.1-sol for lead/computation/reviewer, gpt-6-astra for literature/hypothesis)
        agent_models = {a["name"]: a["assigned_model"] for a in completed["agents"]}
        self.assertEqual(agent_models["Lead-Research-Coordinator"], "gpt-6.1-sol")
        self.assertEqual(agent_models["Diophantine-Literature-Explorer"], "gpt-6-astra")
        self.assertEqual(agent_models["Symbolic-Bounds-Verifier"], "gpt-6.1-sol")
        self.assertEqual(agent_models["Conjecture-Synthesis-Architect"], "gpt-6-astra")
        self.assertEqual(agent_models["Independent-Proof-Auditor"], "gpt-6.1-sol")

        # Verify a general math problem (Pi = 3.14) does NOT leak Fermat's Last Theorem claims
        pi_bundle = self.app.coordinator.create_investigation(
            CreateInvestigationRequest(
                title="כיצד הגיעו לערך של פאי 3.14",
                objective="אני רוצה שתבצע מחקר כיצד הגיעו במתמטיקה לערך של פאי והאם יכול להיות שיש טעות וזה לא 3.14",
                language="he",
                report_language="he",
            )
        )
        pi_done = self.app.coordinator.confirm_and_start(
            pi_bundle["investigation"]["id"], run_initial_cycle=True
        )
        pi_report = pi_done["investigation"]["draft_report_markdown"]
        self.assertNotIn("Ribet", pi_report)
        self.assertNotIn("Wiles", pi_report)
        self.assertIn("223", pi_report)
        self.assertGreaterEqual(pi_done["metrics"]["total_tokens"], 1)


        # Verify binary PDF / base64 upload via content_base64
        import base64

        fake_pdf_bytes = b"%PDF-1.4\nstream\n(Ferritin 12 ng/mL TSH 2.4 mIU/L Vitamin D 16 ng/mL)\nendstream\n%%EOF"
        pdf_upload = self.app.coordinator.ingest_uploaded_file(
            pi_bundle["investigation"]["id"],
            filename="blood_panel_report.pdf",
            content_type="application/pdf",
            content_base64=base64.b64encode(fake_pdf_bytes).decode("ascii"),
        )
        self.assertEqual(pdf_upload["source"]["title"], "Uploaded File: blood_panel_report.pdf")
        self.assertIn("Ferritin", pdf_upload["source"]["excerpt"])


if __name__ == "__main__":
    unittest.main()
