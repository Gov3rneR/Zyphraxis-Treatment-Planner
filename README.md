# 🧬 Zyphraxis Treatment Planner — Developer Handover

> **Research use only. Not a licensed medical device. Not medical advice.**  
> See `TERMS_OF_USE.md` and `PRIVACY_POLICY.md` before deploying.

---

## What This Is

Zyphraxis is a deterministic, multi-objective oncology treatment-plan optimiser.
Given a tumour-escape time window and patient constraints, it ranks candidate single
and combination treatment plans by time, risk, cost, HLA mismatch, and effectiveness —
then returns the best feasible plan with a full explanation.

---

## Project Structure

```
Zyphraxis/
├── med_brain_v6.py      # Core engine (fixed, optimised)
├── main.py              # FastAPI app entry point
├── api.py               # Route definitions + request/response schemas
├── auth.py              # API-key authentication
├── config.py            # Central config (env-overridable)
├── logger.py            # Structured rotating logger
├── ui.py                # Streamlit browser UI
├── scenarios.json       # Pre-built demo cases
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── Dockerfile           # Container image
├── docker-compose.yml   # API + UI services
├── TERMS_OF_USE.md
├── PRIVACY_POLICY.md
├── tests/
│   ├── __init__.py
│   └── test_engine.py   # Full unit test suite (pytest)
├── logs/                # Rotating log files (auto-created)
├── data/                # memory.json, stats.json (auto-created)
└── reports/             # For exported plan JSONs
```

---

## Quick Start (Local, No Docker)

### 1. Prerequisites
- Python 3.11+
- pip

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env — set ZYPHRAXIS_API_KEY at minimum
```

### 4. Start the API
```bash
uvicorn main:app --reload
# API runs at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 5. Start the UI (separate terminal)
```bash
streamlit run ui.py
# UI runs at http://localhost:8501
```

### 6. Run tests
```bash
pytest tests/ -v
```

---

## Docker Deployment

```bash
cp .env.example .env      # configure your key
docker-compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

---

## API Reference

### Authentication
All planning endpoints require an `X-API-Key` header.

```
X-API-Key: your-key-here
```

Set the key in `.env` as `ZYPHRAXIS_API_KEY`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/scenarios` | List demo scenarios |
| POST | `/generate_plan` | Generate optimal treatment plan |
| POST | `/learn` | Submit observed outcome for memory |

### POST /generate_plan — Request Body

```json
{
  "tumor_escape_h": 960,
  "max_risk": 0.25,
  "human_use": true,
  "mode": "balanced",
  "patient_id": "optional-ref"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `tumor_escape_h` | float > 0 | ✅ | Hours until tumour escape |
| `max_risk` | float 0–1 | | Max acceptable risk (default 0.30) |
| `human_use` | bool | | Include human-trial treatments (default true) |
| `mode` | string | | `aggressive` / `balanced` / `conservative` |
| `patient_id` | string | | Opaque ID for logging/traceability only |

### POST /generate_plan — Response

```json
{
  "status": "success",
  "plan": [
    {
      "step": 1,
      "treatment_id": "IMMUNO_2",
      "treatment_name": "Immunotherapy Booster",
      "duration_h": 168,
      "modality": "immuno"
    }
  ],
  "metrics": {
    "total_time_h": 168,
    "risk_score": 0.06,
    "estimated_cost": 28000,
    "hla_mismatches": 2,
    "confidence": 0.85
  },
  "explanation": "Mode 'balanced': Selected [Immunotherapy Booster] | ...",
  "timestamp": "2024-01-01T12:00:00+00:00",
  "alternatives": 3
}
```

`status` is `"success"`, `"NO_PATH"`, or `"INVALID_INPUT"`.

---

## Optimisation Modes

| Mode | Behaviour |
|---|---|
| `conservative` | 2× risk penalty. Prefers lower-risk plans even if slower. |
| `balanced` | Default weights. Balances time, risk, cost, effectiveness equally. |
| `aggressive` | 1.5× time weight, 0.6× risk weight. Prefers faster plans. |

Legacy mode names (`apollo` → conservative, `manhattan` → aggressive) are
accepted by the `run_engine()` wrapper for backwards compatibility.

---

## Configuration Reference (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ZYPHRAXIS_API_KEY` | `zyphraxis-demo-key` | API authentication key |
| `THRESHOLD_MAX_RISK` | `0.30` | Default max risk threshold |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `LOG_FILE` | `logs/zyphraxis.log` | Log file path |
| `LOG_MAX_BYTES` | `10485760` | Log rotation size (10 MB) |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated log files to keep |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `API_URL` | `http://localhost:8000` | Used by the Streamlit UI |

---

## Logging

Every request and response is logged to `logs/zyphraxis.log` in structured format:

```
2024-01-01 12:00:00 | INFO     | REQUEST  | id=P001 | {"tumor_escape_h": 960, ...}
2024-01-01 12:00:00 | INFO     | RESPONSE | id=P001 | latency=4.2ms | status=success | ...
2024-01-01 12:00:00 | WARNING  | NO_PATH  | reason=... | request=...
```

Logs rotate at 10 MB with 5 backups. Configure via `.env`.

---

## Known Limitations

- Treatment catalogue is hardcoded in `med_brain_v6.py`. For production, replace with a database-backed catalogue.
- Authentication is static API-key only. For multi-user production use, replace `auth.py` with OAuth2 / JWT.
- Rate limiting in `auth.py` is a stub. Implement with `slowapi` + Redis before exposing publicly.
- The engine is deterministic and non-ML. Outcomes logged via `/learn` are stored but not yet fed back into scoring weights — this is the intended next development milestone.

---

## Regulatory Notice

Zyphraxis is **not** a medical device. Before clinical deployment, the deploying organisation must obtain all applicable regulatory approvals for their jurisdiction (e.g. FDA, CE, CDSCO). See `TERMS_OF_USE.md` for full terms.
