"""
exports/docx.py
------------------
Renders exports._shared.ReportData into a professional DOCX using
python-docx. Same content, structure, and terminology as exports/pdf.py
- both read the identical ReportData shape (exports/_shared.py owns what
goes in a report; this module only lays it out).

UPGRADE (report-upgrade task): kept the existing summary/mood/
distribution sections exactly as before, and added the two new required
sections - the complete Companion conversation (grouped by conversation,
chronological, timestamped, User vs Sahay AI clearly labelled) and a
SEPARATE Chatbot History section - plus a light visual pass (a title
page block, a brand-coloured rule under each heading, a real table for
mood history instead of bullet lines, page numbers in the footer) so PDF
and DOCX read as the same report. python-docx is imported lazily inside
the function, matching this codebase's established pattern.
"""

from __future__ import annotations

import io

from exports._shared import ReportData

BRAND_HEX = "A6193C"   # components/theme.py COLORS["deep_blue"]
MUTED_HEX = "6B7280"
RULE_HEX = "E5D6D9"
FILL_HEX = "FAF0F2"


class DocxExportError(RuntimeError):
    """User-safe error message - never contains raw library internals."""


def build_docx_report(data: ReportData) -> bytes:
    """Returns DOCX bytes for the given (already-bounded, already-shaped)
    report data. Raises DocxExportError with a friendly message on any
    failure - never raises a raw python-docx exception to the caller."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError as exc:
        raise DocxExportError(
            "DOCX export isn't available right now - the required library isn't installed."
        ) from exc

    try:
        ctx = _Ctx(Pt, RGBColor, Cm, WD_ALIGN_PARAGRAPH, WD_TABLE_ALIGNMENT, qn, OxmlElement)
        doc = Document()
        _page_setup(doc, ctx)
        _header(doc, data, ctx)
        _summary_section(doc, data, ctx)

        if not data.has_any_data:
            p = doc.add_paragraph("No wellness activity was recorded in this period.")
            p.runs[0].italic = True
        else:
            _mood_section(doc, data, ctx)
            _distribution_section(doc, data, ctx)
            _conversations_overview(doc, data, ctx)
            _companion_section(doc, data, ctx)
            _chatbot_section(doc, data, ctx)

        _disclaimer_section(doc, data, ctx)
        _add_page_numbers(doc, ctx)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except DocxExportError:
        raise
    except Exception as exc:  # noqa: BLE001 - any python-docx-internal failure becomes a friendly error
        try:
            from backend.logging_config import get_logger
            get_logger(__name__).exception("DOCX report generation failed")
        except Exception:  # noqa: BLE001
            pass
        raise DocxExportError("Couldn't generate the DOCX report right now. Please try again.") from exc


class _Ctx:
    """Small holder so every section function gets the lazily-imported
    docx classes without re-importing them everywhere."""

    def __init__(self, Pt, RGBColor, Cm, ALIGN, TABLE_ALIGN, qn, OxmlElement):
        self.Pt, self.RGBColor, self.Cm = Pt, RGBColor, Cm
        self.ALIGN, self.TABLE_ALIGN = ALIGN, TABLE_ALIGN
        self.qn, self.OxmlElement = qn, OxmlElement
        self.brand = RGBColor.from_string(BRAND_HEX)
        self.muted = RGBColor.from_string(MUTED_HEX)


def _page_setup(doc, ctx) -> None:
    section = doc.sections[0]
    section.left_margin = section.right_margin = ctx.Cm(2.2)
    section.top_margin = section.bottom_margin = ctx.Cm(1.8)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = ctx.Pt(10.5)


def _rule(doc, ctx, color_hex: str = RULE_HEX) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = ctx.Pt(0)
    p.paragraph_format.space_after = ctx.Pt(6)
    pPr = p._p.get_or_add_pPr()
    border = ctx.OxmlElement("w:pBdr")
    bottom = ctx.OxmlElement("w:bottom")
    bottom.set(ctx.qn("w:val"), "single")
    bottom.set(ctx.qn("w:sz"), "8")
    bottom.set(ctx.qn("w:color"), color_hex)
    border.append(bottom)
    pPr.append(border)


def _heading(doc, ctx, text: str, level: int = 2) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = ctx.brand


def _header(doc, data: ReportData, ctx) -> None:
    title = doc.add_paragraph()
    title.alignment = ctx.ALIGN.LEFT
    run = title.add_run("Sahay AI")
    run.bold = True
    run.font.size = ctx.Pt(12)
    run.font.color.rgb = ctx.brand

    doc.add_heading("Wellness Reflection Report", level=1)
    _rule(doc, ctx, BRAND_HEX)

    def meta_line(label: str, value: str) -> None:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = ctx.Pt(2)
        r1 = p.add_run(f"{label}: ")
        r1.bold = True
        r1.font.size = ctx.Pt(9.5)
        r1.font.color.rgb = ctx.muted
        r2 = p.add_run(value)
        r2.font.size = ctx.Pt(9.5)
        r2.font.color.rgb = ctx.muted

    meta_line("Generated", data.generated_at)
    if data.display_name:
        meta_line("Prepared for", data.display_name)
    meta_line("Period", f"{data.period_start} - {data.period_end} ({data.period_days} days)")
    doc.add_paragraph()


def _summary_section(doc, data: ReportData, ctx) -> None:
    _heading(doc, ctx, "Summary", level=2)
    _rule(doc, ctx)
    lines = [
        f"Conversations in this period: {len(data.conversations_summary)}",
        f"Mood entries recorded: {len(data.mood_events)}",
        f"Relaxation activities completed: {data.activities_completed}",
    ]
    if data.stress_avg is not None:
        lines.append(f"Average recorded stress: {data.stress_avg}/5")
    if data.energy_avg is not None:
        lines.append(f"Average recorded energy: {data.energy_avg}/5")
    if data.sleep_avg is not None:
        lines.append(f"Average recorded sleep quality: {data.sleep_avg}/5")
    for line in lines:
        doc.add_paragraph(line, style="List Bullet")


def _shaded_cell(cell, ctx, hex_color: str) -> None:
    shd = ctx.OxmlElement("w:shd")
    shd.set(ctx.qn("w:val"), "clear")
    shd.set(ctx.qn("w:color"), "auto")
    shd.set(ctx.qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def _mood_section(doc, data: ReportData, ctx) -> None:
    if not data.mood_events:
        return
    _heading(doc, ctx, "Mood History", level=2)
    _rule(doc, ctx)
    cols = ["Date (UTC)", "Mood", "Source", "Stress", "Energy", "Sleep"]
    table = doc.add_table(rows=1, cols=len(cols))
    table.alignment = ctx.TABLE_ALIGN.LEFT
    table.style = "Light Grid Accent 1" if "Light Grid Accent 1" in [s.name for s in doc.styles] else "Table Grid"
    for i, name in enumerate(cols):
        cell = table.rows[0].cells[i]
        cell.text = name
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = ctx.Pt(9)
        cell.paragraphs[0].runs[0].font.color.rgb = ctx.RGBColor(0xFF, 0xFF, 0xFF)
        _shaded_cell(cell, ctx, BRAND_HEX)

    def scale(v):
        return f"{v}/5" if v is not None else "-"

    for m in data.mood_events:
        row = table.add_row().cells
        values = [m.get("date") or "-", m.get("mood") or "Neutral", m.get("source") or "",
                  scale(m.get("stress")), scale(m.get("energy")), scale(m.get("sleep"))]
        for i, value in enumerate(values):
            row[i].text = str(value)
            row[i].paragraphs[0].runs[0].font.size = ctx.Pt(9.5)
        if m.get("note"):
            note_p = doc.add_paragraph(f"   Note: {m['note']}")
            note_p.runs[0].italic = True
            note_p.runs[0].font.size = ctx.Pt(9)
            note_p.runs[0].font.color.rgb = ctx.muted
    doc.add_paragraph()


def _distribution_section(doc, data: ReportData, ctx) -> None:
    if not data.mood_distribution:
        return
    _heading(doc, ctx, "Approximate Mood Distribution", level=2)
    _rule(doc, ctx)
    for mood, count in sorted(data.mood_distribution.items(), key=lambda kv: -kv[1]):
        doc.add_paragraph(f"{mood}: {count}", style="List Bullet")


def _conversations_overview(doc, data: ReportData, ctx) -> None:
    if not data.conversations_summary:
        return
    _heading(doc, ctx, "Conversations Overview", level=2)
    _rule(doc, ctx)
    note_p = doc.add_paragraph("Titles and message counts for this period.")
    note_p.runs[0].font.size = ctx.Pt(9)
    note_p.runs[0].font.color.rgb = ctx.muted
    for c in data.conversations_summary:
        doc.add_paragraph(f"{c['date']}  {c['title']} ({c['message_count']} messages)", style="List Bullet")


def _add_speaker_line(doc, ctx, msg: dict) -> None:
    ts = msg.get("ts") or "time not recorded"
    ts_p = doc.add_paragraph()
    ts_p.paragraph_format.space_after = ctx.Pt(0)
    r = ts_p.add_run(f"[{ts}]")
    r.font.size = ctx.Pt(8)
    r.font.color.rgb = ctx.muted

    is_user = msg.get("role") == "User"
    speak_p = doc.add_paragraph()
    speak_p.paragraph_format.space_after = ctx.Pt(2)
    r1 = speak_p.add_run(f"{msg.get('role')}: ")
    r1.bold = True
    r1.font.size = ctx.Pt(9.5)
    r1.font.color.rgb = ctx.RGBColor(0x33, 0x33, 0x33) if is_user else ctx.brand

    body_p = doc.add_paragraph(msg.get("content") or "")
    body_p.paragraph_format.left_indent = ctx.Cm(0.5)
    body_p.paragraph_format.space_after = ctx.Pt(6)
    for run in body_p.runs:
        run.font.size = ctx.Pt(9.5)


def _companion_section(doc, data: ReportData, ctx) -> None:
    _heading(doc, ctx, "Sahay AI Companion \u2014 Complete Conversation", level=2)
    _rule(doc, ctx)
    if not data.companion_transcripts:
        p = doc.add_paragraph("No Companion messages were stored in this period.")
        p.runs[0].italic = True
        p.runs[0].font.color.rgb = ctx.muted
        return
    for convo in data.companion_transcripts:
        title_p = doc.add_paragraph()
        title_p.paragraph_format.space_before = ctx.Pt(8)
        r = title_p.add_run(convo["title"])
        r.bold = True
        r.font.size = ctx.Pt(10.5)
        if convo.get("started"):
            cap = doc.add_paragraph()
            cr = cap.add_run(f"Started {convo['started']}")
            cr.font.size = ctx.Pt(8)
            cr.font.color.rgb = ctx.muted
        for msg in convo["messages"]:
            _add_speaker_line(doc, ctx, msg)
        doc.add_paragraph()


def _chatbot_section(doc, data: ReportData, ctx) -> None:
    _heading(doc, ctx, "Chatbot History", level=2)
    _rule(doc, ctx)
    if data.chatbot_note:
        note_p = doc.add_paragraph(data.chatbot_note)
        note_p.runs[0].italic = True
        note_p.runs[0].font.size = ctx.Pt(9)
        note_p.runs[0].font.color.rgb = ctx.muted
    if not data.chatbot_messages:
        p = doc.add_paragraph("No chatbot messages were recorded in this session.")
        p.runs[0].italic = True
        p.runs[0].font.color.rgb = ctx.muted
        return
    for msg in data.chatbot_messages:
        _add_speaker_line(doc, ctx, msg)


def _disclaimer_section(doc, data: ReportData, ctx) -> None:
    doc.add_paragraph()
    _rule(doc, ctx)
    p = doc.add_paragraph()
    r = p.add_run(data.disclaimer)
    r.italic = True
    r.font.size = ctx.Pt(8)
    r.font.color.rgb = ctx.muted


def _add_page_numbers(doc, ctx) -> None:
    """Adds a 'Page X of Y' field to the footer so PDF and DOCX both
    carry page numbers, per the report-formatting requirement."""
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = ctx.ALIGN.CENTER
    p.text = ""

    def _field(instr: str):
        run = p.add_run()
        fld_begin = ctx.OxmlElement("w:fldChar")
        fld_begin.set(ctx.qn("w:fldCharType"), "begin")
        instr_el = ctx.OxmlElement("w:instrText")
        instr_el.set(ctx.qn("xml:space"), "preserve")
        instr_el.text = instr
        fld_sep = ctx.OxmlElement("w:fldChar")
        fld_sep.set(ctx.qn("w:fldCharType"), "separate")
        fld_end = ctx.OxmlElement("w:fldChar")
        fld_end.set(ctx.qn("w:fldCharType"), "end")
        run._r.append(fld_begin)
        run._r.append(instr_el)
        run._r.append(fld_sep)
        run._r.append(fld_end)

    r0 = p.add_run("Page ")
    r0.font.size = ctx.Pt(8)
    r0.font.color.rgb = ctx.muted
    _field("PAGE")
    r1 = p.add_run(" of ")
    r1.font.size = ctx.Pt(8)
    r1.font.color.rgb = ctx.muted
    _field("NUMPAGES")
