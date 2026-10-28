import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
TOP_K = int(os.getenv("TOP_K", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPOSITORIES_DIR = DATA_DIR / "repositories"
INDEX_PATH = DATA_DIR / "faiss.index"
RECORDS_PATH = DATA_DIR / "records.json"
DOCUMENTS_PATH = DATA_DIR / "documents.json"

for path in (DATA_DIR, UPLOAD_DIR, REPOSITORIES_DIR):
    path.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Mentor login (LOCAL PROTOTYPE ONLY).
# These credentials are deliberately hardcoded for a small local prototype.
# They are NOT secure production authentication. Change them (or set the
# environment variables below in backend/.env) before any real deployment.
# ---------------------------------------------------------------------------
MENTOR_USER_ID = os.getenv("MENTOR_USER_ID", "ravi.tambade@transflower.in")
MENTOR_PASSWORD = os.getenv("MENTOR_PASSWORD", "password")
# How long an in-memory mentor session token stays valid (hours).
MENTOR_SESSION_HOURS = float(os.getenv("MENTOR_SESSION_HOURS", "8"))

# Extra comma-separated CORS origins, e.g. http://192.168.1.10:5173
EXTRA_CORS_ORIGINS = [o.strip() for o in os.getenv("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()]

JAVA_API_BASE_URL = os.getenv("JAVA_API_BASE_URL","http://localhost:5201",).rstrip("/")

