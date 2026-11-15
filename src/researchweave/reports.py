"""Report exporter for ResearchWeave (Markdown, Word .docx with native RTL/LTR BiDi runs, and PDF)."""

from __future__ import annotations

import html
import io
import re
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
    is_he = inv.get("report_language", "en").lower().startswith("he") or any(
        "\u0590" <= ch <= "\u05ff" for ch in inv.get("objective", "")
    )
    is_complete = inv.get("status") == "completed"
    tot_in_tok = sum(int(ag.get("input_tokens") or 0) for ag in agents) or sum(
        int(t.get("input_tokens") or 0) for t in tasks
    )
    tot_out_tok = sum(int(ag.get("output_tokens") or 0) for ag in agents) or sum(
        int(t.get("output_tokens") or 0) for t in tasks
    )
    tot_tok = sum(int(ag.get("total_tokens") or 0) for ag in agents) or sum(
        int(t.get("total_tokens") or 0) for t in tasks
    )

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
            "## 1. תקציר מנהלים, טלמטריה ומטרת המחקר",
            f"- **מטרת המחקר הנוכחית:** {inv['objective']}",
            f"- **סטטוס ריצה:** `{inv['status']}` | **מצב אוטונומיה:** `{inv['autonomy_mode']}`",
            f"- **מאגר מודלים פעיל:** `{', '.join(inv.get('model_pool', []))}`",
            f"- **מספר סוכנים פעילים:** `{len(agents)}` | **משימות שהושלמו:** `{sum(1 for t in tasks if t.get('status') == 'completed')}/{len(tasks)}`",
            f"- **סה\"כ טוקנים:** `{tot_tok:,}` (`{tot_in_tok:,}` קלט / `{tot_out_tok:,}` פלט)",
            f"- **עלות משוערת:** `${inv.get('estimated_spend_usd', 0.0):.4f}` | **זמן ריצה מדוד:** `{inv.get('runtime_seconds', 0.0):.2f}s`",
            "",
            "## 2. הבחנה מדעית: ממצאים מאומתים לעומת השערות",
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
            "## 1. Executive Summary, Telemetry & Research Objective",
            f"- **Current Objective:** {inv['objective']}",
            f"- **Run Status:** `{inv['status']}` | **Autonomy Mode:** `{inv['autonomy_mode']}`",
            f"- **Active Model Pool:** `{', '.join(inv.get('model_pool', []))}`",
            f"- **Active Specialist Agents:** `{len(agents)}` | **Tasks Completed:** `{sum(1 for t in tasks if t.get('status') == 'completed')}/{len(tasks)}`",
            f"- **Token Usage (Input / Output / Total):** `{tot_in_tok:,} in / {tot_out_tok:,} out ({tot_tok:,} total tokens)`",
            f"- **Estimated Spend:** `${inv.get('estimated_spend_usd', 0.0):.4f}` | **Measured Runtime:** `{inv.get('runtime_seconds', 0.0):.2f}s`",
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

    state_labels_he = {
        "reviewed_verified": "ממצא מאומת (REVIEWED_VERIFIED)",
        "calculated": "חישוב מאומת (CALCULATED)",
        "observed": "תצפית מבוססת מקור (OBSERVED)",
        "hypothesis": "השערת מחקר לבדיקה (HYPOTHESIS)",
        "contradicted": "ממצא סותר (CONTRADICTED)",
        "unresolved": "לא מוכרע (UNRESOLVED)",
    }

    lines.append("### ממצאים וחישובים מאומתים" if is_he else "### Verified & Calculated Findings")
    if verified:
        for c in verified:
            refs = ", ".join(f"`[{sid}]`" for sid in c.get("supporting_source_ids", [])) or ("פנימי" if is_he else "internal")
            if is_he:
                lbl = state_labels_he.get(c["verification_state"], c["verification_state"].upper())
                reviewer = f" *(נבדק ע\"י `{c.get('checked_by_agent')}`)*" if c.get("checked_by_agent") else ""
                lines.append(
                    f"- **[{lbl}]** {c['statement']} (רמת ביטחון: `{c['confidence']:.2f}`, מקורות: {refs}){reviewer}"
                )
                if c.get("reviewer_notes"):
                    lines.append(f"  - *הערת אימות:* {c['reviewer_notes']}")
            else:
                reviewer = f" *(Checked by `{c.get('checked_by_agent')}`)*" if c.get("checked_by_agent") else ""
                lines.append(
                    f"- **[{c['verification_state'].upper()}]** {c['statement']} (Confidence: `{c['confidence']:.2f}`, Sources: {refs}){reviewer}"
                )
                if c.get("reviewer_notes"):
                    lines.append(f"  - *Verification Note:* {c['reviewer_notes']}")
    else:
        lines.append("- *טרם נרשמו ממצאים מאומתים.*" if is_he else "- *No independently verified findings recorded yet.*")

    lines.append("")
    lines.append(
        "### השערות פתוחות, סתירות ואי-ודאות"
        if is_he
        else "### Active Hypotheses, Contradictions & Unresolved Questions"
    )
    if hypotheses:
        for c in hypotheses:
            refs = ", ".join(f"`[{sid}]`" for sid in c.get("supporting_source_ids", [])) or ("ללא" if is_he else "none")
            if is_he:
                lbl = state_labels_he.get(c["verification_state"], c["verification_state"].upper())
                lines.append(
                    f"- **[{lbl}]** {c['statement']} (רמת ביטחון: `{c['confidence']:.2f}`, מקורות: {refs})"
                )
                if c.get("reviewer_notes"):
                    lines.append(f"  - *ביקורת אפיסטמית וגבולות אי-ודאות:* {c['reviewer_notes']}")
            else:
                lines.append(
                    f"- **[{c['verification_state'].upper()}]** {c['statement']} (Confidence: `{c['confidence']:.2f}`, Sources: {refs})"
                )
                if c.get("reviewer_notes"):
                    lines.append(f"  - *Uncertainty / Reviewer Note:* {c['reviewer_notes']}")
    else:
        lines.append("- *טרם נרשמו השערות פתוחות.*" if is_he else "- *No open hypotheses recorded yet.*")

    lines.append("")
    lines.append(
        "## 3. צוות סוכנים דינמי וחישובים שבוצעו"
        if is_he
        else "## 3. Dynamic Specialist Team & Computational Artifacts"
    )
    for ag in agents:
        ag_tok = int(ag.get("total_tokens") or 0)
        ag_dur = float(ag.get("duration_seconds") or 0.0)
        if is_he:
            lines.append(
                f"- **`{ag['name']}`** (מודל: `{ag['assigned_model']}` | טוקנים: `{ag_tok:,}` | זמן: `{ag_dur:.2f}s`): {ag['role_title']}"
            )
        else:
            lines.append(
                f"- **{ag['name']}** (`{ag['role_title']}` — Model: `{ag['assigned_model']}` | Tokens: `{ag_tok:,}` | Time: `{ag_dur:.2f}s`): {ag['description']}"
            )

    lines.append("")
    for t in tasks:
        t_tok = int(t.get("total_tokens") or 0)
        t_dur = float(t.get("duration_seconds") or 0.0)
        if is_he:
            lines.append(
                f"### משימה: {t['title']} (`{t['status']}` — סוכן: `{t.get('assigned_agent_name') or 'coordinator'}` | `{t_tok:,}` טוקנים | `{t_dur:.2f}s`)"
            )
        else:
            lines.append(
                f"### Task: {t['title']} (`{t['status']}` — `{t.get('assigned_agent_name') or 'coordinator'}` | `{t_tok:,} tokens` | `{t_dur:.2f}s`)"
            )
        if t.get("code_executed"):
            lines.extend(
                [
                    "```python",
                    t["code_executed"],
                    "```",
                    f"**פלט חישוב מבודד (Sandbox Output):** `{t.get('code_output') or 'none'}`"
                    if is_he
                    else f"**Isolated Sandbox Output:** `{t.get('code_output') or 'none'}`",
                ]
            )
        elif t.get("result_summary"):
            summary_text = t["result_summary"]
            if t.get("kind") in ("hypothesis_test", "independent_review") and len(summary_text) > 420:
                summary_text = summary_text[:420].rstrip() + "... *(הניתוח המלא מוצג בסעיף 2 לעיל)*" if is_he else summary_text[:420].rstrip() + "... *(Full analysis in Section 2 above)*"
            lines.append(summary_text)
        lines.append("")

    if brain_paths:
        lines.append(
            "## 4. נתיבי ידע מקושרים במוח הארגוני (Company Brain)"
            if is_he
            else "## 4. Company Brain Connected Knowledge Paths"
        )
        for p in brain_paths[:10]:
            lines.append(f"- `{p['path']}` (Sources: {', '.join(p.get('supporting_sources', []))})")
        lines.append("")

    if len(inv.get("objective_history", [])) > 1:
        lines.append(
            "## 5. היסטוריית שינויי מטרת המחקר בזמן ריצה"
            if is_he
            else "## 5. Objective Revision History (Live Researcher Steering)"
        )
        for rev in inv["objective_history"]:
            lines.append(
                f"- **Rev {rev['revision']}** ({rev['created_at']} by `{rev['updated_by']}`): {rev['objective']} — *{rev['reason']}*"
            )
        lines.append("")

    lines.append("## 6. מקורות מידע וציטוטים" if is_he else "## 6. Cited Sources & Provenance")
    if sources:
        for s in sources:
            lines.append(
                f"- **`[{s['id']}]` {s['title']}** (`{s['source_type']}`) — `{s['uri_or_path']}` (SHA-256: `{s['content_hash'][:12]}...`)"
            )
    else:
        lines.append("- *No active sources.*")

    return "\n".join(lines) + "\n"


def _build_bidi_runs_xml(text: str, rtl: bool = False, bold: bool = False, size_half_pts: int = 22) -> str:
    """Split mixed Hebrew/English/Code/Math segments into properly tagged OpenXML <w:r> runs.

    In Microsoft Word, mixed Hebrew + English/LaTeX/code scrambles when placed in a single
    run without `<w:rtl/>` on Hebrew runs and LTR isolation on code/math runs.
    """
    # Split by inline code `...` or LaTeX math $...$ first
    tokens = re.split(r"(`[^`]+`|\$\$[^$]+\$\$|\$[^$]+\$)", text)
    runs: list[str] = []
    b_tag = "<w:b/><w:bCs/>" if bold else ""
    sz_tag = f'<w:sz w:val="{size_half_pts}"/><w:szCs w:val="{size_half_pts}"/>'
    font_tag = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
    code_font_tag = '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Arial"/>'

    for tok in tokens:
        if not tok:
            continue
        is_code_or_math = (tok.startswith("`") and tok.endswith("`")) or (tok.startswith("$") and tok.endswith("$"))
        clean_tok = tok.strip("`") if tok.startswith("`") else tok
        has_hebrew = any("\u0590" <= ch <= "\u05ff" for ch in clean_tok)

        if is_code_or_math and not has_hebrew:
            # Force LTR run for inline code, IDs, URLs, and LaTeX equations
            esc = html.escape(clean_tok)
            runs.append(
                f"<w:r><w:rPr>{code_font_tag}{b_tag}{sz_tag}</w:rPr>"
                f'<w:t xml:space="preserve">\u2066{esc}\u2069</w:t></w:r>'
            )
        else:
            # Remove markdown ** markers inside normal prose and render bold sub-segments
            sub_parts = re.split(r"(\*\*[^*]+\*\*)", clean_tok)
            for sp in sub_parts:
                if not sp:
                    continue
                sub_bold = bold or (sp.startswith("**") and sp.endswith("**"))
                sub_text = sp[2:-2] if (sp.startswith("**") and sp.endswith("**")) else sp
                sub_has_he = any("\u0590" <= ch <= "\u05ff" for ch in sub_text)
                rtl_run_tag = "<w:rtl/>" if (rtl or sub_has_he) else ""
                sb_tag = "<w:b/><w:bCs/>" if sub_bold else ""
                esc = html.escape(sub_text)
                runs.append(
                    f"<w:r><w:rPr>{font_tag}{sb_tag}{sz_tag}{rtl_run_tag}</w:rPr>"
                    f'<w:t xml:space="preserve">{esc}</w:t></w:r>'
                )
    return "".join(runs)


def export_docx_bytes(markdown_text: str, title: str, rtl: bool = False) -> bytes:
    """Create a valid OpenXML Word (.docx) document with proper BiDi RTL/LTR paragraph and run formatting."""
    paragraphs_xml: list[str] = []
    is_doc_rtl = rtl or any("\u0590" <= ch <= "\u05ff" for ch in (title + markdown_text[:400]))
    rtl_ppr = '<w:bidi/><w:jc w:val="both"/>' if is_doc_rtl else ""
    ltr_code_ppr = '<w:bidi w:val="0"/><w:jc w:val="left"/><w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>'

    in_code_block = False
    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            # Code blocks are strictly Left-to-Right (LTR) with monospace font so Python code never reverses in Hebrew docs
            esc = html.escape(raw_line)
            paragraphs_xml.append(
                f"<w:p><w:pPr>{ltr_code_ppr}</w:pPr>"
                '<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
                '<w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr>'
                f'<w:t xml:space="preserve">{esc}</w:t></w:r></w:p>'
            )
            continue

        if not stripped:
            paragraphs_xml.append(f"<w:p><w:pPr>{rtl_ppr}</w:pPr></w:p>")
            continue

        if stripped.startswith("# "):
            runs = _build_bidi_runs_xml(stripped[2:].strip(), rtl=is_doc_rtl, bold=True, size_half_pts=34)
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading1"/>{rtl_ppr}<w:spacing w:before="240" w:after="120"/></w:pPr>{runs}</w:p>'
            )
        elif stripped.startswith("## "):
            runs = _build_bidi_runs_xml(stripped[3:].strip(), rtl=is_doc_rtl, bold=True, size_half_pts=28)
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading2"/>{rtl_ppr}<w:spacing w:before="200" w:after="100"/></w:pPr>{runs}</w:p>'
            )
        elif stripped.startswith("### "):
            runs = _build_bidi_runs_xml(stripped[4:].strip(), rtl=is_doc_rtl, bold=True, size_half_pts=24)
            paragraphs_xml.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading3"/>{rtl_ppr}<w:spacing w:before="160" w:after="80"/></w:pPr>{runs}</w:p>'
            )
        else:
            runs = _build_bidi_runs_xml(stripped, rtl=is_doc_rtl, bold=False, size_half_pts=22)
            paragraphs_xml.append(
                f'<w:p><w:pPr>{rtl_ppr}<w:spacing w:after="100"/></w:pPr>{runs}</w:p>'
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
    # Standard PDF Type1 Helvetica supports Latin-1 / CP1252 only.
    # For non-Latin scripts (such as Hebrew), strip raw markdown symbols and preserve Latin/numeric/math identifiers
    # while noting that full Hebrew/KaTeX PDF rendering is served via the browser Print-to-PDF view.
    cleaned = re.sub(r"[\u0590-\u05FF]+", "[Hebrew-RTL]", text)
    ascii_safe = cleaned.encode("latin-1", errors="replace").decode("latin-1")
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
