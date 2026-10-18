import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_env_path = os.path.join(_ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip("\"'")
                if _k and _k not in os.environ:
                    os.environ[_k] = _v

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mindful_metrics.db")
ENV = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    if ENV in ("production", "prod"):
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing in production environment!")
    import secrets as _secrets
    JWT_SECRET = _secrets.token_hex(32)
elif len(JWT_SECRET.encode("utf-8")) < 32 and ENV in ("production", "prod"):
    raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET must be at least 32 bytes for secure HMAC-SHA256 in production!")

JWT_ALG = "HS256"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://mindful-metrics-alpha.vercel.app,https://*.trycloudflare.com",
)
ALLOWED_ORIGINS = [origin.strip() for origin in _ALLOWED_ORIGINS.split(",") if origin.strip()]
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(_ROOT, "models"))
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(MODEL_DIR, "burnout_random_forest.joblib"))
LOW_MAX = int(os.getenv("RISK_LOW_MAX", "39"))
MOD_MAX = int(os.getenv("RISK_MOD_MAX", "69"))
DATASET_VERSION = "synthetic_v1"
MODEL_VERSION = "burnout_rf_v1.0"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()
