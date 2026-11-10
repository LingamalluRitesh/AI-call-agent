"""
Interactive Call Simulator & Test Harness.
Allows testing the complete Real-Time AI Calling Pipeline without activating live call forwarding:
1. Exotel AgentStream media protocol simulation.
2. Multilingual conversation (English, Telugu, Hindi).
3. Privacy-first consent-gated recording policy (affirmative vs declined).
4. RMVS Web Services knowledge retrieval & pricing safeguards.
5. Post-call structured summary generation.
6. Android push notification dispatch.
"""

import sys
import os
import asyncio
from typing import List

# Ensure app is in Python path and stdout is UTF-8 clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.services.database import db_service
from app.services.recording_policy import ConsentGatedAudioBuffer, parse_verbal_consent
from app.services.ai_provider import conversation_provider
from app.services.voice_provider import voice_provider
from app.services.notification_service import notification_service
from app.config import settings


BANNER = """
======================================================================
       RITESH AI CALL ASSISTANT — REAL-TIME PIPELINE SIMULATOR       
======================================================================
 Testing Exotel Audio Stream + OpenAI Conversation + ElevenLabs Cloned Voice
 Privacy Safeguard: Consent-Gated Audio Recording (30-day Retention)
 Approved Knowledge Base: RMVS Web Services (Website Development)
======================================================================
"""


async def run_simulation(caller_number: str, test_scenarios: List[str], language: str = "en"):
    print(f"\n[+] Starting Call Session for: {caller_number} (Language: {language.upper()})")

    # 1. Initialize Call in Database
    call_id = await db_service.create_call(
        provider_call_id=f"sim-{os.urandom(4).hex()}",
        caller_number=caller_number
    )
    print(f"[OK] Call Initialized in Database -> Call ID: {call_id}")

    # 2. Setup Consent-Gated Audio Buffer
    audio_buffer = ConsentGatedAudioBuffer(call_id=call_id, feature_enabled=settings.call_recording_enabled)
    history = []

    # 3. Initial AI Greeting & Mandatory Consent Notice
    greeting = conversation_provider.get_initial_greeting(language=language)
    history.append({"role": "assistant", "content": greeting})
    await db_service.add_transcript(call_id, speaker="assistant", content=greeting)

    print("\n" + "-" * 70)
    print(f"[AI ASSISTANT]: {greeting}")
    print("-" * 70)

    # Synthesize audio for greeting
    greeting_audio = await voice_provider.synthesize(greeting, language=language)
    print(f"   [Audio Stream] Synthesized {len(greeting_audio)} bytes of Telephony mono PCM16 8kHz")

    # 4. Turn-by-Turn Dialogue
    curr_lang = language
    for idx, caller_msg in enumerate(test_scenarios, 1):
        print(f"\n[CALLER] (Turn {idx}): {caller_msg}")
        history.append({"role": "user", "content": caller_msg})
        await db_service.add_transcript(call_id, speaker="caller", content=caller_msg)

        # Evaluate Consent if pending
        if audio_buffer.consent_state == "awaiting_consent":
            consent_verdict = parse_verbal_consent(caller_msg)
            if consent_verdict in ["yes", "no"]:
                await audio_buffer.update_consent(
                    consent=consent_verdict,
                    disclosure_text="Spoken notice given in greeting",
                    disclosure_language=curr_lang
                )
                if consent_verdict == "yes":
                    print("   [Privacy Audit] Affirmative Consent CONFIRMED -> Audio Recording ACTIVATED.")
                else:
                    print("   [Privacy Audit] Consent DECLINED -> Audio Buffer PURGED (No audio saved).")

        # Simulate incoming caller audio
        if audio_buffer.recording_allowed:
            simulated_caller_pcm = b"\x00\x00" * 3200  # simulated audio chunk
            audio_buffer.add_pcm_chunk(simulated_caller_pcm)

        # AI Reply
        reply, curr_lang = await conversation_provider.reply(history, curr_lang)
        history.append({"role": "assistant", "content": reply})
        await db_service.add_transcript(call_id, speaker="assistant", content=reply)

        print(f"[AI ASSISTANT]: {reply}")

        # Synthesize reply audio
        reply_audio = await voice_provider.synthesize(reply, language=curr_lang)
        print(f"   [Audio Stream] Synthesized {len(reply_audio)} bytes of Telephony mono PCM16 8kHz")

    # 5. Call Teardown & Persistence
    print("\n[+] Call Disconnected. Processing Post-Call Pipeline...")

    storage_path = None
    recording_status = "not_recorded"
    if audio_buffer.recording_allowed:
        wav_bytes = audio_buffer.get_final_wav_bytes()
        if wav_bytes:
            storage_path = await db_service.save_recording(call_id, wav_bytes)
            recording_status = "recording"
            print(f"[OK] Consent-Gated Recording SAVED to: {storage_path}")
    elif audio_buffer.consent_state == "no":
        recording_status = "declined"
        print("[OK] Privacy Safeguard Enforced: Caller declined recording. ZERO audio saved.")

    # 6. Structured Notes & AI Summary Extraction
    print("[+] Extracting Structured Call Summary...")
    notes = await conversation_provider.extract_structured_notes([
        {"speaker": m["role"], "content": m["content"]} for m in history
    ])

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

    print("\n======================= CALL SUMMARY =======================")
    print(f" Caller Name        : {notes.get('caller_name')}")
    print(f" Language Detected  : {curr_lang.upper()}")
    print(f" Call Reason        : {notes.get('call_reason')}")
    print(f" Urgency Level      : {notes.get('urgency', 'normal').upper()}")
    print(f" Callback Required  : {notes.get('callback_required')}")
    print(f" Preferred Time     : {notes.get('preferred_callback_time')}")
    print(f" Recording Status   : {recording_status.upper()}")
    print(f" Summary            : {notes.get('summary')}")
    print("============================================================")

    # 7. Android Push Notification Dispatch
    print("\n[+] Dispatching Android Push Notification...")
    await notification_service.notify_call_summary(
        call_id=call_id,
        caller_number=caller_number,
        caller_name=notes.get("caller_name"),
        urgency=notes.get("urgency", "normal"),
        summary=notes.get("summary", "Call completed."),
        callback_required=notes.get("callback_required", True)
    )
    print("[OK] Notification Sent Successfully to Ritesh's Android Device.")

    return call_id


async def main():
    print(BANNER)

    print("Select a simulation scenario to run:")
    print("  1. English Call: RMVS Website Inquiry (Consent GRANTED)")
    print("  2. Telugu Call : RMVS Project Inquiry (Consent GRANTED)")
    print("  3. Hindi Call  : E-Commerce Inquiry (Consent DECLINED - Privacy Safeguard)")
    print("  4. Urgent Emergency Call (Server Down Alert)")

    # Parse command line argument
    target_number = "+919705162303"
    choice = "1"
    selected_lang = "en"

    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.replace("+", "").isdigit() and len(arg.replace("+", "")) >= 10:
            target_number = arg if arg.startswith("+") else f"+91{arg.lstrip('0')}"
            choice = "custom_number"
            if len(sys.argv) > 2:
                selected_lang = sys.argv[2].strip().lower()
        else:
            choice = arg

    if choice == "custom_number":
        print(f"\n>>> Running Dedicated Voice & Conversation Test for Phone Number: {target_number} (Language: {selected_lang.upper()}) <<<")
        if selected_lang == "te":
            test_utterances = [
                "సరేనండి, రికార్డ్ చేసుకోవచ్చు.",
                "నమస్కారం, 9705162303 నుంచి మాట్లాడుతున్నాను. RMVS వెబ్ సర్వీసెస్ లో మా బిజినెస్ కోసం వెబ్‌సైట్ చేయించాలి.",
                "ఖర్చు మరియు టైమ్‌లైన్ ఎంత పడుతుంది? రితేష్ గారికి వివరాలు చెప్పండి.",
                "సాయంత్రం లోపు రితేష్ గారిని నాకు కాల్ చేయమని చెప్పండి."
            ]
        elif selected_lang == "hi":
            test_utterances = [
                "हाँ, ठीक है, रिकॉर्ड कर सकते हैं।",
                "नमस्ते, मैं 9705162303 से बोल रहा हूँ। हमें एक नई ई-कॉमर्स वेबसाइट बनानी है।",
                "रितेश जी से बात करनी थी, क्या वे आज कॉल कर सकते हैं?"
            ]
        else:
            test_utterances = [
                "Yes, I consent to this call being recorded.",
                "Hello, I am calling Ritesh regarding website design and development services from RMVS Web Services.",
                "We need a responsive corporate website with contact forms. Can Ritesh give an estimate and timeline?",
                "My name is authorized caller from 9705162303. Please ask Ritesh to call me back today."
            ]

        await run_simulation(
            caller_number=target_number,
            test_scenarios=test_utterances,
            language=selected_lang
        )
    elif choice == "1":
        await run_simulation(
            caller_number="+919876543210",
            test_scenarios=[
                "Yes, I am fine with recording.",
                "Hi, I want to build a modern 5-page business website for my consulting agency with RMVS Web Services.",
                "How much will it cost and how quickly can Ritesh deliver it?",
                "My name is Sandeep Verma. Please ask Ritesh to call me tomorrow morning at 10 AM."
            ],
            language="en"
        )
    elif choice == "2":
        await run_simulation(
            caller_number="+919848012345",
            test_scenarios=[
                "సరేనండి, రికార్డ్ చేసుకోవచ్చు.",
                "నమస్కారం, మా కాలేజ్ B.Tech ప్రాజెక్ట్ వెబ్ అప్లికేషన్ డెవలప్‌మెంట్ కోసం రితేష్ గారిని కలవాలి.",
                "నా పేరు వెంకట్. రితేష్ గారిని సాయంత్రం 5 గంటలకు కాల్ చేయమని చెప్పండి."
            ],
            language="te"
        )
    elif choice == "3":
        await run_simulation(
            caller_number="+919711223344",
            test_scenarios=[
                "नहीं, रिकॉर्ड मत करना।",
                "मुझे एक ऑनलाइन कपड़ों की ई-कॉमर्स वेबसाइट बनवानी है। RMVS वेब सर्विसेज में यह सर्विस उपलब्ध है क्या?",
                "मेरा नाम राहुल है, रितेश को मेरा मैसेज दे देना।"
            ],
            language="hi"
        )
    elif choice == "4":
        await run_simulation(
            caller_number="+919811009988",
            test_scenarios=[
                "Yes, sure.",
                "Emergency! The production website payment gateway is throwing errors and clients cannot checkout! Please alert Ritesh immediately!"
            ],
            language="en"
        )


if __name__ == "__main__":
    asyncio.run(main())
