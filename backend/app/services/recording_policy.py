"""
Recording Policy & Consent-Gated Audio Buffer.
Guarantees privacy safeguards:
- Audio is NEVER written to persistent storage without affirmative caller consent.
- If consent is declined or unclear, audio buffers are instantly purged.
"""

import io
from dataclasses import dataclass
from typing import Optional, List
from app.services.voice_provider import pcm16_to_wav
from app.services.database import db_service


@dataclass
class RecordingDecision:
    allowed: bool
    reason: str


def recording_decision(*, feature_enabled: bool, consent: str | None,
                       affirmative_required: bool = True) -> RecordingDecision:
    if not feature_enabled:
        return RecordingDecision(False, "recording_disabled")
    if affirmative_required and consent != "yes":
        return RecordingDecision(False, "affirmative_consent_not_obtained")
    if consent == "no":
        return RecordingDecision(False, "caller_declined")
    return RecordingDecision(True, "consent_confirmed")


def parse_verbal_consent(caller_text: str) -> str:
    """Detects 'yes', 'no', or 'unknown' from caller's verbal statement in EN, TE, HI."""
    text = caller_text.lower()

    # Negative keywords (checked first for privacy safety)
    negatives = [
        "no", "nope", "don't record", "do not record", "not comfortable", "no recording",
        "vaddu", "vaddandi", "record cheyoddu", "వద్దు", "వద్దండి",
        "nahi", "mat karo", "record mat karna", "नहीं", "ना"
    ]
    if any(neg in text for neg in negatives):
        return "no"

    # Positive keywords
    positives = [
        "yes", "yeah", "sure", "okay", "ok", "fine", "agree", "comfortable", "alright",
        "sare", "sare andi", "parvaledu", "parvaledandi", "సరే", "సరేనండి", "పర్వాలేదు",
        "haan", "theek hai", "chalega", "हाँ", "ठीक है"
    ]
    if any(pos in text for pos in positives):
        return "yes"

    return "unknown"


class ConsentGatedAudioBuffer:
    """Manages call audio frames in memory and strictly enforces consent-gated persistence."""
    def __init__(self, call_id: str, feature_enabled: bool = True):
        self.call_id = call_id
        self.feature_enabled = feature_enabled
        self.consent_state: str = "awaiting_consent"  # awaiting_consent, yes, no
        self.buffer = bytearray()
        self.recording_allowed: bool = False

    def add_pcm_chunk(self, chunk: bytes):
        """Adds PCM16 8kHz chunk if recording is awaiting or allowed."""
        if self.consent_state in ["awaiting_consent", "yes"]:
            self.buffer.extend(chunk)

    async def update_consent(self, consent: str, disclosure_text: str, disclosure_language: str = "en"):
        self.consent_state = consent
        decision = recording_decision(
            feature_enabled=self.feature_enabled,
            consent=consent,
            affirmative_required=True
        )
        self.recording_allowed = decision.allowed

        # Persist consent decision in database
        await db_service.record_consent(
            call_id=self.call_id,
            consent=consent,
            disclosure_text=disclosure_text,
            disclosure_language=disclosure_language
        )

        # If declined, immediately purge in-memory buffer
        if not self.recording_allowed:
            self.buffer.clear()
            print(f"[RecordingPolicy] Call {self.call_id}: Consent declined. In-memory audio buffer purged.")
        else:
            print(f"[RecordingPolicy] Call {self.call_id}: Affirmative consent granted. Recording active.")

    def get_final_wav_bytes(self) -> Optional[bytes]:
        """Returns WAV bytes only if consent was affirmed and audio exists."""
        if not self.recording_allowed or len(self.buffer) == 0:
            return None
        return pcm16_to_wav(bytes(self.buffer), sample_rate=8000, channels=1)
