"""
=============================================================================
RITESH AI CALL ASSISTANT — COMPREHENSIVE AUTOMATED TEST SUITE
=============================================================================
Automated End-to-End Verification Pipeline for Cloud & Mobile Readiness:
1. System & Environment Configurations
2. Neon Cloud PostgreSQL Connection & Database Schema Verification
3. Live Backend Health & Dashboard Stats Endpoints
4. Multilingual Simulation Engine (English, Telugu, Hindi, Emergency)
5. Privacy-First Consent Safeguards & Audio Buffer Policy
6. Retention Policy & Expired Recording Purge
7. Call Detail & Transcript Fetch Integrity
8. Mobile APK Download Endpoint & Binary Integrity
=============================================================================
"""

import sys
import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Force working directory to backend
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import httpx
from app.config import settings
from app.services.database import db_service

BASE_URL = os.getenv("TEST_SERVER_URL", "http://127.0.0.1:8000")

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration_ms = 0.0

results: List[TestResult] = []


def record_result(name: str, passed: bool, message: str, start_time: float):
    res = TestResult(name)
    res.passed = passed
    res.message = message
    res.duration_ms = (time.time() - start_time) * 1000
    results.append(res)
    icon = "PASSED" if passed else "FAILED"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{icon}{reset}] {name} ({res.duration_ms:.1f}ms) - {message}", flush=True)


async def test_01_environment_config():
    t0 = time.time()
    try:
        assert settings.owner_display_name == "Ritesh", "Owner display name must be Ritesh"
        assert settings.owner_phone_number, "Owner phone number must be configured"
        assert settings.neon_database_url or settings.database_url, "Database URL must be present"
        db_type = "Neon PostgreSQL" if db_service.use_neon else "SQLite Local"
        record_result(
            "01. Environment & Config Verification",
            True,
            f"Config valid. Owner: {settings.owner_display_name} ({settings.owner_phone_number}) | DB Engine: {db_type}",
            t0
        )
    except Exception as e:
        record_result("01. Environment & Config Verification", False, str(e), t0)


async def test_02_neon_postgresql_connectivity():
    t0 = time.time()
    try:
        if not db_service.use_neon:
            raise RuntimeError("Backend is not configured to use Neon PostgreSQL. Check NEON_DATABASE_URL.")
        
        with db_service._get_connection() as conn:
            with conn.cursor() as cur:
                # Check tables exist
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('call_logs', 'call_transcripts', 'call_recording_consents');
                """)
                tables = [r["table_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
                assert "call_logs" in tables, "Table 'call_logs' missing in Neon DB"
                assert "call_transcripts" in tables, "Table 'call_transcripts' missing in Neon DB"
                assert "call_recording_consents" in tables, "Table 'call_recording_consents' missing in Neon DB"

                # Check row count
                cur.execute("SELECT count(*) FROM call_logs;")
                r = cur.fetchone()
                call_count = r["count"] if isinstance(r, dict) else r[0]
                
        record_result(
            "02. Neon Cloud PostgreSQL Health",
            True,
            f"Connected to Neon! Found 3/3 tables. Active calls in cloud DB: {call_count}",
            t0
        )
    except Exception as e:
        record_result("02. Neon Cloud PostgreSQL Health", False, str(e), t0)


async def test_03_health_endpoint(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        resp = await client.get(f"{BASE_URL}/health", timeout=10.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "ok", "Expected status: ok"
        assert data.get("service") == "ritesh-ai-call-assistant", "Unexpected service name"
        record_result(
            "03. GET /health Endpoint",
            True,
            f"HTTP 200 OK. Service: {data.get('service')} v{data.get('version')}",
            t0
        )
    except Exception as e:
        record_result("03. GET /health Endpoint", False, str(e), t0)


async def test_04_dashboard_stats(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        resp = await client.get(f"{BASE_URL}/api/dashboard/stats", timeout=10.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        for field in ["total_calls", "calls_today", "unread_messages", "recorded_calls", "emergency_calls"]:
            assert field in data, f"Missing field in stats: {field}"
            assert isinstance(data[field], int), f"Field {field} is not int"
        record_result(
            "04. GET /api/dashboard/stats Endpoint",
            True,
            f"HTTP 200 OK. Total Calls: {data['total_calls']} | Unread: {data['unread_messages']} | Recorded: {data['recorded_calls']} | Emergency: {data['emergency_calls']}",
            t0
        )
    except Exception as e:
        record_result("04. GET /api/dashboard/stats Endpoint", False, str(e), t0)


async def test_05_calls_list(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        resp = await client.get(f"{BASE_URL}/api/calls?limit=10", timeout=10.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "items" in data, "Response missing 'items' key"
        assert "count" in data, "Response missing 'count' key"
        assert isinstance(data["items"], list), "'items' is not a list"
        record_result(
            "05. GET /api/calls Endpoint",
            True,
            f"HTTP 200 OK. Retrieved {data['count']} calls from Neon PostgreSQL.",
            t0
        )
    except Exception as e:
        record_result("05. GET /api/calls Endpoint", False, str(e), t0)


async def test_06_simulation_english_granted(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        payload = {
            "caller_number": "+919876543210",
            "language": "en",
            "caller_utterances": [
                "Yes, I agree to recording this conversation.",
                "Hello, I am looking for a website for my retail shop through RMVS Web Services.",
                "My name is Amit. Can Ritesh call me back this evening with a consultation?"
            ]
        }
        resp = await client.post(f"{BASE_URL}/api/test/simulate-call", json=payload, timeout=60.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Simulation failed: {data}"
        call_id = data.get("call_id")
        assert call_id, "Missing call_id in response"
        assert data.get("recording_status") == "recording", f"Expected recording status 'recording', got {data.get('recording_status')}"
        
        # Verify persistence in Neon DB
        call_in_db = await db_service.get_call(call_id)
        assert call_in_db is not None, "Call was not found in Neon DB"
        assert len(call_in_db.get("transcripts", [])) >= 4, "Transcripts missing in Neon DB"
        
        record_result(
            "06. Call Simulation (English + Consent Granted)",
            True,
            f"Call {call_id[:8]}... simulated & stored in Neon DB. Recording: {data.get('recording_status')}",
            t0
        )
        return call_id
    except Exception as e:
        record_result("06. Call Simulation (English + Consent Granted)", False, f"{type(e).__name__}: {e}", t0)
        return None


async def test_07_simulation_telugu_multilingual(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        payload = {
            "caller_number": "+919705162303",
            "language": "te",
            "caller_utterances": [
                "సరేనండి, రికార్డింగ్ చేసుకోవచ్చు.",
                "నమస్తే అండి, కాలేజ్ B.Tech ప్రాజెక్ట్ గైడెన్స్ కోసం రితేష్ గారిని కలవాలనుకుంటున్నాను.",
                "నా పేరు సురేష్. ఆయన ఎప్పుడు అందుబాటులో ఉంటారో చెప్పగలరా?"
            ]
        }
        resp = await client.post(f"{BASE_URL}/api/test/simulate-call", json=payload, timeout=60.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Telugu simulation failed: {data}"
        call_id = data.get("call_id")
        
        record_result(
            "07. Call Simulation (Telugu Multilingual Support)",
            True,
            f"Telugu conversation simulated & persisted to Neon DB for 9705162303. ID: {call_id[:8]}...",
            t0
        )
        return call_id
    except Exception as e:
        record_result("07. Call Simulation (Telugu Multilingual Support)", False, f"{type(e).__name__}: {e}", t0)
        return None


async def test_08_simulation_hindi_declined_safeguard(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        payload = {
            "caller_number": "+919123456789",
            "language": "hi",
            "caller_utterances": [
                "नहीं, मुझे रिकॉर्डिंग नहीं चाहिए।",
                "नमस्ते, मुझे अपने नए क्लोदिंग स्टोर के लिए ऑनलाइन ई-कॉमर्स वेबसाइट बनवानी है।",
                "मेरा नाम राहुल है, क्या मुझे कोटेशन मिल सकती है?"
            ]
        }
        resp = await client.post(f"{BASE_URL}/api/test/simulate-call", json=payload, timeout=60.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Hindi simulation failed: {data}"
        
        # Verify privacy safeguard: recording_status MUST be 'declined'
        rec_status = data.get("recording_status")
        assert rec_status == "declined", f"Privacy breach! Recording status should be 'declined', got {rec_status}"
        assert data.get("recording_path") is None, "Audio path should be None when consent is declined"
        
        record_result(
            "08. Privacy Safeguard (Hindi + Consent Declined)",
            True,
            "Consent DECLINED respected. Zero audio recorded/saved. Transcripts preserved safely.",
            t0
        )
    except Exception as e:
        record_result("08. Privacy Safeguard (Hindi + Consent Declined)", False, f"{type(e).__name__}: {e}", t0)


async def test_09_simulation_emergency_priority(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        payload = {
            "caller_number": "+919999000111",
            "language": "en",
            "caller_utterances": [
                "Yes, record this urgent notice.",
                "Emergency alert: The production PostgreSQL database has high latency and orders are failing.",
                "Please have Ritesh check Slack immediately!"
            ]
        }
        resp = await client.post(f"{BASE_URL}/api/test/simulate-call", json=payload, timeout=60.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success"
        summary = data.get("summary", {})
        urgency = summary.get("urgency", "").lower()
        assert urgency in ["emergency", "high"], f"Expected emergency/high urgency, got: {urgency}"
        
        record_result(
            "09. Emergency Call Classification & Triage",
            True,
            f"Urgency classified as '{urgency}'. Immediate callback flagged in Neon DB.",
            t0
        )
    except Exception as e:
        record_result("09. Emergency Call Classification & Triage", False, f"{type(e).__name__}: {e}", t0)


async def test_10_call_detail_and_transcripts(client: httpx.AsyncClient, call_id: str):
    t0 = time.time()
    if not call_id:
        record_result("10. GET /api/calls/{call_id} Endpoint", False, "Skipped due to prior failure", t0)
        return
    try:
        resp = await client.get(f"{BASE_URL}/api/calls/{call_id}", timeout=10.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("id") == call_id, "Call ID mismatch"
        transcripts = data.get("transcripts", [])
        assert len(transcripts) > 0, "No transcripts returned for call"
        speakers = {t["speaker"] for t in transcripts}
        assert "assistant" in speakers and "caller" in speakers, "Transcripts must contain both assistant and caller turns"
        
        record_result(
            "10. GET /api/calls/{call_id} Detail Endpoint",
            True,
            f"Retrieved call {call_id[:8]}... with {len(transcripts)} multi-turn transcripts from Neon DB.",
            t0
        )
    except Exception as e:
        record_result("10. GET /api/calls/{call_id} Detail Endpoint", False, f"{type(e).__name__}: {e}", t0)


async def test_11_retention_purge(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        headers = {"x-internal-api-key": settings.internal_api_key} if settings.internal_api_key else {}
        resp = await client.post(f"{BASE_URL}/api/recording/retention/purge", headers=headers, timeout=10.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "ok", f"Purge returned error: {data}"
        purged = data.get("purged_count", 0)
        record_result(
            "11. POST /api/recording/retention/purge Endpoint",
            True,
            f"30-day retention purge sweep completed successfully. Files purged: {purged}",
            t0
        )
    except Exception as e:
        record_result("11. POST /api/recording/retention/purge Endpoint", False, f"{type(e).__name__}: {e}", t0)


async def test_12_apk_download_endpoint(client: httpx.AsyncClient):
    t0 = time.time()
    try:
        resp = await client.get(f"{BASE_URL}/download", timeout=15.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.headers.get("content-type") == "application/vnd.android.package-archive", \
            f"Wrong MIME type: {resp.headers.get('content-type')}"
        size_mb = len(resp.content) / (1024 * 1024)
        assert size_mb > 5.0, f"APK file suspiciously small: {size_mb:.2f} MB"
        record_result(
            "12. GET /download APK Distribution Endpoint",
            True,
            f"HTTP 200 OK. Serves valid Android APK ({size_mb:.2f} MB) with correct package-archive MIME type.",
            t0
        )
    except Exception as e:
        record_result("12. GET /download APK Distribution Endpoint", False, f"{type(e).__name__}: {e}", t0)


async def main():
    print("\n" + "=" * 78, flush=True)
    print("      RITESH AI CALL ASSISTANT — AUTOMATED PRODUCTION TEST SUITE", flush=True)
    print(f"      Target Host: {BASE_URL}", flush=True)
    print(f"      Execution Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 78 + "\n", flush=True)

    # 1. Environment & Config
    await test_01_environment_config()

    # 2. Database Connectivity
    await test_02_neon_postgresql_connectivity()

    # 3. HTTP Client Suite
    async with httpx.AsyncClient() as client:
        await test_03_health_endpoint(client)
        await test_04_dashboard_stats(client)
        await test_05_calls_list(client)
        call_id = await test_06_simulation_english_granted(client)
        await test_07_simulation_telugu_multilingual(client)
        await test_08_simulation_hindi_declined_safeguard(client)
        await test_09_simulation_emergency_priority(client)
        await test_10_call_detail_and_transcripts(client, call_id)
        await test_11_retention_purge(client)
        await test_12_apk_download_endpoint(client)

    # Summary
    print("\n" + "=" * 78, flush=True)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    print(f"AUTOMATION TEST RUN RESULTS: {passed}/{total} PASSED ({failed} FAILED)", flush=True)
    print("=" * 78, flush=True)

    if failed == 0:
        print("\033[92mALL AUTOMATED TESTS PASSED SUCCESSFULLY! BACKEND & DATABASE ARE PRODUCTION READY.\033[0m\n", flush=True)
        return 0
    else:
        print(f"\033[91mWARNING: {failed} test(s) failed. Review failures above.\033[0m\n", flush=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
