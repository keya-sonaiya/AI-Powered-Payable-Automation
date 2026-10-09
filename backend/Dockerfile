FROM python:3.11-slim

# Tesseract + poppler are needed by pytesseract / pdf2image (Phase 2 wiring),
# installed now so the image doesn't need rebuilding later for OCR support.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# main.py is a Phase 2 concern (TODO placeholder in Phase 1). This CMD is the
# target entrypoint once Phase 2 implements it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
