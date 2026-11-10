"""
Voice Provider & Telephony Codec Module.
Handles ElevenLabs streaming TTS with Ritesh's authorized cloned voice,
and converts audio into the exact telephony standard: mono PCM16 at 8 kHz.
Includes offline simulation fallback so testing works out of the box.
"""

import io
import math
import wave
import struct
import base64
import httpx
from typing import AsyncGenerator, Optional
from app.config import settings


# Precomputed G.711 mu-law table for telephony fallback if needed
_MULAW_TO_PCM = []
for i in range(256):
    byte = ~i & 0xFF
    sign = -1 if (byte & 0x80) else 1
    exponent = (byte >> 4) & 0x07
    mantissa = byte & 0x0F
    sample = sign * ((mantissa << 3) + 0x84) << exponent
    sample -= 0x84
    sample = max(-32768, min(32767, sample))
    _MULAW_TO_PCM.append(sample)


def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """Converts 8kHz G.711 mu-law bytes into 16-bit linear PCM (8kHz)."""
    samples = [_MULAW_TO_PCM[b] for b in mulaw_bytes]
    return struct.pack(f"<{len(samples)}h", *samples)


def pcm16_to_wav(pcm_bytes: bytes, sample_rate: int = 8000, channels: int = 1) -> bytes:
    """Wraps raw 16-bit linear PCM into a standard WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buf.getvalue()


def resample_16k_to_8k(pcm_16k: bytes) -> bytes:
    """Downsamples 16kHz mono PCM16 to 8kHz by 2x decimation."""
    num_samples = len(pcm_16k) // 2
    if num_samples == 0:
        return b""
    samples = struct.unpack(f"<{num_samples}h", pcm_16k)
    downsampled = samples[::2]
    return struct.pack(f"<{len(downsampled)}h", *downsampled)


class VoiceProvider:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id
        self.model_id = settings.elevenlabs_model_id

    async def synthesize_stream(self, text: str, language: str = "en") -> AsyncGenerator[bytes, None]:
        """
        Synthesizes text using ElevenLabs cloned voice and yields
        mono PCM16 8kHz frames (20ms frames = 320 bytes each) for Exotel streaming.
        """
        # Fallback to simulation if credentials are not configured
        if not self.api_key or not self.voice_id or self.voice_id.startswith("your_"):
            async for frame in self._mock_speech_frames(text):
                yield frame
            return

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream?output_format=pcm_16000&optimize_streaming_latency=3"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        buffer = bytearray()
                        # Read 640 bytes of 16kHz (20ms of audio) -> downsampled to 320 bytes of 8kHz
                        chunk_size = 640
                        async for chunk in response.aiter_bytes():
                            buffer.extend(chunk)
                            while len(buffer) >= chunk_size:
                                pcm_16k = bytes(buffer[:chunk_size])
                                buffer = buffer[chunk_size:]
                                pcm_8k = resample_16k_to_8k(pcm_16k)
                                yield pcm_8k

                        if buffer:
                            pcm_8k = resample_16k_to_8k(bytes(buffer))
                            yield pcm_8k
                    else:
                        err_text = await response.aread()
                        print(f"[VoiceProvider] ElevenLabs API error {response.status_code}: {err_text.decode('utf-8', errors='ignore')}")
                        async for frame in self._mock_speech_frames(text):
                            yield frame
        except Exception as e:
            print(f"[VoiceProvider] Synthesis request failed: {e}")
            async for frame in self._mock_speech_frames(text):
                yield frame

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """Collects all stream frames into a single mono PCM16 8kHz byte block."""
        all_frames = bytearray()
        async for frame in self.synthesize_stream(text, language):
            all_frames.extend(frame)
        return bytes(all_frames)

    async def _mock_speech_frames(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Simulates speech audio frames (mono PCM16 at 8kHz, 20ms frames = 160 samples = 320 bytes).
        Permits instant offline testing without API keys.
        """
        frame_samples = 160
        # Estimate duration: ~3 words per second, min 0.6s
        word_count = max(1, len(text.split()))
        duration = min(4.0, max(0.8, word_count * 0.32))
        total_frames = int(duration * 50)  # 50 frames per second

        for f_idx in range(total_frames):
            frame_bytes = bytearray()
            for s in range(frame_samples):
                t = (f_idx * frame_samples + s) / 8000.0
                # Harmonic mixture mimicking voice pitch (220 Hz and 440 Hz)
                sample = int(3200 * (0.7 * math.sin(2 * math.pi * 220 * t) + 0.3 * math.sin(2 * math.pi * 440 * t)))
                frame_bytes.extend(struct.pack("<h", sample))
            yield bytes(frame_bytes)


voice_provider = VoiceProvider()
