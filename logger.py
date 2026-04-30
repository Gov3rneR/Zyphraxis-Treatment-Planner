"""
logger.py - Structured logging for Zyphraxis.

Tracks every run: inputs, outputs, decisions, errors.
Required for debugging, explainability, and enterprise audit trails.

Usage::

    from logger import zyphraxis_log
    zyphraxis_log.log_request(request_dict, patient_id)
"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

from config import LOG_CONFIG

# Ensure the log directory exists before creating handlers
Path(LOG_CONFIG["file"]).parent.mkdir(parents=True, exist_ok=True)

_FMT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE = "%Y-%m-%d %H:%M:%S"


class ZyphraxisLogger:
    """Singleton logger with structured log messages."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("zyphraxis")
        self.logger.setLevel(LOG_CONFIG["level"])

        if not self.logger.handlers:
            formatter = logging.Formatter(_FMT, datefmt=_DATE)

            # Rotating file handler
            fh = RotatingFileHandler(
                LOG_CONFIG["file"],
                maxBytes=LOG_CONFIG["max_bytes"],
                backupCount=LOG_CONFIG["backup_count"],
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

            # Stdout (Docker / cloud log collectors)
            sh = logging.StreamHandler()
            sh.setFormatter(formatter)
            self.logger.addHandler(sh)

    # ------------------------------------------------------------------ #

    def log_request(self, request_data: dict, request_id: Optional[str] = None) -> None:
        self.logger.info("REQUEST  | id=%s | %s", request_id, json.dumps(request_data))

    def log_response(
        self,
        response_data: dict,
        request_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        self.logger.info(
            "RESPONSE | id=%s | latency=%.1fms | status=%s | metrics=%s",
            request_id,
            latency_ms or 0,
            response_data.get("status"),
            json.dumps(response_data.get("metrics") or {}),
        )

    def log_decision(self, step: str, details: dict) -> None:
        self.logger.info("DECISION | step=%s | %s", step, json.dumps(details))

    def log_error(self, error: Exception, context: Optional[dict] = None) -> None:
        self.logger.error(
            "ERROR    | %s: %s | context=%s",
            type(error).__name__,
            str(error),
            json.dumps(context or {}),
        )

    def log_no_path(self, reason: str, request_data: dict) -> None:
        self.logger.warning(
            "NO_PATH  | reason=%s | request=%s", reason, json.dumps(request_data)
        )

    def log_learn(self, entry: dict) -> None:
        self.logger.info("LEARN    | %s", json.dumps(entry))


# Singleton — import this everywhere
zyphraxis_log = ZyphraxisLogger()
