import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

class Settings(BaseSettings):
    app_env: str = "development"
    public_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    internal_api_key: str = "ritesh-call-ai-dev-secret-2026"

    # OpenAI Speech & Language Models
    openai_api_key: str = ""
    openai_realtime_model: str = "gpt-4o-realtime-preview"
    openai_text_model: str = "gpt-4o"
    openai_stt_model: str = "whisper-1"

    # ElevenLabs Cloned Voice Settings
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    # Neon PostgreSQL Cloud Database
    neon_database_url: str = ""
    database_url: str = ""

    # Supabase (Cloud Database & Storage)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_recordings_bucket: str = "call-recordings"

    # Local Storage Fallback & Retention
    recording_retention_days: int = 30
    local_data_dir: str = "./data"
    local_recordings_dir: str = "./data/recordings"

    # Exotel Telephony
    exotel_account_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_exophone: str = ""
    exotel_webhook_secret: str = ""

    # Receptionist Behaviors & Consent Policy
    owner_display_name: str = "Ritesh"
    owner_phone_number: str = "9705162303"
    default_greeting_language: str = "auto"
    call_recording_enabled: bool = True
    recording_requires_affirmative_consent: bool = True

    # Android Push Notifications (Firebase)
    fcm_server_key: str = ""
    ritesh_android_fcm_token: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH if os.path.exists(ENV_PATH) else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure local data and recording directories exist
os.makedirs(settings.local_data_dir, exist_ok=True)
os.makedirs(settings.local_recordings_dir, exist_ok=True)
