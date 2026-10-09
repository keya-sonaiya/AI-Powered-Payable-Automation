"""
Tesseract wrapper (pytesseract + pdf2image).

NOTE (Phase 2 concern): This is a blocking/sync call. Phase 2's ingest
router must call it via `await asyncio.to_thread(...)`, never directly
inside an `async def`.
"""
from pdf2image import convert_from_path
import pytesseract


def extract_text_from_pdf(pdf_path: str) -> str:
    """Rasterize a PDF's pages and OCR each one, returning concatenated text."""
    pages = convert_from_path(pdf_path)
    return "\n".join(pytesseract.image_to_string(page) for page in pages)


def extract_text_from_image(image_path: str) -> str:
    """OCR a single image file directly."""
    return pytesseract.image_to_string(image_path)


def extract_text(file_path: str) -> str:
    """Dispatch by extension. Entry point Phase 2's ingest router should call."""
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    return extract_text_from_image(file_path)
