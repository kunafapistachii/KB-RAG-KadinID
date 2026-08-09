import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "adart_kb"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
EMBEDDING_BATCH_SIZE = 100  # inputs per API call, well under 2048 limit

MAX_CHUNK_CHARS = 1500

# OCR (optional). Only needed when --ocr is used. Override via env if
# Tesseract or the language data live somewhere non-default.
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA_DIR = os.environ.get("TESSDATA_DIR", "")  # e.g. a user-owned dir holding ind.traineddata
OCR_LANG = os.environ.get("OCR_LANG", "ind")
