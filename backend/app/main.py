from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.routers import agent, agent_v1, advisor, investment_platform, account_aggregator, community, wellness_program, webhook, export
from app.auth.router import router as auth_router
from app.core.background_tasks import start_background_sync
from app.core.config import get_settings
from app.guardrails.financial_output import FinancialOutputError
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start one sync worker per application process and stop it cleanly."""
    worker = start_background_sync() if get_settings().enable_background_sync else None
    try:
        yield
    finally:
        if worker:
            sync_thread, stop_event = worker
            stop_event.set()
            sync_thread.join(timeout=5)


app = FastAPI(
    title="Financial Freedom Copilot API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(FinancialOutputError)
async def financial_output_error_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={"detail": "Financial result failed traceability validation"},
    )

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api/auth")
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(agent_v1.router, prefix="/api/v1/agent", tags=["agent-v1"])
settings = get_settings()

if settings.enable_advisor_access:
    app.include_router(advisor.router, prefix="/api/advisor", tags=["advisor"])
if settings.enable_financial_integrations:
    app.include_router(investment_platform.router, prefix="/api/investment-platform", tags=["investment_platform"])
    app.include_router(account_aggregator.router, prefix="/api/account-aggregator", tags=["account_aggregator"])
if settings.enable_community_benchmarks:
    app.include_router(community.router, prefix="/api/community", tags=["community"])
if settings.enable_wellness_programs:
    app.include_router(wellness_program.router, prefix="/api/wellness-program", tags=["wellness_program"])
if settings.enable_external_webhooks:
    app.include_router(webhook.router, prefix="/api/webhook", tags=["webhook"])
if settings.enable_data_exports:
    app.include_router(export.router, prefix="/api/export", tags=["export"])

# Health endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Mount static files for frontend
# Try the production build directory first
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
else:
    # Fallback for development
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
    if os.path.exists(frontend_path):
        app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    else:
        # Final fallback
        @app.get("/")
        async def root():
            return {"message": "Financial Freedom Copilot API is running. Frontend not found."}
