import os
import sys

# Ensure UTF-8 console output for cross-platform robustness
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from app.api.routes import router
from app.config import settings
from app.services.retention_service import retention_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print(f"=== {settings.owner_display_name} AI Call Assistant Backend Starting ===")
    print(f"Environment: {settings.app_env}")
    print(f"Recording Retention: {settings.recording_retention_days} days")
    print(f"Data directory: {os.path.abspath(settings.local_data_dir)}")
    print(f"Recordings directory: {os.path.abspath(settings.local_recordings_dir)}")

    # Initial retention sweep
    try:
        await retention_service.purge_expired_recordings()
    except Exception as e:
        print(f"[Lifespan] Initial retention purge notice: {e}")

    yield

    # Shutdown actions
    print(f"=== {settings.owner_display_name} AI Call Assistant Backend Shut Down ===")


app = FastAPI(
    title="Ritesh AI Call Assistant",
    version="1.0.0",
    description="Real-Time AI Receptionist with Telugu/Hindi/English conversation, Exotel live audio streaming, ElevenLabs cloned voice, and consent-gated recording.",
    lifespan=lifespan
)

# Enable CORS for local Android development and Web testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount Mobile Companion Web App & PWA
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/app/")


@app.get("/download")
async def download_apk():
    """Direct APK download endpoint for mobile devices."""
    apk_path = os.path.join(static_dir, "Ritesh_AI_Call_Assistant.apk")
    if not os.path.exists(apk_path):
        return {"error": "APK not found. Please build the APK first."}
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="Ritesh_AI_Call_Assistant.apk"
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ritesh-ai-call-assistant",
        "version": "1.0.0",
        "telephony_stream_endpoint": "/api/telephony/media",
        "dashboard_endpoint": "/api/dashboard/stats"
    }
