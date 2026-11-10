"""
Voice Provider & Telephony Codec Module.
Supports:
1. Google Gemini Speech (TTS) when GEMINI_API_KEY is configured.
2. ElevenLabs Cloned Voice streaming when ELEVENLABS_API_KEY is configured.
3. Telephony audio codec encoding: converts audio to exact standard mono PCM16 at 8 kHz.
4. Offline harmonic audio synthesizer fallback for 100% reliable local/offline testing.
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


def resample_24k_to_8k(pcm_24k: bytes) -> bytes:
    """Downsamples 24kHz mono PCM16 to 8kHz by 3x decimation."""
    num_samples = len(pcm_24k) // 2
    if num_samples == 0:
        return b""
    samples = struct.unpack(f"<{num_samples}h", pcm_24k)
    downsampled = samples[::3]
    return struct.pack(f"<{len(downsampled)}h", *downsampled)


class VoiceProvider:
    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.elevenlabs_key = settings.elevenlabs_api_key
        self.elevenlabs_voice_id = settings.elevenlabs_voice_id
        self.elevenlabs_model_id = settings.elevenlabs_model_id

    async def synthesize_stream(self, text: str, language: str = "en") -> AsyncGenerator[bytes, None]:
        """
        Synthesizes text and yields mono PCM16 8kHz frames (20ms frames = 320 bytes each) for Exotel/Twilio streaming.
        Order of priority:
        1. ElevenLabs (if cloned voice configured)
        2. Gemini Speech (if GEMINI_API_KEY configured)
        3. Local simulation audio synthesizer
        """
        # 1. ElevenLabs Cloned Voice
        if self.elevenlabs_key and self.elevenlabs_voice_id and not self.elevenlabs_voice_id.startswith("your_"):
            try:
                async for frame in self._stream_elevenlabs(text):
                    yield frame
                return
            except Exception as e:
                print(f"[VoiceProvider] ElevenLabs streaming failed: {e}. Falling back.")

        # 2. Gemini Speech
        if self.gemini_key and not self.gemini_key.startswith("your_"):
            try:
                gemini_pcm = await self._synthesize_gemini_tts(text)
                if gemini_pcm:
                    # Yield in 20ms chunks (320 bytes of 8kHz 16-bit mono)
                    chunk_size = 320
                    for i in range(0, len(gemini_pcm), chunk_size):
                        yield gemini_pcm[i:i + chunk_size]
                    return
            except Exception as e:
                print(f"[VoiceProvider] Gemini TTS failed: {e}. Falling back.")

        # 3. Offline simulation synthesizer
        async for frame in self._mock_speech_frames(text):
            yield frame

    async def _stream_elevenlabs(self, text: str) -> AsyncGenerator[bytes, None]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream?output_format=pcm_16000&optimize_streaming_latency=3"
        headers = {
            "xi-api-key": self.elevenlabs_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": self.elevenlabs_model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code == 200:
                    buffer = bytearray()
                    chunk_size = 640
                    async for chunk in response.aiter_bytes():
                        buffer.extend(chunk)
                        while len(buffer) >= chunk_size:
                            pcm_16k = bytes(buffer[:chunk_size])
                            buffer = buffer[chunk_size:]
                            yield resample_16k_to_8k(pcm_16k)
                    if buffer:
                        yield resample_16k_to_8k(bytes(buffer))
                else:
                    raise RuntimeError(f"ElevenLabs error {response.status_code}")

    async def _synthesize_gemini_tts(self, text: str) -> Optional[bytes]:
        """Synthesizes speech using Google Gemini audio/TTS endpoint."""
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            # Check interaction output_audio
            interaction = client.interactions.create(
                model=settings.gemini_tts_model,
                input=f"Read this message clearly, professionally, and naturally: {text}"
            )
            if hasattr(interaction, "output_audio") and interaction.output_audio:
                audio_bytes = base64.b64decode(interaction.output_audio.data)
                # Resample 24k/16k to 8k
                if len(audio_bytes) > 44 and audio_bytes[:4] == b"RIFF":
                    raw_pcm = audio_bytes[44:]
                    return resample_24k_to_8k(raw_pcm)
                return resample_16k_to_8k(audio_bytes)
        except Exception:
            pass
        return None

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
        word_count = max(1, len(text.split()))
        duration = min(4.0, max(0.8, word_count * 0.32))
        total_frames = int(duration * 50)  # 50 frames per second

        for f_idx in range(total_frames):
            frame_bytes = bytearray()
            for s in range(frame_samples):
                t = (f_idx * frame_samples + s) / 8000.0
                sample = int(3200 * (0.7 * math.sin(2 * math.pi * 220 * t) + 0.3 * math.sin(2 * math.pi * 440 * t)))
                frame_bytes.extend(struct.pack("<h", sample))
            yield bytes(frame_bytes)


voice_provider = VoiceProvider()
