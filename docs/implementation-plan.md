# Implementation plan

1. Run FastAPI and verify `/health`.
2. Create Supabase project; apply schema; review RLS.
3. Provision Exotel test number and validate inbound AgentStream events.
4. Implement provider authentication, per-call session state and event deduplication.
5. Add multilingual streaming STT and language detection.
6. Add receptionist conversation state and structured call-note extraction.
7. Add verified ElevenLabs streaming voice and telephony codec conversion.
8. Persist call summary/transcript subject to notice, consent and retention rules.
9. Add Android authentication, call list, details and push notifications.
10. Test full Vi forwarding path, then deploy with HTTPS/WSS, secret storage and monitoring.
