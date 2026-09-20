import io
from pathlib import Path

import mammoth
from pypdf import PdfReader


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return data.decode("utf-8", errors="replace")
    if ext == ".docx":
        result = mammoth.extract_raw_text(io.BytesIO(data))
        return result.value or ""
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n\n".join(parts).strip()
    raise ValueError(f"Unsupported file type: {ext}")
