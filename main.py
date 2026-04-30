"""
main.py - FastAPI application entry point for Zyphraxis.

Run with:
    uvicorn main:app --reload                              # development
    uvicorn main:app --host 0.0.0.0 --port 8000           # production / Docker
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_CONFIG
from api import router
from med_brain_v6 import MedBrainV6, SAFWeights
from logger import zyphraxis_log


# ---------------------------------------------------------------------------
# Lifespan — initialise engine once, share across all requests
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    zyphraxis_log.logger.info("STARTUP  | Initialising Zyphraxis engine …")
    app.state.engine  = MedBrainV6()
    app.state.weights = SAFWeights()
    zyphraxis_log.logger.info("STARTUP  | Engine ready.")
    yield
    zyphraxis_log.logger.info("SHUTDOWN | Zyphraxis shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title       = API_CONFIG["title"],
    version     = API_CONFIG["version"],
    description = API_CONFIG["description"],
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins    = API_CONFIG["cors_origins"],
    allow_credentials= True,
    allow_methods    = ["*"],
    allow_headers    = ["*"],
)

app.include_router(router)


# ---------------------------------------------------------------------------
# Development convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
