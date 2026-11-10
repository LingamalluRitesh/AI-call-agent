"""
AI Provider Module.
Orchestrates:
1. Multilingual Speech-to-Text (STT) via OpenAI Whisper.
2. Receptionist conversation management via OpenAI GPT-4o with multilingual adaptation (Telugu, Hindi, English).
3. Structured post-call note and summary extraction.
Includes complete offline/simulation fallbacks for test runs.
"""

import json
import httpx
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.agents.prompt import SYSTEM_PROMPT
from app.services.knowledge_base import load_knowledge_base
from app.services.voice_provider import pcm16_to_wav


class STTProvider:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_stt_model

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 8000) -> Tuple[str, str]:
        """
        Transcribes mono PCM16 audio bytes into text.
        Returns: (transcribed_text, detected_language)
        """
        if not self.api_key or self.api_key.startswith("your_"):
            return self._mock_transcription(len(pcm_bytes))

        wav_bytes = pcm16_to_wav(pcm_bytes, sample_rate=sample_rate)

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("caller_audio.wav", wav_bytes, "audio/wav")}
        data = {"model": self.model, "response_format": "verbose_json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, files=files, data=data)
                if res.status_code == 200:
                    result = res.json()
                    text = result.get("text", "").strip()
                    lang = result.get("language", "en")
                    normalized_lang = "te" if "telugu" in lang.lower() else ("hi" if "hindi" in lang.lower() else "en")
                    return text, normalized_lang
                else:
                    print(f"[STTProvider] Whisper API error {res.status_code}: {res.text}")
                    return self._mock_transcription(len(pcm_bytes))
        except Exception as e:
            print(f"[STTProvider] Request failed: {e}")
            return self._mock_transcription(len(pcm_bytes))

    def _mock_transcription(self, byte_length: int) -> Tuple[str, str]:
        if byte_length < 800:
            return "", "en"
        return "Hello, I am calling regarding website development with RMVS Web Services.", "en"


class ConversationProvider:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_text_model
        self.kb_data = load_knowledge_base()

    def build_initial_system_prompt(self) -> str:
        kb_json = json.dumps(self.kb_data, ensure_ascii=False, indent=2)
        return f"""
{SYSTEM_PROMPT.strip()}

=== APPROVED KNOWLEDGE BASE ===
{kb_json}
===============================
"""

    def get_initial_greeting(self, language: str = "en") -> str:
        """Mandatory initial greeting identifying AI and stating recording notice."""
        if language == "te":
            return (
                "నమస్కారం అండి, నేను రితేష్ గారి AI అసిస్టెంట్ ని మాట్లాడుతున్నాను. రితేష్ గారు ప్రస్తుతం అందుబాటులో లేరు. "
                "నాణ్యత మరియు కాల్-బ్యాక్ వివరాల కొరకు ఈ కాల్ రికార్డ్ చేయబడుతుంది. మీకు అభ్యంతరం లేదా అండి?"
            )
        elif language == "hi":
            return (
                "नमस्ते, मैं रितेश का AI असिस्टेंट बात कर रहा हूँ। रितेश अभी उपलब्ध नहीं हैं। "
                "गुणवत्ता और कॉलबैक के लिए यह कॉल रिकॉर्ड की जा सकती है। क्या आप इससे सहमत हैं?"
            )
        else:
            return (
                "Hello, I am Ritesh's AI call assistant. Ritesh is currently unavailable. "
                "For quality and callback notes, this call may be recorded. Do I have your consent to record?"
            )

    def detect_language(self, text: str) -> str:
        """Detects whether text is in Telugu, Hindi, or English."""
        # Check Telugu Unicode range
        if any('\u0c00' <= ch <= '\u0c7f' for ch in text) or any(w in text.lower() for w in ["namaskaram", "andi", "sare", "cheppandi", "bagunnara"]):
            return "te"
        # Check Devanagari Unicode range
        if any('\u0900' <= ch <= '\u097f' for ch in text) or any(w in text.lower() for w in ["namaste", "aap", "theek", "kaise", "bataiye"]):
            return "hi"
        return "en"

    async def reply(self, history: List[Dict[str, str]], current_language: str = "en") -> Tuple[str, str]:
        """
        Generates assistant response based on conversation history.
        Returns: (response_text, detected_language)
        """
        last_user_msg = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        detected_lang = self.detect_language(last_user_msg) if last_user_msg else current_language

        if not self.api_key or self.api_key.startswith("your_"):
            reply_text = self._mock_reply(last_user_msg, detected_lang)
            return reply_text, detected_lang

        messages = [{"role": "system", "content": self.build_initial_system_prompt()}] + history

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 200
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content, detected_lang
                else:
                    print(f"[ConversationProvider] OpenAI error {res.status_code}: {res.text}")
                    return self._mock_reply(last_user_msg, detected_lang), detected_lang
        except Exception as e:
            print(f"[ConversationProvider] Request failed: {e}")
            return self._mock_reply(last_user_msg, detected_lang), detected_lang

    def _mock_reply(self, user_msg: str, lang: str) -> str:
        msg_lower = user_msg.lower()

        # Telugu mock responses
        if lang == "te":
            if any(w in msg_lower for w in ["no", "vaddu", "వద్దు", "oddu"]):
                return "సరేనండి, ఎటువంటి సమస్య లేదు! ఈ కాల్ ని మేము రికార్డ్ చేయము. మీ సందేశం లేదా అవసరం ఏమిటో దయచేసి చెప్పండి."
            elif any(w in msg_lower for w in ["yes", "sare", "సరే", "ok"]):
                return "ధన్యవాదాలు అండి. RMVS వెబ్ సర్వీసెస్ లో మేము ఆధునిక వెబ్‌సైట్స్ మరియు ప్రాజెక్ట్స్ చేస్తాము. మీకు ఎటువంటి వెబ్‌సైట్ కావాలి?"
            elif any(w in msg_lower for w in ["cost", "price", "ఖర్చు", "ధర"]):
                return "ధర అనేది మీ ప్రాజెక్ట్ ఫీచర్స్ పై ఆధారపడి ఉంటుంది. రితేష్ గారు మీ అవసరాలను సమీక్షించి ఖచ్చితమైన ఎస్టిమేట్ ఇస్తారు. మీ పేరు చెప్పగలరా?"
            else:
                return "ధన్యవాదాలు అండి. మీ వివరాలను నోట్ చేసుకున్నాను. రితేష్ గారు త్వరలోనే మీకు తిరిగి కాల్ చేస్తారు."

        # Hindi mock responses
        elif lang == "hi":
            if any(w in msg_lower for w in ["no", "nahi", "नहीं", "mat karo"]):
                return "कोई बात नहीं! यह कॉल रिकॉर्ड नहीं की जाएगी। आप निश्चिंत होकर बताएं कि मैं आपकी क्या मदद कर सकता हूँ?"
            elif any(w in msg_lower for w in ["yes", "haan", "हाँ", "theek"]):
                return "धन्यवाद! RMVS वेब सर्विसेज बिजनेस वेबसाइट्स और प्रोजेक्ट्स बनाती है। आपको किस तरह की वेबसाइट चाहिए?"
            elif any(w in msg_lower for w in ["cost", "price", "खर्च", "कीमत"]):
                return "फाइनल प्राइस प्रोजेक्ट की रिक्वायरमेंट पर तय होती है। रितेश जी डिटेल्स देखकर आपको एस्टीमेट देंगे। कृपया अपना नाम बताएं?"
            else:
                return "धन्यवाद! मैंने आपकी जानकारी नोट कर ली है। रितेश जी जल्द ही आपसे संपर्क करेंगे।"

        # English mock responses
        else:
            if any(w in msg_lower for w in ["no", "don't", "refuse", "not comfortable"]):
                return "No problem at all! We will not record this call. Please let me know what message you would like me to pass to Ritesh."
            elif any(w in msg_lower for w in ["yes", "sure", "okay", "agree"]):
                return "Thank you! How can I assist you today with RMVS Web Services or leaving a message for Ritesh?"
            elif any(w in msg_lower for w in ["price", "cost", "quote"]):
                return "RMVS Web Services tailors pricing to specific feature requirements. Ritesh will confirm the exact estimate after understanding your scope. May I have your name and preferred callback time?"
            elif any(w in msg_lower for w in ["website", "services", "web"]):
                return "We develop single-page and multi-page business websites, custom web applications, and assist with academic B.Tech/M.Tech projects. When would you need the project completed?"
            elif any(w in msg_lower for w in ["urgent", "emergency", "down"]):
                return "I will mark this as urgent and notify Ritesh immediately. He will get back to you as soon as possible."
            else:
                return "Thank you. I have documented your requirements and will pass them to Ritesh. Have a great day!"

    async def extract_structured_notes(self, transcript_lines: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extracts structured summary and metadata from completed conversation."""
        conversation_str = "\n".join([f"{t['speaker'].upper()}: {t['content']}" for t in transcript_lines])

        if not self.api_key or self.api_key.startswith("your_"):
            return self._heuristic_summary(conversation_str)

        prompt = f"""
Analyze this call transcript between a caller and Ritesh's AI call assistant:
---
{conversation_str}
---

Return a valid JSON object matching this schema:
{{
  "caller_name": "Caller's name if identified, else null",
  "call_reason": "Primary purpose of the call in one concise sentence",
  "detected_language": "en" | "te" | "hi",
  "urgency": "low" | "normal" | "high" | "emergency",
  "summary": "2-3 sentence executive summary of the conversation",
  "callback_required": true | false,
  "preferred_callback_time": "Preferred time mentioned or null",
  "recording_consent": "yes" | "no" | "unknown"
}}

Respond ONLY with valid JSON.
"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    return json.loads(res.json()["choices"][0]["message"]["content"])
                else:
                    return self._heuristic_summary(conversation_str)
        except Exception:
            return self._heuristic_summary(conversation_str)

    def _heuristic_summary(self, conversation_str: str) -> Dict[str, Any]:
        text_lower = conversation_str.lower()
        urgency = "emergency" if any(w in text_lower for w in ["emergency", "crash", "outage", "down", "hospital"]) else (
            "high" if "urgent" in text_lower else "normal"
        )
        consent = "yes" if any(w in text_lower for w in ["yes", "agree", "sure", "sare", "haan"]) else (
            "no" if any(w in text_lower for w in ["no", "vaddu", "nahi", "don't"]) else "unknown"
        )
        return {
            "caller_name": "Inquiring Caller",
            "call_reason": "Inquired about RMVS Web Services and website development.",
            "detected_language": "en",
            "urgency": urgency,
            "summary": "Caller reached Ritesh's AI call assistant to discuss website requirements and requested a callback with project details.",
            "callback_required": True,
            "preferred_callback_time": "As soon as available",
            "recording_consent": consent
        }


stt_provider = STTProvider()
conversation_provider = ConversationProvider()
