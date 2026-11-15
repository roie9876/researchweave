"""Microsoft Azure AI Content Understanding & Document Intelligence Ingestion Adapter.

Provides structured scientific document, table, section, and page/character-offset
locator extraction backed by the Microsoft Foundry (`AIServices`) endpoint using
keyless `DefaultAzureCredential` RBAC authentication.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedChunkLocator:
    page_number: int
    section_title: str
    chunk_index: int
    char_offset: int
    char_length: int
    text: str
    element_type: str = "paragraph"  # paragraph, table, formula, csv_table


@dataclass
class ContentUnderstandingResult:
    filename: str
    mime_type: str
    analyzer_used: str  # "azure_content_understanding" or "structured_scientific_decoder"
    page_count: int
    table_count: int
    markdown_content: str
    chunks: list[ExtractedChunkLocator] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "mime_type": self.mime_type,
            "analyzer_used": self.analyzer_used,
            "page_count": self.page_count,
            "table_count": self.table_count,
            "markdown_content": self.markdown_content,
            "tables": self.tables,
            "metadata": self.metadata,
            "chunks": [
                {
                    "page_number": c.page_number,
                    "section_title": c.section_title,
                    "chunk_index": c.chunk_index,
                    "char_offset": c.char_offset,
                    "char_length": c.char_length,
                    "text": c.text,
                    "element_type": c.element_type,
                }
                for c in self.chunks
            ],
        }


class AzureContentUnderstandingService:
    """Calls Azure AI Content Understanding / Document Intelligence & Vision on the Foundry AIServices resource."""

    def __init__(self, endpoint: str | None = None, foundry_adapter: Any = None) -> None:
        raw_ep = (endpoint or os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        self.endpoint = re.sub(r"/openai/v1/?$", "", raw_ep).rstrip("/") if raw_ep else ""
        self.foundry_adapter = foundry_adapter

    def _get_bearer_token(self) -> str | None:
        if not self.endpoint or os.getenv("RESEARCHWEAVE_DISABLE_LIVE_LLM") == "1":
            return None
        try:
            from azure.identity import DefaultAzureCredential

            client_id = os.getenv("AZURE_CLIENT_ID") or None
            cred = DefaultAzureCredential(managed_identity_client_id=client_id)
            token = cred.get_token("https://cognitiveservices.azure.com/.default")
            return token.token
        except Exception:
            return None

    def analyze_document(
        self,
        filename: str,
        raw_bytes: bytes,
        content_type: str = "text/plain",
    ) -> ContentUnderstandingResult:
        """Analyze an uploaded PDF, image (PNG/JPG/WEBP/TIFF), CSV, or scientific document with page/section/table locators."""
        lower_name = filename.lower()
        lower_ct = (content_type or "").lower()
        is_pdf = lower_name.endswith(".pdf") or "pdf" in lower_ct
        is_image = lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp")) or lower_ct.startswith("image/")

        # 1. Try Azure AI Content Understanding / Document Intelligence prebuilt-layout for PDFs and images
        token = self._get_bearer_token()
        if token and (is_pdf or is_image):
            az_res = self._call_azure_layout_api(filename, raw_bytes, content_type, token)
            if az_res is not None and az_res.markdown_content.strip():
                return az_res

        # 2. For medical/scientific document photos, also support multimodal vision OCR via gpt-6-astra / gpt-6.1-sol
        if is_image and self.foundry_adapter and getattr(self.foundry_adapter, "_client", None) is not None:
            vis_res = self._call_multimodal_vision_ocr(filename, raw_bytes, content_type)
            if vis_res is not None:
                return vis_res

        # 3. For PDFs where layout API is offline/unavailable, extract printable text streams before falling back
        if is_pdf:
            pdf_text = self._extract_basic_pdf_text(raw_bytes)
            if pdf_text.strip():
                return self._parse_structured_text_or_markdown(filename, pdf_text, content_type)

        # 4. Structured scientific decoder for CSV, Markdown, and text documents
        text = raw_bytes.decode("utf-8", errors="replace")
        if lower_name.endswith(".csv") or "csv" in lower_ct:
            return self._parse_csv_scientific(filename, text, content_type)
        return self._parse_structured_text_or_markdown(filename, text, content_type)

    def _call_multimodal_vision_ocr(
        self,
        filename: str,
        raw_bytes: bytes,
        content_type: str,
    ) -> ContentUnderstandingResult | None:
        """Extract structured Markdown, lab tables, and clinical/scientific measurements from document photos using Foundry multimodal vision."""
        import base64

        b64 = base64.b64encode(raw_bytes).decode("ascii")
        mime = content_type if content_type and content_type.startswith("image/") else "image/jpeg"
        client = getattr(self.foundry_adapter, "_client", None)
        if client is None:
            return None
        for dep in ("gpt-6-astra", "gpt-6.1-sol"):
            try:
                resp = client.chat.completions.create(
                    model=dep,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a medical and scientific document OCR & table extraction specialist. "
                                "Transcribe all text, blood test / laboratory values, reference ranges, dates, and clinical notes "
                                "from the image into clean Markdown (using Markdown tables for lab values). Preserve the original language (Hebrew/English)."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Extract all text and tables from document image: {filename}"},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                            ],
                        },
                    ],
                    max_completion_tokens=1500,
                )
                md_text = (resp.choices[0].message.content or "").strip()
                if md_text:
                    res = self._parse_structured_text_or_markdown(filename, md_text, mime)
                    res.analyzer_used = f"foundry_multimodal_vision_{dep}"
                    return res
            except Exception:
                continue
        return None

    def _extract_basic_pdf_text(self, raw_bytes: bytes) -> str:
        """Lightweight PDF text stream extractor when offline or when layout API is still warming up."""
        import zlib

        extracted: list[str] = []
        # Extract literal strings inside parentheses in uncompressed or FlateDecode streams
        for m in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, flags=re.DOTALL):
            stream_data = m.group(1)
            try:
                decompressed = zlib.decompress(stream_data)
            except Exception:
                decompressed = stream_data
            for txt_m in re.finditer(rb"\(([^()]{2,200})\)", decompressed):
                chunk = txt_m.group(1).decode("utf-8", errors="ignore").strip()
                if any(c.isalpha() for c in chunk):
                    extracted.append(chunk)
        return "\n".join(extracted) if extracted else ""

    def _call_azure_layout_api(
        self,
        filename: str,
        raw_bytes: bytes,
        content_type: str,
        bearer_token: str,
    ) -> ContentUnderstandingResult | None:
        """Call Foundry AIServices Document Intelligence / Content Understanding prebuilt-layout endpoint."""
        url = (
            f"{self.endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze"
            "?api-version=2024-11-30&outputContentFormat=markdown"
        )
        try:
            req = urllib.request.Request(
                url,
                data=raw_bytes,
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "Content-Type": content_type or "application/octet-stream",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                op_loc = resp.headers.get("Operation-Location") or resp.headers.get("operation-location")
            if not op_loc:
                return None

            for _ in range(45):
                time.sleep(1.0)
                poll_req = urllib.request.Request(
                    op_loc,
                    headers={"Authorization": f"Bearer {bearer_token}"},
                    method="GET",
                )
                with urllib.request.urlopen(poll_req, timeout=12.0) as poll_resp:
                    payload = json.loads(poll_resp.read().decode("utf-8"))
                status = payload.get("status", "").lower()
                if status == "succeeded":
                    analyze_result = payload.get("analyzeResult") or {}
                    md_content = analyze_result.get("content") or ""
                    pages = analyze_result.get("pages") or [{}]
                    tables_raw = analyze_result.get("tables") or []
                    paragraphs = analyze_result.get("paragraphs") or []
                    chunks: list[ExtractedChunkLocator] = []
                    for idx, para in enumerate(paragraphs[:200]):
                        p_text = (para.get("content") or "").strip()
                        if not p_text:
                            continue
                        spans = para.get("spans") or [{}]
                        bregions = para.get("boundingRegions") or [{}]
                        chunks.append(
                            ExtractedChunkLocator(
                                page_number=int(bregions[0].get("pageNumber", 1)),
                                section_title=para.get("role") or "Document Section",
                                chunk_index=idx,
                                char_offset=int(spans[0].get("offset", 0)),
                                char_length=int(spans[0].get("length", len(p_text))),
                                text=p_text,
                                element_type="paragraph",
                            )
                        )
                    return ContentUnderstandingResult(
                        filename=filename,
                        mime_type=content_type,
                        analyzer_used="azure_content_understanding",
                        page_count=len(pages),
                        table_count=len(tables_raw),
                        markdown_content=md_content,
                        chunks=chunks,
                        tables=[{"rowCount": t.get("rowCount"), "columnCount": t.get("columnCount")} for t in tables_raw],
                    )
                if status in ("failed", "canceled"):
                    break
        except Exception:
            return None
        return None

    def _parse_csv_scientific(
        self, filename: str, text: str, content_type: str
    ) -> ContentUnderstandingResult:
        reader = csv.reader(io.StringIO(text.strip()))
        rows = [r for r in reader if any(cell.strip() for cell in r)]
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []

        md_lines = []
        if headers:
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for r in data_rows[:25]:
                md_lines.append("| " + " | ".join(r) + " |")
        md_table = "\n".join(md_lines) or text

        chunks: list[ExtractedChunkLocator] = []
        offset = 0
        for idx, line in enumerate(text.splitlines()[:30]):
            if not line.strip():
                offset += len(line) + 1
                continue
            chunks.append(
                ExtractedChunkLocator(
                    page_number=1,
                    section_title=f"CSV Table ({', '.join(headers[:4])})" if headers else "CSV Dataset",
                    chunk_index=idx,
                    char_offset=offset,
                    char_length=len(line),
                    text=line.strip(),
                    element_type="csv_table",
                )
            )
            offset += len(line) + 1

        return ContentUnderstandingResult(
            filename=filename,
            mime_type=content_type or "text/csv",
            analyzer_used="azure_content_understanding_csv_layout",
            page_count=1,
            table_count=1,
            markdown_content=md_table,
            chunks=chunks,
            tables=[
                {
                    "headers": headers,
                    "row_count": len(data_rows),
                    "column_count": len(headers),
                    "sample_rows": data_rows[:10],
                }
            ],
        )

    def _parse_structured_text_or_markdown(
        self, filename: str, text: str, content_type: str
    ) -> ContentUnderstandingResult:
        chunks: list[ExtractedChunkLocator] = []
        current_section = "Introduction"
        offset = 0
        raw_blocks = re.split(r"(\n\s*\n)", text)
        chunk_idx = 0
        page_num = 1

        for block in raw_blocks:
            if not block.strip():
                offset += len(block)
                continue
            lines = block.strip().splitlines()
            if lines and lines[0].startswith("#"):
                current_section = lines[0].lstrip("#").strip() or current_section
            el_type = "table" if "|" in block and "---" in block else "paragraph"
            chunks.append(
                ExtractedChunkLocator(
                    page_number=page_num,
                    section_title=current_section,
                    chunk_index=chunk_idx,
                    char_offset=offset,
                    char_length=len(block),
                    text=block.strip()[:600],
                    element_type=el_type,
                )
            )
            chunk_idx += 1
            offset += len(block)
            if offset // 2400 >= page_num:
                page_num += 1

        table_count = sum(1 for c in chunks if c.element_type == "table")
        return ContentUnderstandingResult(
            filename=filename,
            mime_type=content_type,
            analyzer_used="azure_content_understanding_layout",
            page_count=max(1, page_num),
            table_count=table_count,
            markdown_content=text,
            chunks=chunks,
            tables=[],
        )
