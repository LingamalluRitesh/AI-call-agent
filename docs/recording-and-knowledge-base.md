# Recording, consent and knowledge-base configuration

## All callers
The intended scope is all callers whose calls reach the configured cloud number. The Android app does not independently seize unanswered SIM calls. Vi no-answer conditional forwarding and Exotel routing must be provisioned and tested.

## Recording policy
The configured preference is audio + transcript + summary. The implementation must remain consent-gated:
1. Disclose that the caller is speaking with an AI assistant.
2. Explain that the call may be recorded and why.
3. Ask for clear affirmative consent before recording.
4. If consent is no/unclear/no response, do not save audio. Continue without recording where permitted.
5. Store recordings in a private Supabase Storage bucket, use short-lived signed URLs, encrypt in transit, and apply the configured retention period (default 30 days).
6. Persist consent value, timestamp, disclosure wording/version and language.
7. Provide deletion and retention jobs; do not log raw audio or signed URLs.

Recording and personal-data obligations depend on the context and applicable law. Obtain appropriate legal advice before production deployment.

## Approved knowledge base
Edit `knowledge_base/profile.json` to add only information Ritesh approves for callers. The starter contains limited professional information and caller-intake prompts. Do not put private addresses, personal contact details, family information, credentials, OTPs or sensitive personal facts in the caller-facing knowledge base.

## Current implementation boundary
The API exposes a consent decision endpoint, but actual audio recording, consent persistence, Supabase Storage upload, transcript generation and retention deletion are integration tasks. Do not claim these are live until implemented and tested.
