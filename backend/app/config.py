import os
from pathlib import Path

ENGINE_DIR = Path(os.getenv("ENGINE_DIR", Path(__file__).resolve().parents[2] / "engine"))
DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp/card-printer-data"))
PYTHON = os.getenv("ENGINE_PYTHON", "python")

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
STEP_TIMEOUT_SECONDS = int(os.getenv("STEP_TIMEOUT_SECONDS", "900"))
MAX_DECK_LINES = int(os.getenv("MAX_DECK_LINES", "500"))
MAX_DECK_BYTES = 200_000
MAX_BACK_BYTES = 10 * 1024 * 1024
# Se definido, toda chamada /api precisa do header X-Access-Token com este valor.
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
