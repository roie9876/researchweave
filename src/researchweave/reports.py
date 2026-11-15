"""Report exporter for ResearchWeave (Markdown, Word .docx, and PDF)."""

from __future__ import annotations

import html
import io
import zipfile
from typing import Any


def build_live_report_markdown(
    inv: dict[str, Any],
    agents: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    brain_paths: list[dict[str, Any]],
) -> str:
    """Compile an evidence-backed research report separating verified results from hypotheses."""
    is_he = inv.get("report_language", "en").lower().startswith("he")
    is_complete = inv.get("status") == "completed"

    if is_he:
        banner = (
            "✅ **דוח מחקר סופי (מאומת ומבוסס ראיות)**"
            if is_complete
            else "⏳ **טיוטת מחקר חיה — המחקר עדיין בתהליך (לא סופי)**"
        )
        lines = [
            f"# {inv['title']}",
            "",
            banner,
            "",
            "## 1. תקציר מנהלים ומטרת המחקר",
            f"- **מטרת המחקר הנוכחית:** {inv['objective']}",
            f"- **סטטוס ריצה:** `{inv['status']}` | **מצב אוטונומיה:** `{inv['autonomy_mode']}`",
            f"- **מאגר מודלים פעיל:** `{', '.join(inv.get('model_pool', []))}`",
            f"- **עלות משוערת:** `${inv.get('estimated_spend_usd', 0.0):.4f}` | **זמן ריצה:** `{inv.get('runtime_seconds', 0.0):.1f}s`",
            "",
            "## 2. הבחנה מדעית: ממצאים מאומתים לעומת השערות (Hypotheses)",
            "> מערכת ResearchWeave מפרידה באופן מחמיר בין חישובים ומדידות שאומתו על ידי סוכן ביקורת עצמאי לבין השערות מחקריות הדורשות ניסוי נוסף.",
            "",
        ]
    else:
        banner = (
            "✅ **FINAL RESEARCH REPORT — Evidence-Backed & Independently Checked**"
            if is_complete
            else "⏳ **LIVE EVOLVING DRAFT — Investigation in Progress (Incomplete)**"
        )
        lines = [
            f"# {inv['title']}",
            "",
            banner,
            "",
            "## 1. Executive Summary & Research Objective",
            f"- **Current Objective:** {inv['objective']}",
            f"- **Run Status:** `{inv['status']}` | **Autonomy Mode:** `{inv['autonomy_mode']}`",
            f"- **Active Model Pool:** `{', '.join(inv.get('model_pool', []))}`",
            f"- **Estimated Spend:** `${inv.get('estimated_spend_usd', 0.0):.4f}` | **Runtime:** `{inv.get('runtime_seconds', 0.0):.1f}s`",
            "",
            "## 2. Scientific Epistemology: Verified Findings vs. Hypotheses",
            "> ResearchWeave strictly separates independently checked calculations and source-backed observations from unverified hypotheses.",
            "",
        ]

    verified = [
        c
        for c in claims
        if c["verification_state"] in ("reviewed_verified", "calculated", "observed")
    ]
    hypotheses = [
        c
        for c in claims
        if c["verification_state"] in ("hypothesis", "contradicted", "unresolved")
    ]

    lines.append("### Verified & Calculated Findings" if not is_he else "### ממצאים וחישובים מאומתים")
    if verified:
        for c in verified:
            refs = ", ".join(f"`[{sid}]`" for sid in c.get("supporting_source_ids", [])) or "internal"
            reviewer = f" *(Checked by `{c.get('checked_by_agent')}`)*" if c.get("checked_by_agent") else ""
            lines.append(
                f"- **[{c['verification_state'].upper()}]** {c['statement']} (Confidence: `{c['confidence']:.2f}`, Sources: {refs}){reviewer}"
            )
            if c.get("reviewer_notes"):
                lines.append(f"  - *Verification Note:* {c['reviewer_notes']}")
    else:
        lines.append("- *No independently verified findings recorded yet.*")

    lines.append("")
    lines.append(
        "### Active Hypotheses, Contradictions & Unresolved Questions"
        if not is_he
        else "### השערות פתוחות, סתירות ואי-ודאות"
    )
    if hypotheses:
        for c in hypotheses:
            refs = ", ".join(f"`[{sid}]`" for sid in c.get("supporting_source_ids", [])) or "none"
            lines.append(
                f"- **[{c['verification_state'].upper()}]** {c['statement']} (Confidence: `{c['confidence']:.2f}`, Sources: {refs})"
            )
            if c.get("reviewer_notes"):
                lines.append(f"  - *Uncertainty / Reviewer Note:* {c['reviewer_notes']}")
    else:
        lines.append("- *No open hypotheses recorded yet.*")

    lines.append("")
    lines.append(
        "## 3. Dynamic Specialist Team & Computational Artifacts"
        if not is_he
        else "## 3. צוות סוכנים דינמי וחישובים שבוצעו"
    )
    for ag in agents:
        lines.append(
            f"- **{ag['name']}** (`{ag['role_title']}` — Model: `{ag['assigned_model']}`): {ag['description']}"
        )

    lines.append("")
    for t in tasks:
        lines.append(f"### Task: {t['title']} (`{t['status']}` — `{t.get('assigned_agent_name') or 'coordinator'}`)")
        if t.get("result_summary"):
            lines.append(t["result_summary"])
        if t.get("code_executed"):
            lines.extend(
                [
                    "",
                    "```python",
                    t["code_executed"],
                    "```",
                    f"**Isolated Sandbox Output:** `{t.get('code_output') or 'none'}`",
                ]
            )
        lines.append("")

    if brain_paths:
        lines.append(
            "## 4. Company Brain Connected Knowledge Paths"
            if not is_he
            else "## 4. נתיבי ידע מקושרים במוח הארגוני (Company Brain)"
        )
        for p in brain_paths[:10]:
            lines.append(f"- `{p['path']}` (Sources: {', '.join(p.get('supporting_sources', []))})")
        lines.append("")

    if len(inv.get("objective_history", [])) > 1:
        lines.append(
            "## 5. Objective Revision History (Live Researcher Steering)"
            if not is_he
            else "## 5. היסטוריית שינויי מטרת המחקר בזמן ריצה"
        )
        for rev in inv["objective_history"]:
            lines.append(
                f"- **Rev {rev['revision']}** ({rev['created_at']} by `{rev['updated_by']}`): {rev['objective']} — *{rev['reason']}*"
            )
        lines.append("")

    lines.append("## 6. Cited Sources & Provenance" if not is_he else "## 6. מקורות מידע וציטוטים")
    if sources:
        for s in sources:
            lines.append(
                f"- **`[{s['id']}]` {s['title']}** (`{s['source_type']}`) — `{s['uri_or_path']}` (SHA-256: `{s['content_hash'][:12]}...`)"
            )
    else:
        lines.append("- *No active sources.*")

    return "\n".join(lines) + "\n"


def export_docx_bytes(markdown_text: str, title: str, rtl: bool = False) -> bytes:
    """Create a valid OpenXML Word (.docx) document without external binary dependencies."""
    paragraphs_xml: list[str] = []
    bidi_prop = "<w:bidi/>" if rtl else ""

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        escaped = html.escape(line)
        if line.startswith("# "):
            text = html.escape(line[2:].strip())
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading1"/>{bidi_prop}</w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>{text}</w:t></w:r></w:p>'
            )
        elif line.startswith("## "):
            text = html.escape(line[3:].strip())
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading2"/>{bidi_prop}</w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>{text}</w:t></w:r></w:p>'
            )
        elif line.startswith("### "):
            text = html.escape(line[4:].strip())
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading3"/>{bidi_prop}</w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>{text}</w:t></w:r></w:p>'
            )
        else:
            paragraphs_xml.append(
                f'<w:p><w:pPr>{bidi_prop}</w:pPr>'
                f'<w:r><w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
            )

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paragraphs_xml)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/></w:sectPr>"
        "</w:body></w:document>"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", document_xml)
    return buf.getvalue()


def _pdf_escape(text: str) -> str:
    ascii_safe = text.encode("ascii", errors="replace").decode("ascii")
    return ascii_safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def export_pdf_bytes(markdown_text: str, title: str) -> bytes:
    """Generate a valid standalone PDF 1.4 document containing the research report."""
    raw_lines = [f"ResearchWeave Report: {title}", "=" * 60, ""] + markdown_text.splitlines()
    wrapped: list[str] = []
    for line in raw_lines:
        clean = line.strip()
        if not clean:
            wrapped.append("")
            continue
        while len(clean) > 88:
            wrapped.append(clean[:88])
            clean = clean[88:]
        wrapped.append(clean)

    lines_per_page = 46
    pages = [
        wrapped[i : i + lines_per_page]
        for i in range(0, max(1, len(wrapped)), lines_per_page)
    ]

    objects: list[bytes] = []
    # 1: Catalog, 2: Pages, 3: Font
    page_obj_Numbers: list[int] = []
    content_obj_numbers: list[int] = []

    next_obj_num = 4
    for _ in pages:
        page_obj_Numbers.append(next_obj_num)
        content_obj_numbers.append(next_obj_num + 1)
        next_obj_num += 2

    kids_str = " ".join(f"{num} 0 R" for num in page_obj_Numbers)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids_str}] /Count {len(pages)} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for idx, page_lines in enumerate(pages):
        content_num = content_obj_numbers[idx]
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>"
        ).encode("ascii")
        objects.append(page_dict)

        stream_cmds = ["BT", "/F1 10 Tf", "50 745 Td", "14 TL"]
        for line in page_lines:
            stream_cmds.append(f"({_pdf_escape(line)}) Tj T*")
        stream_cmds.append("ET")
        stream_bytes = "\n".join(stream_cmds).encode("ascii")
        content_obj = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        objects.append(content_obj)

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref_offset = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))

    out.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return out.getvalue()
