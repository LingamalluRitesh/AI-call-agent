import json
import base64
import asyncio
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.config import settings
from app.services.recording_policy import recording_decision, ConsentGatedAudioBuffer, parse_verbal_consent
from app.services.knowledge_base import load_knowledge_base
from app.services.ai_provider import conversation_provider, stt_provider
from app.services.voice_provider import voice_provider
from app.services.database import db_service
from app.services.notification_service import notification_service
from app.services.retention_service import retention_service
from app.services.exotel_client import exotel_client
from app.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_user
)

router = APIRouter(prefix="/api")


# --- Auth Models ---
class UserRegisterRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20, description="User's mobile number, e.g. 9705162303")
    password: str = Field(min_length=4, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    company_name: Optional[str] = ""

class UserLoginRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=4, max_length=128)

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    company_name: Optional[str] = None
    greeting_language: Optional[str] = None
    custom_greeting: Optional[str] = None
    knowledge_base_json: Optional[str] = None

class ConsentUpdate(BaseModel):
    call_id: str = Field(min_length=1, max_length=128)
    consent: str = Field(pattern="^(yes|no|unknown)$")

class SimulateCallRequest(BaseModel):
    caller_number: str = "+919999999999"
    caller_utterances: List[str] = [
        "Yes, I agree to the recording.",
        "Hello, I wanted to inquire about a business website for my store with RMVS Web Services.",
        "My name is Amit. Please have Ritesh call me back this evening."
    ]
    language: str = "en"
    owner_name: Optional[str] = None
    company_name: Optional[str] = None


def require_internal_key(value: str | None):
    if settings.internal_api_key and value != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# --- Multi-User Company Authentication Endpoints ---

@router.post("/auth/register")
async def register(req: UserRegisterRequest):
    """Registers a new company user account so each user can configure their own number and AI."""
    existing = await db_service.get_user_by_phone(req.phone_number)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this phone number already exists.")

    pwd_hash = hash_password(req.password)
    user = await db_service.create_user(
        phone_number=req.phone_number,
        password_hash=pwd_hash,
        display_name=req.display_name,
        company_name=req.company_name or ""
    )
    token = create_access_token(
        user_id=user["id"],
        phone_number=user["phone_number"],
        display_name=user["display_name"]
    )
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/auth/login")
async def login(req: UserLoginRequest):
    """Authenticates a user and returns a session token."""
    user = await db_service.get_user_by_phone(req.phone_number)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone number or password.")

    if not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid phone number or password.")

    token = create_access_token(
        user_id=user["id"],
        phone_number=user["phone_number"],
        display_name=user["display_name"]
    )
    user_sanitized = {k: v for k, v in user.items() if k != "password_hash"}
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user_sanitized
    }


@router.get("/auth/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Fetches the authenticated user profile and AI preferences."""
    user = await db_service.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.put("/auth/profile")
async def update_profile(body: UpdateProfileRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Updates user display name, company name, custom greeting, and knowledge base."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated_user = await db_service.update_user(current_user["user_id"], **updates)
    return {"status": "success", "user": updated_user}


# --- Call & Dashboard Endpoints (Multi-Tenant Aware) ---

@router.get("/dashboard/stats")
async def dashboard_stats(current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """Aggregates for the Android dashboard, filtered by authenticated user if logged in."""
    user_id = current_user.get("user_id") if current_user else None
    return await db_service.get_stats(user_id=user_id)


@router.get("/calls")
async def list_calls(limit: int = 50, current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """List recent calls with metadata and summaries, filtered by user if authenticated."""
    user_id = current_user.get("user_id") if current_user else None
    calls = await db_service.list_calls(limit=limit, user_id=user_id)
    return {"items": calls, "count": len(calls)}


@router.get("/calls/{call_id}")
async def get_call_detail(call_id: str):
    """Retrieve full details of a specific call including transcripts."""
    call = await db_service.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    return call


@router.get("/recordings/{filename}")
async def get_recording_audio(filename: str):
    """Streams the recorded WAV audio file for playback on mobile/web."""
    import os
    clean_name = os.path.basename(filename)
    path = os.path.join(settings.local_recordings_dir, clean_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Recording audio file not found or has been purged by retention policy.")
    return FileResponse(path, media_type="audio/wav", filename=clean_name)


@router.get("/knowledge-base")
async def get_knowledge_base(x_internal_api_key: str | None = Header(default=None)):
    require_internal_key(x_internal_api_key)
    return load_knowledge_base()


@router.post("/recording/consent")
async def set_recording_consent(body: ConsentUpdate, x_internal_api_key: str | None = Header(default=None)):
    require_internal_key(x_internal_api_key)
    decision = recording_decision(
        feature_enabled=settings.call_recording_enabled,
        consent=body.consent,
        affirmative_required=settings.recording_requires_affirmative_consent,
    )
    await db_service.record_consent(
        call_id=body.call_id,
        consent=body.consent,
        disclosure_text="API Consent Override",
        disclosure_language="en"
    )
    return {
        "call_id": body.call_id,
        "consent": body.consent,
        "recording_allowed": decision.allowed,
        "reason": decision.reason
    }


@router.post("/recording/retention/purge")
async def trigger_retention_purge(x_internal_api_key: str | None = Header(default=None)):
    """Manually triggers 30-day recording expiration cleanup."""
    require_internal_key(x_internal_api_key)
    purged = await retention_service.purge_expired_recordings()
    return {"status": "ok", "purged_count": purged}


class OutboundCallRequest(BaseModel):
    phone_number: str = Field(..., description="Destination number to call (e.g. 9705162303)")
    custom_field: Optional[str] = None


@router.post("/telephony/outbound-call")
async def trigger_outbound_call(body: OutboundCallRequest, x_internal_api_key: str | None = Header(default=None)):
    """Triggers an outbound call via Exotel to connect a live phone with the Voicebot flow."""
    require_internal_key(x_internal_api_key)
    result = await exotel_client.initiate_call(body.phone_number, body.custom_field)
    return result


@router.post("/telephony/status")
async def telephony_status(request: Request, x_exotel_signature: str | None = Header(default=None)):
    body = await request.body()
    if settings.app_env == "production" and not x_exotel_signature:
        raise HTTPException(status_code=401, detail="Missing telephony signature")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return {"received": True, "event": payload.get("Status", payload.get("event", "unknown"))}


@router.websocket("/telephony/media")
async def telephony_media(websocket: WebSocket):
    """
    Telephony AgentStream bidirectional WebSocket handler.
    Orchestrates live media streaming, speech recognition, multilingual conversational intelligence
    (Google Gemini / OpenAI), voice synthesis, and strictly consent-gated audio recording.
    """
    await websocket.accept()
    call_id: Optional[str] = None
    stream_sid: Optional[str] = None
    caller_number: str = "Unknown"
    current_language: str = "en" if settings.default_greeting_language == "auto" else settings.default_greeting_language
    owner_name: str = settings.owner_display_name
    company_name: str = ""

    audio_buffer: Optional[ConsentGatedAudioBuffer] = None
    history: List[Dict[str, str]] = []
    incoming_pcm_frames = bytearray()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("event")

            # 1. Connection established
            if event_type == "connected":
                print("[TelephonyMedia] Telephony connected.")
                continue

            # 2. Call started
            elif event_type == "start":
                start_data = event.get("start", {})
                stream_sid = event.get("stream_sid", start_data.get("stream_sid", "stream-1"))
                provider_call_id = start_data.get("call_sid", start_data.get("call_id", f"call-{stream_sid}"))
                caller_number = start_data.get("from", start_data.get("caller_id", "Unknown"))
                called_number = start_data.get("to", start_data.get("called_number", ""))

                # Look up user if called number matches a registered company user
                user_record = await db_service.get_user_by_phone(called_number) if called_number else None
                user_id = user_record["id"] if user_record else None
                if user_record:
                    owner_name = user_record["display_name"]
                    company_name = user_record.get("company_name", "")

                call_id = await db_service.create_call(
                    provider_call_id=provider_call_id,
                    caller_number=caller_number,
                    user_id=user_id
                )
                audio_buffer = ConsentGatedAudioBuffer(call_id=call_id, feature_enabled=settings.call_recording_enabled)

                # Generate initial greeting identifying AI and stating recording notice
                greeting_text = conversation_provider.get_initial_greeting(
                    language=current_language,
                    owner_name=owner_name,
                    company_name=company_name
                )
                history.append({"role": "assistant", "content": greeting_text})
                await db_service.add_transcript(call_id, speaker="assistant", content=greeting_text)

                # Synthesize and stream speech back
                async for pcm_frame in voice_provider.synthesize_stream(greeting_text, language=current_language):
                    b64_payload = base64.b64encode(pcm_frame).decode("ascii")
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "stream_sid": stream_sid,
                        "media": {"payload": b64_payload}
                    }))
                continue

            # 3. Audio chunk received from caller
            elif event_type == "media":
                media_data = event.get("media", {})
                payload_b64 = media_data.get("payload", "")
                if payload_b64:
                    raw_pcm = base64.b64decode(payload_b64)
                    incoming_pcm_frames.extend(raw_pcm)
                    if audio_buffer:
                        audio_buffer.add_pcm_chunk(raw_pcm)

                    # When enough audio accumulates (~1.5s = 24000 bytes of 8kHz 16-bit mono PCM)
                    if len(incoming_pcm_frames) >= 24000:
                        chunk_to_transcribe = bytes(incoming_pcm_frames)
                        incoming_pcm_frames.clear()

                        transcribed_text, detected_lang = await stt_provider.transcribe(chunk_to_transcribe)
                        if transcribed_text.strip():
                            current_language = detected_lang
                            history.append({"role": "user", "content": transcribed_text})
                            if call_id:
                                await db_service.add_transcript(call_id, speaker="caller", content=transcribed_text)

                            # Handle consent if awaiting
                            if audio_buffer and audio_buffer.consent_state == "awaiting_consent":
                                consent_verdict = parse_verbal_consent(transcribed_text)
                                if consent_verdict in ["yes", "no"]:
                                    await audio_buffer.update_consent(
                                        consent=consent_verdict,
                                        disclosure_text="Spoken notice given in initial greeting",
                                        disclosure_language=current_language
                                    )

                            # Generate response from AI
                            reply_text, current_language = await conversation_provider.reply(
                                history=history,
                                current_language=current_language,
                                owner_name=owner_name,
                                company_name=company_name
                            )
                            history.append({"role": "assistant", "content": reply_text})
                            if call_id:
                                await db_service.add_transcript(call_id, speaker="assistant", content=reply_text)

                            # Stream reply back to caller
                            async for pcm_frame in voice_provider.synthesize_stream(reply_text, language=current_language):
                                b64_payload = base64.b64encode(pcm_frame).decode("ascii")
                                await websocket.send_text(json.dumps({
                                    "event": "media",
                                    "stream_sid": stream_sid,
                                    "media": {"payload": b64_payload}
                                }))
                continue

            # 4. Call ended
            elif event_type == "stop":
                print(f"[TelephonyMedia] Call {call_id} ended.")
                break

    except WebSocketDisconnect:
        print(f"[TelephonyMedia] WebSocket disconnected for call {call_id}")
    finally:
        if call_id:
            storage_path = None
            recording_status = "not_recorded"

            if audio_buffer and audio_buffer.recording_allowed:
                wav_data = audio_buffer.get_final_wav_bytes()
                if wav_data:
                    storage_path = await db_service.save_recording(call_id, wav_data)
                    recording_status = "recording"
            elif audio_buffer and audio_buffer.consent_state == "no":
                recording_status = "declined"

            transcripts_for_summary = [{"speaker": m["role"], "content": m["content"]} for m in history]
            notes = await conversation_provider.extract_structured_notes(transcripts_for_summary, owner_name=owner_name)

            await db_service.finalize_call(
                call_id=call_id,
                caller_name=notes.get("caller_name"),
                detected_language=notes.get("detected_language", current_language),
                call_reason=notes.get("call_reason"),
                urgency=notes.get("urgency", "normal"),
                summary=notes.get("summary"),
                callback_required=notes.get("callback_required", True),
                preferred_callback_time=notes.get("preferred_callback_time"),
                recording_storage_path=storage_path,
                recording_status=recording_status
            )

            # Android Push Notification
            await notification_service.notify_call_summary(
                call_id=call_id,
                caller_number=caller_number,
                caller_name=notes.get("caller_name"),
                urgency=notes.get("urgency", "normal"),
                summary=notes.get("summary", "Call completed."),
                callback_required=notes.get("callback_required", True)
            )


@router.post("/test/simulate-call")
async def simulate_call_endpoint(req: SimulateCallRequest, current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """
    Test API endpoint to simulate an end-to-end phone call without live telephony.
    Tests STT, conversation prompt, consent enforcement, and notification dispatch.
    """
    user_id = current_user.get("user_id") if current_user else None
    owner_name = req.owner_name or (current_user.get("display_name") if current_user else settings.owner_display_name)
    company_name = req.company_name or ""

    call_id = await db_service.create_call(
        provider_call_id=f"test-{datetime.utcnow().timestamp()}",
        caller_number=req.caller_number,
        user_id=user_id
    )
    audio_buffer = ConsentGatedAudioBuffer(call_id=call_id, feature_enabled=settings.call_recording_enabled)

    dialogue_log = []
    history: List[Dict[str, str]] = []

    # 1. Initial greeting
    greeting = conversation_provider.get_initial_greeting(
        language=req.language,
        owner_name=owner_name,
        company_name=company_name
    )
    history.append({"role": "assistant", "content": greeting})
    await db_service.add_transcript(call_id, speaker="assistant", content=greeting)
    dialogue_log.append({"speaker": "AI Assistant", "text": greeting})

    # 2. Process caller utterances turn by turn
    curr_lang = req.language
    for utterance in req.caller_utterances:
        history.append({"role": "user", "content": utterance})
        await db_service.add_transcript(call_id, speaker="caller", content=utterance)
        dialogue_log.append({"speaker": "Caller", "text": utterance})

        # Check consent
        if audio_buffer.consent_state == "awaiting_consent":
            c_verdict = parse_verbal_consent(utterance)
            if c_verdict in ["yes", "no"]:
                await audio_buffer.update_consent(
                    consent=c_verdict,
                    disclosure_text="Spoken notice given in initial greeting",
                    disclosure_language=curr_lang
                )

        # AI reply
        reply, curr_lang = await conversation_provider.reply(
            history=history,
            current_language=curr_lang,
            owner_name=owner_name,
            company_name=company_name
        )
        history.append({"role": "assistant", "content": reply})
        await db_service.add_transcript(call_id, speaker="assistant", content=reply)
        dialogue_log.append({"speaker": "AI Assistant", "text": reply})

    # 3. Simulate audio frames if consented
    storage_path = None
    recording_status = "not_recorded"
    if audio_buffer.recording_allowed:
        simulated_pcm = bytearray(b"\x00\x00" * 8000)
        audio_buffer.add_pcm_chunk(bytes(simulated_pcm))
        wav_data = audio_buffer.get_final_wav_bytes()
        if wav_data:
            storage_path = await db_service.save_recording(call_id, wav_data)
            recording_status = "recording"
    elif audio_buffer.consent_state == "no":
        recording_status = "declined"

    # 4. Extract summary
    notes = await conversation_provider.extract_structured_notes(
        [{"speaker": m["role"], "content": m["content"]} for m in history],
        owner_name=owner_name
    )

    await db_service.finalize_call(
        call_id=call_id,
        caller_name=notes.get("caller_name"),
        detected_language=curr_lang,
        call_reason=notes.get("call_reason"),
        urgency=notes.get("urgency", "normal"),
        summary=notes.get("summary"),
        callback_required=notes.get("callback_required", True),
        preferred_callback_time=notes.get("preferred_callback_time"),
        recording_storage_path=storage_path,
        recording_status=recording_status
    )

    # 5. Push notification
    await notification_service.notify_call_summary(
        call_id=call_id,
        caller_number=req.caller_number,
        caller_name=notes.get("caller_name"),
        urgency=notes.get("urgency", "normal"),
        summary=notes.get("summary", "Test call processed."),
        callback_required=notes.get("callback_required", True)
    )

    final_call_record = await db_service.get_call(call_id)
    return {
        "status": "success",
        "call_id": call_id,
        "dialogue": dialogue_log,
        "summary": notes,
        "recording_status": recording_status,
        "recording_path": storage_path,
        "call_record": final_call_record
    }
