from __future__ import annotations

import io
import re
from html import escape, unescape

from app.services.text_utils import html_to_plain


def export_txt(html: str) -> bytes:
    return html_to_plain(html).encode("utf-8")


def export_md(html: str, title: str = "") -> bytes:
    plain = html_to_plain(html)
    lines = [f"# {title}".strip(), ""] if title.strip() else []
    for block in re.split(r"\n{2,}", plain.strip()):
        if block.strip():
            lines.append(block.strip())
            lines.append("")
    return "\n".join(lines).encode("utf-8")


def export_html(html: str, title: str = "") -> bytes:
    safe_title = escape(unescape(title) or "Document")
    doc = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>{safe_title}</title></head>
<body>{html}</body></html>"""
    return doc.encode("utf-8")


def export_docx(html: str, title: str = "") -> bytes:
    from docx import Document

    doc = Document()
    if title.strip():
        doc.add_heading(title.strip(), level=0)
    plain = html_to_plain(html)
    for para in plain.split("\n"):
        text = para.strip()
        if text:
            doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_pdf(html: str, title: str = "") -> bytes:
    from xhtml2pdf import pisa

    safe_title = escape(unescape(title) or "Document")
    plain = html_to_plain(html)
    body_parts = "".join(f"<p>{escape(line.strip())}</p>" for line in plain.split("\n") if line.strip())
    if not body_parts:
        body_parts = "<p></p>"
    pdf_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>{safe_title}</title>
<style>@page {{ margin: 2cm; }} body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12pt; }}</style>
</head><body>{body_parts}</body></html>"""
    buf = io.BytesIO()
    status = pisa.CreatePDF(pdf_html, dest=buf, encoding="utf-8")
    if status.err:
        raise RuntimeError("PDF generation failed (try DOCX or HTML for Cyrillic text)")
    data = buf.getvalue()
    if not data:
        raise RuntimeError("PDF export produced empty file")
    return data
