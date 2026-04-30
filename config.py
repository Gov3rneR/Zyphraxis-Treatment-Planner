"""
config.py - Central configuration for Zyphraxis.

Tune system behaviour here without touching core brain logic.
All values can be overridden via environment variables (see .env.example).
"""
import os

# ---------------------------------------------------------------------------
# Optimisation weights
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict = {
    "time_w":         float(os.getenv("WEIGHT_TIME",         "5.0")),
    "risk_w":         float(os.getenv("WEIGHT_RISK",         "3.0")),
    "cost_w":         float(os.getenv("WEIGHT_COST",         "0.01")),
    "hla_mismatch_w": float(os.getenv("WEIGHT_HLA_MISMATCH", "10.0")),
}

# ---------------------------------------------------------------------------
# Clinical thresholds
# ---------------------------------------------------------------------------
THRESHOLDS: dict = {
    "max_risk":            float(os.getenv("THRESHOLD_MAX_RISK",      "0.30")),
    "min_tumor_escape_h":  float(os.getenv("THRESHOLD_MIN_ESCAPE_H",  "24")),
    "no_path_risk_cutoff": float(os.getenv("THRESHOLD_NO_PATH_RISK",  "0.50")),
}

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
API_CONFIG: dict = {
    "title":       "Zyphraxis Treatment Planning API",
    "version":     "1.0.0",
    "description": "AI-driven personalised treatment sequencing for oncology. Research use only.",
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_CONFIG: dict = {
    "level":        os.getenv("LOG_LEVEL",        "INFO"),
    "file":         os.getenv("LOG_FILE",         "logs/zyphraxis.log"),
    "max_bytes":    int(os.getenv("LOG_MAX_BYTES",    "10485760")),  # 10 MB
    "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
}
