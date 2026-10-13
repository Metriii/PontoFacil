from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

FOTOS_DIR = BASE_DIR / "fotos"
JSON_DIR = BASE_DIR / "json"
SAIDA_DIR = BASE_DIR / "saida"
TEMP_DIR = BASE_DIR / "temporarios"

for d in (FOTOS_DIR, JSON_DIR, SAIDA_DIR, TEMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = 15
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_FILES_PER_BATCH = 50

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".jfif", ".png", ".webp"}
ALLOWED_ZIP_EXTS = {".zip"}
ALLOWED_PDF_EXTS = {".pdf"}
ALLOWED_PDF_EXTS = {".pdf"}
ALLOWED_PDF_EXTS = {".pdf"}

API_PORT = 8000
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
