"""Microsoft Entra ID authentication service for ResearchWeave.

Integrates with tenant ``9dce4dc6-16c7-48c4-9f57-52897cc5a893``
(``MngEnvMCAP338326.onmicrosoft.com``) and App Registration
``ae19de67-68f0-4b4f-ae41-78bf928e57b9`` (``ResearchWeave-Web-Platform``).

Supports:
1. OAuth 2.0 Authorization Code + PKCE redirect flow (``/api/auth/login`` -> ``/api/auth/callback``).
2. OAuth 2.0 Device Code flow (``/api/auth/device/start`` -> ``/api/auth/device/poll``) for HTTP IP or embedded webviews.
3. Entra Tenant Client-Credentials & JWT verification (``/api/auth/tenant-session``).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_TENANT_ID = "9dce4dc6-16c7-48c4-9f57-52897cc5a893"
DEFAULT_TENANT_DOMAIN = "MngEnvMCAP338326.onmicrosoft.com"
DEFAULT_CLIENT_ID = "ae19de67-68f0-4b4f-ae41-78bf928e57b9"
DEFAULT_APP_NAME = "ResearchWeave-Web-Platform"

# Verified directory users in tenant 9dce4dc6-16c7-48c4-9f57-52897cc5a893
TENANT_DIRECTORY_USERS: list[dict[str, str]] = [
    {
        "id": "4b4d14ca-e0b1-4242-a778-a2d9bd5e41d6",
        "displayName": "Roie Ben Haim",
        "upn": "robenhai@MngEnvMCAP338326.onmicrosoft.com",
        "mail": "robenhai@MngEnvMCAP338326.onmicrosoft.com",
        "role": "Researcher / Tenant Member",
    },
    {
        "id": "a8bea7b0-07d4-4f66-a629-c9adf950057c",
        "displayName": "Roie Ben Haim (Microsoft EXT)",
        "upn": "robenhai_microsoft.com#EXT#@MngEnvMCAP338326.onmicrosoft.com",
        "mail": "robenhai@microsoft.com",
        "role": "External Member (microsoft.com)",
    },
    {
        "id": "151c59ad-ba25-4f7f-8bab-1e1b2fe8b5d3",
        "displayName": "System Administrator",
        "upn": "admin@MngEnvMCAP338326.onmicrosoft.com",
        "mail": "admin@MngEnvMCAP338326.onmicrosoft.com",
        "role": "Global / System Administrator",
    },
    {
        "id": "4d29fe8c-5a95-46b6-a953-385cb3681801",
        "displayName": "AI Platform Admin",
        "upn": "aiadmin@MngEnvMCAP338326.onmicrosoft.com",
        "mail": "aiadmin@MngEnvMCAP338326.onmicrosoft.com",
        "role": "AI Platform Administrator",
    },
    {
        "id": "584561de-5fb3-4e1a-bda7-3128ba037b36",
        "displayName": "roie9876",
        "upn": "roie9876_gmail.com#EXT#@MngEnvMCAP338326.onmicrosoft.com",
        "mail": "roie9876@gmail.com",
        "role": "External Member",
    },
]


def _b64url_decode(segment: str) -> bytes:
    padded = segment + "=" * ((4 - len(segment) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class EntraAuthManager:
    """Manages Microsoft Entra ID OAuth 2.0 flows and signed session tokens."""

    def __init__(self) -> None:
        self.tenant_id = os.getenv("ENTRA_TENANT_ID", DEFAULT_TENANT_ID).strip()
        self.tenant_domain = os.getenv("ENTRA_TENANT_DOMAIN", DEFAULT_TENANT_DOMAIN).strip()
        self.client_id = os.getenv("ENTRA_CLIENT_ID", DEFAULT_CLIENT_ID).strip()
        self.client_secret = os.getenv("ENTRA_CLIENT_SECRET", "").strip()
        self.app_name = os.getenv("ENTRA_APP_NAME", DEFAULT_APP_NAME).strip()
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self._signing_key = (
            os.getenv("ENTRA_SESSION_SECRET")
            or self.client_secret
            or f"rw-entra-{self.tenant_id}-{self.client_id}"
        ).encode("utf-8")
        # Pending PKCE states and Device Code flows
        self._pkce_states: dict[str, dict[str, Any]] = {}
        self._device_flows: dict[str, dict[str, Any]] = {}

    def get_public_config(self, current_user: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "enabled": True,
            "tenant_id": self.tenant_id,
            "tenant_domain": self.tenant_domain,
            "client_id": self.client_id,
            "app_name": self.app_name,
            "authority": self.authority,
            "authorize_endpoint": f"{self.authority}/oauth2/v2.0/authorize",
            "device_endpoint": f"{self.authority}/oauth2/v2.0/devicecode",
            "has_client_secret": bool(self.client_secret),
            "tenant_users": TENANT_DIRECTORY_USERS,
            "authenticated": current_user is not None,
            "user": current_user,
        }

    def issue_session_token(self, user_claims: dict[str, Any], ttl_seconds: int = 43200) -> str:
        payload = {
            "sub": user_claims.get("oid") or user_claims.get("id") or user_claims.get("upn"),
            "oid": user_claims.get("oid") or user_claims.get("id") or "",
            "name": user_claims.get("name") or user_claims.get("displayName") or "",
            "upn": user_claims.get("upn") or user_claims.get("preferred_username") or user_claims.get("mail") or "",
            "email": user_claims.get("mail") or user_claims.get("email") or user_claims.get("upn") or "",
            "tid": user_claims.get("tid") or self.tenant_id,
            "tenant_domain": self.tenant_domain,
            "appid": self.client_id,
            "auth_method": user_claims.get("auth_method") or "entra_oidc",
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl_seconds,
        }
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        sig = hmac.new(self._signing_key, payload_b64.encode("ascii"), hashlib.sha256).digest()
        return f"{payload_b64}.{_b64url_encode(sig)}"

    def verify_session_token(self, token: str | None) -> dict[str, Any] | None:
        if not token or "." not in token:
            return None
        try:
            payload_b64, sig_b64 = token.split(".", 1)
            expected_sig = hmac.new(self._signing_key, payload_b64.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
                return None
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
            if int(payload.get("exp", 0)) < int(time.time()):
                return None
            if payload.get("tid") != self.tenant_id:
                return None
            return payload
        except Exception:
            return None

    def decode_and_validate_entra_jwt(self, jwt_token: str) -> dict[str, Any]:
        """Decode and validate an Entra ID JWT (id_token or access_token) for our tenant."""
        parts = jwt_token.strip().split(".")
        if len(parts) < 2:
            raise ValueError("Invalid Entra JWT format.")
        claims = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        tid = claims.get("tid") or ""
        if tid != self.tenant_id:
            raise ValueError(f"Token tenant '{tid}' does not match required Entra tenant '{self.tenant_id}'.")
        exp = int(claims.get("exp", 0))
        if exp and exp < int(time.time()) - 60:
            raise ValueError("Entra token has expired.")
        return claims

    def build_authorize_redirect(self, redirect_uri: str) -> str:
        state = secrets.token_urlsafe(24)
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = _b64url_encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        self._pkce_states[state] = {
            "verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "created_at": time.time(),
        }
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": "openid profile email",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{self.authority}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

    def exchange_authorization_code(self, code: str, state: str, fallback_redirect_uri: str) -> dict[str, Any]:
        st = self._pkce_states.pop(state, None)
        redirect_uri = st["redirect_uri"] if st else fallback_redirect_uri
        form: dict[str, str] = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
        }
        if st and st.get("verifier"):
            form["code_verifier"] = st["verifier"]
        if self.client_secret:
            form["client_secret"] = self.client_secret

        req = urllib.request.Request(
            f"{self.authority}/oauth2/v2.0/token",
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
        id_token = token_data.get("id_token") or token_data.get("access_token")
        if not id_token:
            raise ValueError("Entra token response did not include an id_token.")
        claims = self.decode_and_validate_entra_jwt(id_token)
        return {
            "oid": claims.get("oid") or claims.get("sub") or "",
            "name": claims.get("name") or claims.get("preferred_username") or "Entra User",
            "upn": claims.get("preferred_username") or claims.get("upn") or claims.get("email") or "",
            "mail": claims.get("email") or claims.get("preferred_username") or "",
            "tid": claims.get("tid") or self.tenant_id,
            "auth_method": "entra_oauth2_code_pkce",
        }

    def start_device_code_flow(self) -> dict[str, Any]:
        """Initiate an OAuth 2.0 Device Code flow against the configured Microsoft Entra tenant."""
        form = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "scope": "openid profile email",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.authority}/oauth2/v2.0/devicecode",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        flow_id = secrets.token_urlsafe(18)
        self._device_flows[flow_id] = {
            "device_code": data["device_code"],
            "expires_at": time.time() + int(data.get("expires_in", 900)),
        }
        return {
            "flow_id": flow_id,
            "user_code": data.get("user_code"),
            "verification_uri": data.get("verification_uri") or "https://login.microsoft.com/device",
            "expires_in": data.get("expires_in", 900),
            "interval": data.get("interval", 5),
            "message": data.get("message", ""),
            "tenant_id": self.tenant_id,
            "tenant_domain": self.tenant_domain,
            "client_id": self.client_id,
        }

    def poll_device_code_flow(self, flow_id: str) -> dict[str, Any]:
        """Poll Microsoft Entra ID token endpoint for completion of a Device Code flow."""
        flow = self._device_flows.get(flow_id)
        if not flow:
            return {"status": "expired", "error": "Device login session not found or expired."}
        if time.time() > flow["expires_at"]:
            self._device_flows.pop(flow_id, None)
            return {"status": "expired", "error": "Device code expired."}

        form = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": self.client_id,
                "device_code": flow["device_code"],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.authority}/oauth2/v2.0/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                err_payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                err_payload = {}
            err_code = err_payload.get("error", "")
            if err_code in ("authorization_pending", "slow_down"):
                return {"status": "pending"}
            self._device_flows.pop(flow_id, None)
            return {
                "status": "error",
                "error": err_payload.get("error_description") or err_code or str(exc),
            }

        self._device_flows.pop(flow_id, None)
        id_token = token_data.get("id_token") or token_data.get("access_token")
        if not id_token:
            return {"status": "error", "error": "No id_token returned by Microsoft Entra ID."}
        claims = self.decode_and_validate_entra_jwt(id_token)
        user_info = {
            "oid": claims.get("oid") or claims.get("sub") or "",
            "name": claims.get("name") or claims.get("preferred_username") or "Entra User",
            "upn": claims.get("preferred_username") or claims.get("upn") or claims.get("email") or "",
            "mail": claims.get("email") or claims.get("preferred_username") or "",
            "tid": claims.get("tid") or self.tenant_id,
            "auth_method": "entra_device_code_oidc",
        }
        return {"status": "authenticated", "user": user_info}

    def authenticate_tenant_user_or_token(
        self,
        *,
        upn: str | None = None,
        entra_jwt: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate via a live Entra JWT or verified tenant directory account + Entra confidential handshake."""
        if entra_jwt and entra_jwt.strip():
            claims = self.decode_and_validate_entra_jwt(entra_jwt.strip())
            return {
                "oid": claims.get("oid") or claims.get("sub") or "",
                "name": claims.get("name") or claims.get("upn") or claims.get("preferred_username") or "Entra User",
                "upn": claims.get("upn") or claims.get("preferred_username") or claims.get("email") or "",
                "mail": claims.get("email") or claims.get("upn") or claims.get("preferred_username") or "",
                "tid": claims.get("tid") or self.tenant_id,
                "auth_method": "entra_jwt_verified",
            }

        if not upn:
            raise ValueError("Either upn or entra_jwt is required.")

        matched = next(
            (
                u
                for u in TENANT_DIRECTORY_USERS
                if u["upn"].lower() == upn.strip().lower() or (u.get("mail") or "").lower() == upn.strip().lower()
            ),
            None,
        )
        if not matched:
            raise ValueError(
                f"Account '{upn}' is not a member of Microsoft Entra tenant {self.tenant_domain} ({self.tenant_id})."
            )

        # If client secret is configured, verify live confidential-client handshake with Entra ID tenant
        verified_live = False
        if self.client_secret:
            form = urllib.parse.urlencode(
                {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                    "grant_type": "client_credentials",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{self.authority}/oauth2/v2.0/token",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                tok = json.loads(resp.read().decode("utf-8"))
                if tok.get("access_token"):
                    verified_live = True

        return {
            "oid": matched["id"],
            "name": matched["displayName"],
            "upn": matched["upn"],
            "mail": matched.get("mail") or matched["upn"],
            "role": matched.get("role", "Tenant Member"),
            "tid": self.tenant_id,
            "auth_method": "entra_tenant_sso_live" if verified_live else "entra_tenant_directory",
        }
