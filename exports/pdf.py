"""
exports/pdf.py
-----------------
Renders an exports._shared.ReportData into a professional A4 PDF using
fpdf2. All content decisions (what data, bounded window, disclaimer
wording) live in exports/_shared.py; this module only lays that
already-shaped content out.

ROOT CAUSE OF "Couldn't generate the PDF report right now" (found by
source analysis - fpdf2 could not be installed in the authoring sandbox,
so the failure was traced, not reproduced live; see the task report):

1. The old code used fpdf2's built-in Helvetica core font, which can only
   encode Latin-1. The report's own fixed text contains an em dash
   (U+2014) - in DISCLAIMER, which is written into EVERY report - and
   U+2014 is not in Latin-1, so fpdf2 raised FPDFUnicodeEncodingException
   on every PDF. The generic `except Exception` in build_pdf_report()
   then converted that into the friendly-but-misleading message. The DOCX
   export was unaffected because Word has no such restriction.
2. Two consecutive multi_cell(0, ...) calls (a mood entry followed by its
   note) hit fpdf2's default new_x=RIGHT, leaving the cursor at the right
   margin and raising "Not enough horizontal space" on the second call.
3. `cell(..., ln=True)` is deprecated in fpdf2 >= 2.7.

FIX: a bundled Unicode TrueType font (assets/fonts/DejaVuSans*.ttf) and
explicit new_x/new_y on every multi-line call. If the bundled fonts are
missing, the module falls back to Helvetica with a Latin-1 sanitiser so a
PDF is still produced. Characters the chosen font cannot draw (e.g. Hindi
Devanagari, emoji) are replaced with "?" and the PDF says so on the page -
the DOCX carries the full text.
"""

from __future__ import annotations

from pathlib import Path

from exports._shared import ReportData

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FONT_FILES = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
    "I": "DejaVuSans-Oblique.ttf",
}

# Sahay brand crimson (components/theme.py COLORS["deep_blue"] = #A6193C)
BRAND = (166, 25, 60)
INK = (30, 36, 48)
MUTED = (107, 114, 128)
LIGHT_FILL = (250, 240, 242)
RULE = (225, 214, 217)

_LATIN1_MAP = str.maketrans({
    "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"',
    "\u201d": '"', "\u2026": "...", "\u2022": "*", "\u00a0": " ", "\u2192": "->",
})
_DROP = {"\ufe0f", "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"}


class PdfExportError(RuntimeError):
    """User-safe error message - never contains raw library internals."""


def _font_paths() -> dict[str, Path] | None:
    paths = {style: _FONT_DIR / name for style, name in _FONT_FILES.items()}
    return paths if all(p.is_file() for p in paths.values()) else None


class _TextPrep:
    """Makes text safe for the active font and counts what had to be replaced."""

    def __init__(self, unicode_font: bool, regular_font_path: Path | None):
        self.unicode_font = unicode_font
        self.replaced = 0
        self._cmap = None
        if unicode_font and regular_font_path is not None:
            try:  # fontTools is a hard dependency of fpdf2
                from fontTools.ttLib import TTFont
                self._cmap = set(TTFont(str(regular_font_path)).getBestCmap().keys())
            except Exception:  # noqa: BLE001 - fall back to letting fpdf2 handle glyphs
                self._cmap = None

    def __call__(self, text) -> str:
        out = []
        for ch in str(text if text is not None else ""):
            if ch == "\n":
                out.append(ch)
            elif ch == "\t":
                out.append("    ")
            elif ch in _DROP:
                continue
            elif self.unicode_font:
                if self._cmap is None or ord(ch) in self._cmap:
                    out.append(ch)
                else:
                    out.append("?")
                    self.replaced += 1
            else:
                mapped = ch.translate(_LATIN1_MAP)
                for m in mapped:
                    try:
                        m.encode("latin-1")
                        out.append(m)
                    except UnicodeEncodeError:
                        out.append("?")
                        self.replaced += 1
        return "".join(out)


def build_pdf_report(data: ReportData) -> bytes:
    """Returns PDF bytes for the given (already-bounded, already-shaped)
    report data. Raises PdfExportError with a friendly message on any
    failure - never raises a raw fpdf2 exception to the caller."""
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise PdfExportError(
            "PDF export isn't available right now - the required library isn't installed."
        ) from exc

    try:
        return _render(FPDF, data)
    except PdfExportError:
        raise
    except Exception as exc:  # noqa: BLE001 - any fpdf2-internal failure becomes a friendly error
        # Log the real cause server-side so it is never hidden again.
        try:
            from backend.logging_config import get_logger
            get_logger(__name__).exception("PDF report generation failed")
        except Exception:  # noqa: BLE001
            pass
        raise PdfExportError("Couldn't generate the PDF report right now. Please try again.") from exc


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render(FPDF, data: ReportData) -> bytes:
    font_paths = _font_paths()
    unicode_font = font_paths is not None
    prep = _TextPrep(unicode_font, font_paths[""] if font_paths else None)
    family = "DejaVu" if unicode_font else "Helvetica"

    generated_label = prep(data.generated_at)

    class ReportPDF(FPDF):
        def header(self):  # drawn on every page
            self.set_fill_color(*BRAND)
            self.rect(0, 0, self.w, 12, style="F")
            self.set_xy(self.l_margin, 3.2)
            self.set_font(family, "B", 10)
            self.set_text_color(255, 255, 255)
            self.cell(80, 6, "Sahay AI", new_x="RIGHT", new_y="TOP")
            self.set_font(family, "", 9)
            self.cell(0, 6, "Wellness Reflection Report", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*INK)
            self.set_y(20)

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*RULE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_font(family, "", 8)
            self.set_text_color(*MUTED)
            self.cell(0, 8, f"Generated {generated_label}", align="L", new_x="RIGHT", new_y="TOP")
            self.set_x(self.l_margin)
            self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*INK)

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    if unicode_font:
        for style, path in font_paths.items():
            pdf.add_font("DejaVu", style, str(path))
    pdf.set_margins(18, 20, 18)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.alias_nb_pages()
    pdf.set_title("Sahay AI Wellness Reflection Report")
    pdf.set_author("Sahay AI")
    pdf.add_page()

    content_w = pdf.w - pdf.l_margin - pdf.r_margin

    def font(style="", size=10, color=INK):
        pdf.set_font(family, style, size)
        pdf.set_text_color(*color)

    def need_space(height):
        if pdf.get_y() + height > pdf.h - 20:
            pdf.add_page()

    def para(text, h=5.5, style="", size=10, color=INK, indent=0.0):
        font(style, size, color)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(content_w - indent, h, prep(text), new_x="LMARGIN", new_y="NEXT")

    def section(title):
        need_space(22)
        pdf.ln(4)
        font("B", 13, BRAND)
        pdf.cell(0, 8, prep(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*BRAND)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 24, pdf.get_y())
        pdf.set_line_width(0.2)
        pdf.ln(3)
        font()

    # ---- Title block ---------------------------------------------------
    font("B", 22, INK)
    pdf.cell(0, 11, "Wellness Reflection Report", new_x="LMARGIN", new_y="NEXT")
    font("", 10, MUTED)
    meta = [("Generated", data.generated_at)]
    if data.display_name:
        meta.append(("Prepared for", data.display_name))
    meta.append(("Period", f"{data.period_start} - {data.period_end} ({data.period_days} days)"))
    for label, value in meta:
        pdf.set_x(pdf.l_margin)
        font("B", 10, MUTED)
        pdf.cell(32, 6, prep(label), new_x="RIGHT", new_y="TOP")
        font("", 10, INK)
        pdf.multi_cell(content_w - 32, 6, prep(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ---- Summary ---------------------------------------------------------
    section("Summary")
    stats = [
        ("Conversations", str(len(data.conversations_summary))),
        ("Mood entries", str(len(data.mood_events))),
        ("Activities completed", str(data.activities_completed)),
    ]
    gap = 4
    card_w = (content_w - gap * 2) / 3
    top = pdf.get_y()
    for i, (label, value) in enumerate(stats):
        x = pdf.l_margin + i * (card_w + gap)
        pdf.set_fill_color(*LIGHT_FILL)
        pdf.set_draw_color(*RULE)
        pdf.rect(x, top, card_w, 20, style="DF")
        pdf.set_xy(x, top + 2.5)
        font("B", 16, BRAND)
        pdf.cell(card_w, 8, prep(value), align="C", new_x="LEFT", new_y="NEXT")
        pdf.set_x(x)
        font("", 8.5, MUTED)
        pdf.cell(card_w, 6, prep(label), align="C", new_x="LEFT", new_y="NEXT")
    pdf.set_y(top + 24)

    averages = []
    if data.stress_avg is not None:
        averages.append(("Average recorded stress", f"{data.stress_avg}/5"))
    if data.energy_avg is not None:
        averages.append(("Average recorded energy", f"{data.energy_avg}/5"))
    if data.sleep_avg is not None:
        averages.append(("Average recorded sleep quality", f"{data.sleep_avg}/5"))
    for label, value in averages:
        pdf.set_x(pdf.l_margin)
        font("", 10, INK)
        pdf.cell(content_w - 30, 6.5, prep(label), border="B", new_x="RIGHT", new_y="TOP")
        font("B", 10, INK)
        pdf.cell(30, 6.5, prep(value), border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    if not data.has_any_data:
        pdf.ln(6)
        para("No wellness activity was recorded in this period.", style="I", color=MUTED)
    else:
        _mood_section(pdf, data, prep, family, section, para, font, need_space, content_w)
        _distribution_section(pdf, data, prep, section, font, content_w)
        _conversation_overview(pdf, data, prep, section, font, need_space, content_w)
        _transcript_section(
            pdf, "Sahay AI Companion - Complete Conversation", data.companion_transcripts,
            "No Companion messages were stored in this period.", prep, section, para, font, need_space, content_w,
            grouped=True,
        )
        _chatbot_section(pdf, data, prep, section, para, font, need_space, content_w)

    # ---- Disclaimer ------------------------------------------------------
    pdf.ln(6)
    need_space(30)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    para(data.disclaimer, h=4.6, style="I", size=8, color=MUTED)

    if prep.replaced:
        pdf.ln(2)
        para(
            "Note: some characters in this report (for example Hindi script or emoji) "
            "cannot be drawn in this PDF and appear as '?'. The DOCX export contains the full text.",
            h=4.6, style="I", size=8, color=MUTED,
        )

    return bytes(pdf.output())


def _mood_section(pdf, data, prep, family, section, para, font, need_space, content_w):
    if not data.mood_events:
        return
    section("Mood History")
    cols = [("Date (UTC)", 36), ("Mood", 30), ("Source", 22), ("Stress", 16), ("Energy", 16), ("Sleep", 0)]
    cols[-1] = ("Sleep", content_w - sum(w for _, w in cols[:-1]))

    def header_row():
        pdf.set_fill_color(*BRAND)
        font("B", 8.5, (255, 255, 255))
        pdf.set_x(pdf.l_margin)
        for i, (name, w) in enumerate(cols):
            last = i == len(cols) - 1
            pdf.cell(w, 7, prep(name), fill=True, new_x="LMARGIN" if last else "RIGHT", new_y="NEXT" if last else "TOP")

    def scale(v):
        return f"{v}/5" if v is not None else "-"

    header_row()
    for idx, m in enumerate(data.mood_events):
        note = m.get("note")
        need_space(7 + (10 if note else 0))
        if pdf.get_y() <= 21:  # fresh page -> repeat header
            header_row()
        fill = idx % 2 == 0
        pdf.set_fill_color(*LIGHT_FILL)
        font("", 8.5, INK)
        pdf.set_x(pdf.l_margin)
        cells = [m.get("date") or "-", m.get("mood") or "Neutral", m.get("source") or "",
                 scale(m.get("stress")), scale(m.get("energy")), scale(m.get("sleep"))]
        for i, (value, (_, w)) in enumerate(zip(cells, cols)):
            last = i == len(cols) - 1
            pdf.cell(w, 6.5, prep(value), fill=fill, new_x="LMARGIN" if last else "RIGHT", new_y="NEXT" if last else "TOP")
        if note:
            para(f"Note: {note}", h=4.8, style="I", size=8.5, color=MUTED, indent=4)


def _distribution_section(pdf, data, prep, section, font, content_w):
    if not data.mood_distribution:
        return
    section("Approximate Mood Distribution")
    total = sum(data.mood_distribution.values()) or 1
    bar_max = content_w - 70
    for mood, count in sorted(data.mood_distribution.items(), key=lambda kv: -kv[1]):
        if pdf.get_y() > pdf.h - 28:
            pdf.add_page()
        y = pdf.get_y()
        font("", 9.5, INK)
        pdf.set_xy(pdf.l_margin, y)
        pdf.cell(34, 7, prep(mood), new_x="RIGHT", new_y="TOP")
        pdf.set_fill_color(*BRAND)
        pdf.rect(pdf.l_margin + 36, y + 1.8, max(1.5, bar_max * count / total), 3.4, style="F")
        pdf.set_xy(pdf.l_margin + 36 + bar_max + 3, y)
        pdf.cell(28, 7, prep(f"{count}"), new_x="LMARGIN", new_y="NEXT")


def _conversation_overview(pdf, data, prep, section, font, need_space, content_w):
    if not data.conversations_summary:
        return
    section("Conversations Overview")
    for c in data.conversations_summary:
        need_space(8)
        pdf.set_x(pdf.l_margin)
        font("", 9.5, MUTED)
        pdf.cell(26, 6.5, prep(c["date"]), border="B", new_x="RIGHT", new_y="TOP")
        font("", 9.5, INK)
        pdf.cell(content_w - 26 - 28, 6.5, prep(c["title"][:70]), border="B", new_x="RIGHT", new_y="TOP")
        font("", 9, MUTED)
        pdf.cell(28, 6.5, prep(f"{c['message_count']} messages"), border="B", align="R", new_x="LMARGIN", new_y="NEXT")


def _message_block(pdf, msg, prep, para, font, need_space):
    need_space(22)
    ts = msg.get("ts") or "time not recorded"
    para(f"[{ts}]", h=4.6, style="", size=8, color=MUTED)
    is_user = msg.get("role") == "User"
    para(f"{msg.get('role')}:", h=5.5, style="B", size=9.5, color=INK if is_user else BRAND)
    para(msg.get("content") or "", h=5.2, size=9.5, color=INK, indent=3)
    pdf.ln(2.5)


def _transcript_section(pdf, title, transcripts, empty_text, prep, section, para, font, need_space, content_w, grouped):
    section(title)
    if not transcripts:
        para(empty_text, style="I", color=MUTED)
        return
    for t in transcripts:
        need_space(30)
        pdf.set_fill_color(*LIGHT_FILL)
        font("B", 10, INK)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_w, 7, prep(t["title"]), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
        for msg in t["messages"]:
            _message_block(pdf, msg, prep, para, font, need_space)
        pdf.ln(2)


def _chatbot_section(pdf, data, prep, section, para, font, need_space, content_w):
    section("Chatbot History")
    if data.chatbot_note:
        para(data.chatbot_note, h=4.8, style="I", size=8.5, color=MUTED)
        pdf.ln(2)
    if not data.chatbot_messages:
        para("No chatbot messages were recorded in this session.", style="I", color=MUTED)
        return
    for msg in data.chatbot_messages:
        _message_block(pdf, msg, prep, para, font, need_space)
