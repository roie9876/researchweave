"""Per-investigation Azure Blob Storage adapter with local filesystem fallback."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any


def sanitize_container_name(investigation_id: str) -> str:
    """Create a valid Azure Blob container name (3-63 chars, lowercase alphanumeric + hyphens)."""
    cleaned = re.sub(r"[^a-z0-9-]", "-", f"rw-{investigation_id.lower()}")
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if len(cleaned) < 3:
        cleaned = f"rw-run-{cleaned}"
    return cleaned[:63]


class ResearchBlobStore:
    """Manages per-investigation file uploads and generated artifacts.

    Uses Azure Blob Storage via DefaultAzureCredential when AZURE_STORAGE_ACCOUNT_URL
    is configured, and seamlessly falls back to a local mirror directory for
    offline/local development and unit tests.
    """

    def __init__(
        self,
        local_root: Path,
        storage_account_url: str | None = None,
    ) -> None:
        self.local_root = local_root
        self.local_root.mkdir(parents=True, exist_ok=True)
        self.storage_account_url = storage_account_url or os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        self._blob_service_client: Any = None
        if self.storage_account_url:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.storage.blob import BlobServiceClient

                credential = DefaultAzureCredential()
                self._blob_service_client = BlobServiceClient(
                    account_url=self.storage_account_url,
                    credential=credential,
                )
            except Exception:
                self._blob_service_client = None

    def ensure_run_container(self, investigation_id: str) -> dict[str, Any]:
        """Create an isolated container for the research run."""
        container_name = sanitize_container_name(investigation_id)
        local_dir = self.local_root / container_name
        local_dir.mkdir(parents=True, exist_ok=True)

        backend = "local_mirror"
        if self._blob_service_client is not None:
            try:
                container_client = self._blob_service_client.get_container_client(container_name)
                if not container_client.exists():
                    container_client.create_container(
                        metadata={"investigation_id": investigation_id, "managed_by": "researchweave"}
                    )
                backend = "azure_blob"
            except Exception:
                backend = "local_mirror"

        return {
            "container_name": container_name,
            "backend": backend,
            "local_path": str(local_dir),
        }

    def store_artifact(
        self,
        investigation_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str = "text/plain",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Store an uploaded file or generated artifact and return provenance metadata."""
        container_info = self.ensure_run_container(investigation_id)
        container_name = container_info["container_name"]
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(filename).name) or "artifact.txt"
        digest = hashlib.sha256(content_bytes).hexdigest()

        local_file = self.local_root / container_name / safe_filename
        local_file.write_bytes(content_bytes)

        backend = container_info["backend"]
        blob_uri = f"blob://{container_name}/{safe_filename}"
        if self._blob_service_client is not None:
            try:
                blob_client = self._blob_service_client.get_blob_client(
                    container=container_name, blob=safe_filename
                )
                blob_client.upload_blob(
                    content_bytes,
                    overwrite=True,
                    metadata={
                        "sha256": digest,
                        "content_type": content_type,
                        **(metadata or {}),
                    },
                )
                blob_uri = blob_client.url
                backend = "azure_blob"
            except Exception:
                backend = "local_mirror"

        return {
            "container_name": container_name,
            "blob_name": safe_filename,
            "uri": blob_uri,
            "local_path": str(local_file),
            "sha256": digest,
            "size_bytes": len(content_bytes),
            "backend": backend,
        }

    def read_artifact_text(self, investigation_id: str, blob_name: str) -> str:
        """Read text content of an artifact from the run container."""
        container_name = sanitize_container_name(investigation_id)
        local_file = self.local_root / container_name / Path(blob_name).name
        if local_file.exists():
            return local_file.read_text(encoding="utf-8", errors="replace")
        if self._blob_service_client is not None:
            try:
                blob_client = self._blob_service_client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                return blob_client.download_blob().readall().decode("utf-8", errors="replace")
            except Exception:
                return ""
        return ""
