"""HTTP & SSE Server for ResearchWeave (zero external runtime dependency beyond Python 3 + Pydantic)."""

from __future__ import annotations

import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .blob_store import ResearchBlobStore
from .brain import ResearchWeaveStore
from .coordinator import ResearchCoordinator
from .entra_auth import TENANT_DIRECTORY_USERS, EntraAuthManager
from .models import (
    ClarifyConfirmRequest,
    CreateInvestigationRequest,
    SteeringMessageRequest,
    UpdateSettingsRequest,
    UploadFileRequest,
)
from .reports import export_docx_bytes, export_pdf_bytes


STATIC_DIR = Path(__file__).parent / "static"


class ResearchWeaveApp:
    """Application container holding the durable store, Blob adapter, and ResearchCoordinator."""

    def __init__(self, data_dir: Path | None = None) -> None:
        base_dir = data_dir or Path(os.getenv("RESEARCHWEAVE_DATA_DIR", "./.researchweave_data"))
        self.db_path = base_dir / "researchweave.db"
        self.blob_dir = base_dir / "blobs"
        self.store = ResearchWeaveStore(self.db_path)
        self.blob_store = ResearchBlobStore(self.blob_dir)
        self.coordinator = ResearchCoordinator(self.store, self.blob_store)
        self.entra_auth = EntraAuthManager()
        # Pre-seed approved users from the configured Microsoft Entra tenant directory
        for u in TENANT_DIRECTORY_USERS:
            if u.get("upn"):
                self.store.approve_user(
                    email=u["upn"],
                    role=u.get("role", "entra_member"),
                    approved_by=f"entra-tenant-{self.entra_auth.tenant_id}",
                )
            if u.get("mail"):
                self.store.approve_user(
                    email=u["mail"],
                    role=u.get("role", "entra_member"),
                    approved_by=f"entra-tenant-{self.entra_auth.tenant_id}",
                )


def create_http_handler(app: ResearchWeaveApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Keep test and server output clean unless debug logging is requested
            if os.getenv("RESEARCHWEAVE_VERBOSE_LOG") == "1":
                super().log_message(format, *args)

        def _send_json(self, payload: Any, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if extra_headers:
                for hk, hv in extra_headers.items():
                    self.send_header(hk, hv)
            self.end_headers()
            self.wfile.write(body)

        def _get_current_entra_user(self) -> dict[str, Any] | None:
            auth_hdr = self.headers.get("Authorization", "")
            if auth_hdr.lower().startswith("bearer "):
                tok = auth_hdr[7:].strip()
                verified = app.entra_auth.verify_session_token(tok)
                if verified:
                    return verified
            cookie_hdr = self.headers.get("Cookie", "")
            for part in cookie_hdr.split(";"):
                kv = part.strip().split("=", 1)
                if len(kv) == 2 and kv[0] == "rw_entra_session":
                    verified = app.entra_auth.verify_session_token(kv[1].strip())
                    if verified:
                        return verified
            return None

        def _send_bytes(
            self,
            content: bytes,
            content_type: str,
            filename: str | None = None,
            status: int = 200,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw) if raw.strip() else {}

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            try:
                if path in ("/", "/index.html"):
                    index_file = STATIC_DIR / "index.html"
                    if index_file.exists():
                        self._send_bytes(
                            index_file.read_bytes(), "text/html; charset=utf-8"
                        )
                    else:
                        self._send_json({"error": "UI index.html missing"}, 404)
                    return

                if path == "/api/health":
                    self._send_json(
                        {
                            "status": "healthy",
                            "service": "researchweave",
                            "version": "0.2.0",
                            "available_models": [
                                "gpt-6.1-sol",
                                "gpt-6-astra",
                            ],
                            "entra_tenant_id": app.entra_auth.tenant_id,
                            "entra_tenant_domain": app.entra_auth.tenant_domain,
                            "entra_client_id": app.entra_auth.client_id,
                            "foundry_configured": app.coordinator.foundry.is_configured,
                            "foundry_endpoint": app.coordinator.foundry.endpoint or None,
                            "blob_storage_connected": app.blob_store._blob_service_client is not None,
                            "blob_storage_url": app.blob_store.storage_account_url or None,
                            "open_source_stack": {
                                "discovery_engine": "openscientist",
                                "agent_runtime": app.coordinator.agentscope_runtime.runtime_info,
                                "knowledge_graph": "trustgraph-prov-o-ontology",
                                "document_ingestion": "azure-ai-content-understanding",
                            },
                        }
                    )
                    return

                if path == "/api/auth/config":
                    user = self._get_current_entra_user()
                    self._send_json(app.entra_auth.get_public_config(current_user=user))
                    return

                if path == "/api/auth/login":
                    host = self.headers.get("Host", "localhost:8080")
                    proto = self.headers.get("X-Forwarded-Proto", "http")
                    redirect_uri = (query.get("redirect_uri") or [f"{proto}://{host}/api/auth/callback"])[0]
                    auth_url = app.entra_auth.build_authorize_redirect(redirect_uri)
                    self.send_response(302)
                    self.send_header("Location", auth_url)
                    self.end_headers()
                    return

                if path == "/api/auth/callback":
                    err = (query.get("error") or [""])[0]
                    if err:
                        err_desc = (query.get("error_description") or [err])[0]
                        self._send_json({"error": err, "error_description": err_desc}, 400)
                        return
                    code = (query.get("code") or [""])[0]
                    state = (query.get("state") or [""])[0]
                    host = self.headers.get("Host", "localhost:8080")
                    proto = self.headers.get("X-Forwarded-Proto", "http")
                    fallback_redirect = f"{proto}://{host}/api/auth/callback"
                    user_info = app.entra_auth.exchange_authorization_code(code, state, fallback_redirect)
                    for addr in (user_info.get("upn"), user_info.get("mail")):
                        if addr:
                            app.store.approve_user(
                                email=addr,
                                role="entra_member",
                                approved_by=f"entra-oidc-{app.entra_auth.tenant_id}",
                            )
                    session_tok = app.entra_auth.issue_session_token(user_info)
                    self.send_response(302)
                    self.send_header(
                        "Set-Cookie",
                        f"rw_entra_session={session_tok}; Path=/; Max-Age=43200; SameSite=Lax",
                    )
                    self.send_header("Location", "/")
                    self.end_headers()
                    return

                if path == "/api/users":
                    self._send_json({"users": app.store.list_approved_users()})
                    return

                if path == "/api/investigations":
                    self._send_json({"investigations": app.store.list_investigations()})
                    return

                m_inv = re.match(r"^/api/investigations/([^/]+)$", path)
                if m_inv:
                    inv_id = m_inv.group(1)
                    bundle = app.coordinator.get_full_investigation_bundle(inv_id)
                    self._send_json(bundle)
                    return

                m_brain = re.match(r"^/api/investigations/([^/]+)/brain$", path)
                if m_brain:
                    inv_id = m_brain.group(1)
                    q = (query.get("q") or [""])[0]
                    result = app.store.query_company_brain(inv_id, query=q)
                    self._send_json(result)
                    return

                m_events = re.match(r"^/api/investigations/([^/]+)/events$", path)
                if m_events:
                    inv_id = m_events.group(1)
                    after_id = int((query.get("after_id") or ["0"])[0])
                    events = app.store.list_events(inv_id, after_id=after_id)
                    if (query.get("stream") or ["0"])[0] == "1":
                        # Server-Sent Events (SSE) replay with cursor
                        sse_lines: list[str] = []
                        for ev in events:
                            sse_lines.append(f"id: {ev['id']}")
                            sse_lines.append("event: research_event")
                            sse_lines.append(f"data: {json.dumps(ev, ensure_ascii=False)}")
                            sse_lines.append("")
                        payload_bytes = ("\n".join(sse_lines) + "\n").encode("utf-8")
                        self._send_bytes(payload_bytes, "text/event-stream; charset=utf-8")
                    else:
                        self._send_json({"events": events})
                    return

                m_export = re.match(r"^/api/investigations/([^/]+)/export$", path)
                if m_export:
                    inv_id = m_export.group(1)
                    fmt = ((query.get("format") or ["md"])[0]).lower()
                    bundle = app.coordinator.get_full_investigation_bundle(inv_id)
                    inv = bundle["investigation"]
                    md_text = inv.get("draft_report_markdown") or ""
                    is_he = inv.get("report_language", "en").lower().startswith("he")

                    if fmt in ("md", "markdown", "txt"):
                        self._send_bytes(
                            md_text.encode("utf-8"),
                            "text/markdown; charset=utf-8",
                            filename=f"{inv_id}-report.md",
                        )
                    elif fmt == "docx":
                        docx_bytes = export_docx_bytes(md_text, inv["title"], rtl=is_he)
                        self._send_bytes(
                            docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            filename=f"{inv_id}-report.docx",
                        )
                    elif fmt == "pdf":
                        pdf_bytes = export_pdf_bytes(md_text, inv["title"])
                        self._send_bytes(
                            pdf_bytes,
                            "application/pdf",
                            filename=f"{inv_id}-report.pdf",
                        )
                    else:
                        self._send_json({"error": f"Unsupported export format: {fmt}"}, 400)
                    return

                self._send_json({"error": "Not found"}, 404)
            except KeyError as exc:
                self._send_json({"error": str(exc)}, 404)
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = self._read_json_body()

                if path == "/api/auth/device/start":
                    flow = app.entra_auth.start_device_code_flow()
                    self._send_json(flow)
                    return

                if path == "/api/auth/device/poll":
                    flow_id = body.get("flow_id", "")
                    res = app.entra_auth.poll_device_code_flow(flow_id)
                    if res.get("status") == "authenticated" and res.get("user"):
                        user_info = res["user"]
                        for addr in (user_info.get("upn"), user_info.get("mail")):
                            if addr:
                                app.store.approve_user(
                                    email=addr,
                                    role="entra_member",
                                    approved_by=f"entra-device-{app.entra_auth.tenant_id}",
                                )
                        session_tok = app.entra_auth.issue_session_token(user_info)
                        res["session_token"] = session_tok
                        res["user"] = app.entra_auth.verify_session_token(session_tok)
                        self._send_json(
                            res,
                            200,
                            extra_headers={
                                "Set-Cookie": f"rw_entra_session={session_tok}; Path=/; Max-Age=43200; SameSite=Lax"
                            },
                        )
                        return
                    self._send_json(res)
                    return

                if path == "/api/auth/tenant-session":
                    upn = body.get("upn")
                    entra_jwt = body.get("entra_jwt")
                    user_info = app.entra_auth.authenticate_tenant_user_or_token(upn=upn, entra_jwt=entra_jwt)
                    for addr in (user_info.get("upn"), user_info.get("mail")):
                        if addr:
                            app.store.approve_user(
                                email=addr,
                                role=user_info.get("role", "entra_member"),
                                approved_by=f"entra-tenant-{app.entra_auth.tenant_id}",
                            )
                    session_tok = app.entra_auth.issue_session_token(user_info)
                    verified = app.entra_auth.verify_session_token(session_tok)
                    self._send_json(
                        {
                            "status": "authenticated",
                            "session_token": session_tok,
                            "user": verified,
                        },
                        200,
                        extra_headers={
                            "Set-Cookie": f"rw_entra_session={session_tok}; Path=/; Max-Age=43200; SameSite=Lax"
                        },
                    )
                    return

                if path == "/api/auth/logout":
                    self._send_json(
                        {"status": "logged_out"},
                        200,
                        extra_headers={
                            "Set-Cookie": "rw_entra_session=; Path=/; Max-Age=0; SameSite=Lax"
                        },
                    )
                    return

                if path == "/api/users/approve":
                    email = body.get("email", "")
                    role = body.get("role", "researcher")
                    approved_by = body.get("approved_by", "owner")
                    if not email:
                        self._send_json({"error": "email is required"}, 400)
                        return
                    user = app.store.approve_user(email=email, role=role, approved_by=approved_by)
                    self._send_json({"user": user}, 201)
                    return

                if path == "/api/investigations":
                    req = CreateInvestigationRequest(**body)
                    if not app.store.is_user_approved(req.owner):
                        self._send_json(
                            {"error": f"Microsoft account '{req.owner}' is not approved on this installation."},
                            HTTPStatus.FORBIDDEN,
                        )
                        return
                    bundle = app.coordinator.create_investigation(req)
                    self._send_json(bundle, 201)
                    return

                m_confirm = re.match(r"^/api/investigations/([^/]+)/confirm$", path)
                if m_confirm:
                    inv_id = m_confirm.group(1)
                    req = ClarifyConfirmRequest(**body)
                    bundle = app.coordinator.confirm_and_start(
                        inv_id,
                        clarification_answers=req.clarification_answers,
                        confirmed_objective=req.confirmed_objective,
                        autonomy_mode=req.autonomy_mode.value if req.autonomy_mode else None,
                        model_pool=req.model_pool,
                        stopping_conditions=req.stopping_conditions.model_dump()
                        if req.stopping_conditions
                        else None,
                        run_initial_cycle=body.get("run_initial_cycle", True),
                        background_async=bool(body.get("background_async", False)),
                    )
                    self._send_json(bundle)
                    return

                m_step = re.match(r"^/api/investigations/([^/]+)/step$", path)
                if m_step:
                    inv_id = m_step.group(1)
                    max_tasks = int(body.get("max_tasks", 1))
                    bundle = app.coordinator.execute_research_step(inv_id, max_tasks=max_tasks)
                    self._send_json(bundle)
                    return

                m_steer = re.match(r"^/api/investigations/([^/]+)/steer$", path)
                if m_steer:
                    inv_id = m_steer.group(1)
                    req = SteeringMessageRequest(**body)
                    bundle = app.coordinator.handle_live_steering(
                        inv_id,
                        sender=req.sender,
                        message=req.message,
                        update_objective=req.update_objective,
                        new_reference_links=req.new_reference_links,
                    )
                    self._send_json(bundle)
                    return

                m_upload = re.match(r"^/api/investigations/([^/]+)/upload$", path)
                if m_upload:
                    inv_id = m_upload.group(1)
                    req = UploadFileRequest(**body)
                    res = app.coordinator.ingest_uploaded_file(
                        inv_id,
                        filename=req.filename,
                        content_text=req.content_text,
                        content_type=req.content_type,
                        uploaded_by=req.uploaded_by,
                        content_base64=req.content_base64,
                    )
                    self._send_json(res, 201)
                    return

                m_settings = re.match(r"^/api/investigations/([^/]+)/settings$", path)
                if m_settings:
                    inv_id = m_settings.group(1)
                    req = UpdateSettingsRequest(**body)
                    bundle = app.coordinator.update_live_settings(
                        inv_id,
                        model_pool=req.model_pool,
                        autonomy_mode=req.autonomy_mode.value if req.autonomy_mode else None,
                        stopping_conditions=req.stopping_conditions.model_dump()
                        if req.stopping_conditions
                        else None,
                        approval_policy=req.approval_policy.model_dump()
                        if req.approval_policy
                        else None,
                        report_language=req.report_language,
                    )
                    self._send_json(bundle)
                    return

                m_pause = re.match(r"^/api/investigations/([^/]+)/pause$", path)
                if m_pause:
                    inv_id = m_pause.group(1)
                    reason = body.get("reason", "Paused manually by researcher.")
                    bundle = app.coordinator.pause_investigation(inv_id, reason=reason)
                    self._send_json(bundle)
                    return

                m_resume = re.match(r"^/api/investigations/([^/]+)/resume$", path)
                if m_resume:
                    inv_id = m_resume.group(1)
                    bundle = app.coordinator.resume_investigation(
                        inv_id,
                        extend_max_runtime_hours=body.get("extend_max_runtime_hours"),
                        extend_max_budget_usd=body.get("extend_max_budget_usd"),
                        approve_pending_tasks=body.get("approve_pending_tasks", True),
                    )
                    self._send_json(bundle)
                    return

                self._send_json({"error": "Not found"}, 404)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.CONFLICT)
            except KeyError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            try:
                m_src = re.match(r"^/api/investigations/([^/]+)/sources/([^/]+)$", path)
                if m_src:
                    inv_id, source_id = m_src.group(1), m_src.group(2)
                    res = app.store.delete_source_and_propagate(inv_id, source_id)
                    app.coordinator._refresh_report(inv_id)
                    self._send_json(res)
                    return

                m_inv = re.match(r"^/api/investigations/([^/]+)$", path)
                if m_inv:
                    inv_id = m_inv.group(1)
                    requester = ((query.get("requester") or ["researcher@researchweave.local"])[0]).lower()
                    inv = app.store.get_investigation(inv_id)
                    if not inv:
                        self._send_json({"error": "Not found"}, 404)
                        return
                    if requester not in (inv["owner"].lower(), "owner", "admin@researchweave.local"):
                        self._send_json(
                            {"error": "Only the investigation owner or installation administrator can delete this investigation."},
                            403,
                        )
                        return
                    deleted = app.store.delete_investigation(inv_id)
                    self._send_json({"deleted": deleted, "investigation_id": inv_id})
                    return

                self._send_json({"error": "Not found"}, 404)
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)

    return Handler


def run_server(host: str = "0.0.0.0", port: int = 8080, data_dir: Path | None = None) -> None:
    app = ResearchWeaveApp(data_dir=data_dir)
    handler_cls = create_http_handler(app)
    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"ResearchWeave server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port_env = int(os.getenv("PORT", "8080"))
    run_server(port=port_env)
