# Ritesh AI Call Assistant

Automated AI Receptionist with Live Audio Streaming, Cloned Voice Synthesis, Multilingual Conversation (Telugu, Hindi, English), Consent-Gated Recording, and Android Push Notifications.

---

## Architecture Overview

```
Caller (Any Phone)
       │
       ▼
Vi SIM (Conditional No-Answer Forwarding: *61*<ExoPhone>#)
       │
       ▼
Exotel Virtual Number (ExoPhone)
       │
       ▼
Exotel Inbound Voicebot (AgentStream Bidirectional WebSocket WSS)
       │
       ▼
FastAPI Real-Time Voice Gateway (`/api/telephony/media`)
       │
       ├─► Whisper Multilingual STT (Auto-detects Telugu, Hindi, English)
       ├─► OpenAI GPT-4o Conversation Engine (RMVS Web Services Knowledge Base)
       ├─► ElevenLabs Cloned Voice Streaming (Mono PCM16 8kHz Telephony Standard)
       ├─► Consent-Gated Audio Recorder (30-day Retention Cleanup)
       ├─► Database Persistence (Supabase Cloud + Local SQLite Fallback)
       └─► Android Notifications (Firebase Cloud Messaging + Local Dashboard API)
```

---

## Approved Project Configuration

| Feature | Configuration |
|---|---|
| **Incoming Callers** | All callers reaching the forwarded number |
| **Call Handling** | All unanswered calls |
| **Personal Knowledge** | Enabled (`Ritesh`, software/AI development, scheduling rules) |
| **Professional Knowledge** | Enabled (`RMVS Web Services`, website development, e-commerce, web apps, pricing safeguard) |
| **Language Detection** | Automatic (Telugu, Hindi, English seamless switching) |
| **Voice** | Authorized cloned voice via ElevenLabs |
| **Audio Recording** | **Consent-Gated** (Notice given upfront; audio saved ONLY if affirmative consent is granted) |
| **Retention Policy** | Configurable 30-day retention with automated cleanup job |
| **Transcript & Summary** | Turn-by-turn dialogue + structured AI summary (Urgency, Reason, Callback info) |
| **Notifications** | Automatic Android alerts (Firebase Cloud Messaging) |

---

## Implemented Milestones

1. **Exotel Live Audio Streaming**:
   - WebSocket endpoint at `/api/telephony/media`.
   - Supports Exotel AgentStream bidirectional streaming protocol (`connected`, `start`, `media`, `mark`, `stop`).
   - Downsamples & transcodes audio to **telephony mono PCM16 at 8 kHz**.

2. **OpenAI Speech Recognition & Conversation Engine**:
   - `STTProvider` utilizing OpenAI Whisper API with auto language detection.
   - `ConversationProvider` integrating GPT-4o with system prompt, approved RMVS Web Services knowledge base, and conversational rules.
   - Explicit safeguard: Identifies as Ritesh's AI call assistant, never commits to unconfirmed pricing or availability.

3. **ElevenLabs Cloned Voice Responses**:
   - `VoiceProvider` utilizing ElevenLabs Streaming API with verified voice ID.
   - Low-latency streaming in chunks converted directly to telephony mono PCM16 8kHz frames.
   - Built-in simulation fallback for offline testing.

4. **Consent-Gated Recording & Transcription**:
   - `ConsentGatedAudioBuffer` holds audio frames in memory while consent is requested.
   - Affirmative consent ("yes", "sure", "సరేనండి", "हाँ") -> saves WAV recording with 30-day retention.
   - Declined consent ("no", "don't record", "వద్దండి", "नहीं") -> immediately purges audio buffer.
   - Supabase Storage upload with automatic local SQLite/file storage fallback.
   - Automated 30-day retention cleanup service (`/api/recording/retention/purge`).

5. **Automatic Android Notifications**:
   - `NotificationService` formats instant notifications with caller details, urgency badge (`NORMAL`, `HIGH`, `EMERGENCY`), and summary preview.
   - Dispatches push notifications via Firebase Cloud Messaging (FCM).

---

## How to Run

### 1. Start the Backend Server
Double-click `start_backend.bat` or run in PowerShell:
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base URL: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Android Dashboard Stats: `http://localhost:8000/api/dashboard/stats`

### 2. Run the Call Simulator (Test Pipeline)
Double-click `test_pipeline.bat` or run:
```powershell
cd backend
.\.venv\Scripts\python.exe simulate_call.py
```
You can test:
- **Scenario 1**: English call - RMVS website inquiry (Consent GRANTED -> Audio saved).
- **Scenario 2**: Telugu call - College B.Tech project inquiry (Consent GRANTED).
- **Scenario 3**: Hindi call - E-commerce inquiry (**Consent DECLINED -> Zero audio saved**).
- **Scenario 4**: Emergency call - Server outage alert (Triggers `EMERGENCY` priority push notification).

---

## Configuration (`backend/.env`)

Edit `backend/.env` with your API credentials when ready for live calling:

```ini
APP_ENV=development
PUBLIC_BASE_URL=http://localhost:8000
INTERNAL_API_KEY=ritesh-call-ai-dev-secret-2026

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_TEXT_MODEL=gpt-4o
OPENAI_STT_MODEL=whisper-1

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Supabase (Optional for dev - uses local SQLite if left empty)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_RECORDINGS_BUCKET=call-recordings

# Exotel
EXOTEL_ACCOUNT_SID=...
EXOTEL_API_KEY=...
EXOTEL_API_TOKEN=...
EXOTEL_EXOPHONE=...

# Android Push Notifications (Firebase)
FCM_SERVER_KEY=...
RITESH_ANDROID_FCM_TOKEN=...
```

---

## Safety Precaution Before Live Deployment

> **Important**: Do NOT forward your personal Vi SIM number (`*61*...#`) until you have verified the pipeline with a dedicated test phone number and added your production Exotel credentials.
