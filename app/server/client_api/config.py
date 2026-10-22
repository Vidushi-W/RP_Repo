import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
DATA = ROOT / "runtime"
ADMIN = (ROOT / os.getenv("ADMIN_PROJECT_DIR", "../../slsl-research")).resolve()
MONGO_URI = os.getenv("MONGODB_URI", "").strip()
MONGO_DATABASE = os.getenv("MONGODB_DATABASE", "slsl_connect")
PRODUCTION = os.getenv("APP_ENV", "development") == "production"
if PRODUCTION and not MONGO_URI:
    raise RuntimeError(
        "Production requires MONGODB_URI; development fallback is disabled."
    )
