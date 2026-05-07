from __future__ import annotations

import io
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Literal

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    from PIL import Image
    import pytesseract
except ImportError:  # pragma: no cover
    Image = None
    pytesseract = None


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _configure_tesseract() -> None:
    if pytesseract is None:
        return

    repo_tesseract = Path(__file__).resolve().parents[3] / "local-runtime" / "Tesseract-OCR" / "tesseract.exe"
    home_tesseract = Path.home() / "parakh-runtime" / "Tesseract-OCR" / "tesseract.exe"
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        str(repo_tesseract),
        str(home_tesseract),
        r"C:\tmp\parakh-runtime\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            tessdata_dir = Path(candidate).parent / "tessdata"
            if tessdata_dir.exists() and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
            return

    discovered = shutil.which("tesseract")
    if discovered:
        pytesseract.pytesseract.tesseract_cmd = discovered


def _ocr_pil_image(image) -> str:
    if pytesseract is None or Image is None:
        return ""
    _configure_tesseract()
    prepared = image.convert("L")
    return pytesseract.image_to_string(prepared)


def _extract_pdf_text(path: Path) -> tuple[str, Literal["digital_text", "ocr", "fallback"], float]:
    if fitz is not None:
        with fitz.open(path) as document:
            text = " ".join(page.get_text("text") for page in document)
        if _normalise(text):
            return _normalise(text), "digital_text", 0.92
    if pdfplumber is not None:
        with pdfplumber.open(path) as document:
            text = " ".join(page.extract_text() or "" for page in document.pages)
        if _normalise(text):
            return _normalise(text), "digital_text", 0.9
    if pytesseract is not None and fitz is not None and Image is not None:
        chunks: list[str] = []
        with fitz.open(path) as document:
            for page in document[:5]:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                chunks.append(_ocr_pil_image(image))
        text = _normalise(" ".join(chunks))
        if text:
            return text, "ocr", 0.72
    return "", "fallback", 0.25


def _save_temp_image(image) -> Path:
    temp_path = Path(tempfile.gettempdir()) / "parakh_ocr_page.png"
    image.save(temp_path)
    return temp_path


def extract_text(path_str: str) -> tuple[str, Literal["digital_text", "ocr", "html", "fallback"], float]:
    path = Path(path_str)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in {".png", ".jpg", ".jpeg"} and pytesseract is not None and Image is not None:
        return _normalise(_ocr_pil_image(Image.open(path))), "ocr", 0.68
    if suffix in {".html", ".htm"}:
        text = _normalise(re.sub(r"<[^>]+>", " ", path.read_text(encoding="utf-8", errors="ignore")))
        return text, "html", 0.95 if text else 0.3
    if suffix in {".txt", ".csv"}:
        text = _normalise(path.read_text(encoding="utf-8", errors="ignore"))
        return text, "digital_text", 0.96 if text else 0.3
    return "", "fallback", 0.2
