# Vi + Exotel setup

Call path: Caller -> Vi mobile -> Vi no-answer forwarding -> Exotel ExoPhone
-> inbound Voicebot/AgentStream flow -> public WSS backend.

Vi's published help article lists:
- Enable no-answer forwarding: `*61*<destination-number>#`
- Check status: `*#61#`
- Disable no-answer forwarding: `##61#`

Confirm with Vi that forwarding to your Exotel number is supported, timeout/billing,
and caller-ID presentation. Do not assume original caller ID is preserved. Test
from another phone. Avoid unconditional forwarding.

Exotel AgentStream documentation describes bidirectional Voicebot streaming over
WebSocket with mono PCM16 audio; its defaults and exact event contract must be
checked against your account and current docs. Complete KYC and confirm inbound
AgentStream availability before relying on it.
