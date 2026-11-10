import os
import json
from pathlib import Path

DEFAULT_KB = {
    "owner": {
        "display_name": "Ritesh",
        "assistant_identity": "Ritesh's AI call assistant",
        "public_intro": "Ritesh works in software and AI-related development."
    },
    "professional": {
        "company": "RMVS Web Services",
        "role": "Founder",
        "services": [
            "Website design and development",
            "Single-page and multi-page business websites",
            "Web services for small and large businesses",
            "Academic B.Tech and M.Tech project enquiries"
        ],
        "pricing_policy": "Do not quote or negotiate a final price. Ask for requirements and tell the caller Ritesh will confirm the estimate.",
        "project_intake_questions": [
            "What type of website or project do you need?",
            "Is this for a personal, academic, or business requirement?",
            "What features do you need?",
            "When do you need it?",
            "What is your preferred callback time?"
        ]
    },
    "privacy_rules": [
        "Do not disclose private home address, personal phone numbers, account details, passwords, OTPs, or private family information.",
        "Do not invent availability, prices, delivery dates, qualifications, client references, or project status.",
        "If information is not listed here, say you will ask Ritesh to confirm."
    ],
    "handoff": {
        "default_message": "Thank you. I will pass your message and details to Ritesh.",
        "urgent_message": "I will mark this as urgent and notify Ritesh."
    }
}

def get_kb_path() -> Path:
    """Finds profile.json across local dev, Docker container, or cloud deployment paths."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / "knowledge_base" / "profile.json",        # backend/app/knowledge_base/profile.json
        here.parent.parent.parent / "knowledge_base" / "profile.json", # backend/knowledge_base/profile.json
        Path.cwd() / "knowledge_base" / "profile.json",                # cwd / knowledge_base
        Path.cwd() / "backend" / "knowledge_base" / "profile.json",
        Path("/app/knowledge_base/profile.json"),
        Path("/app/app/knowledge_base/profile.json")
    ]
    # Check parent directories safely
    for p in here.parents:
        cand = p / "knowledge_base" / "profile.json"
        if cand not in candidates:
            candidates.append(cand)

    for c in candidates:
        try:
            if c.is_file():
                return c
        except Exception:
            pass

    return here.parent.parent / "knowledge_base" / "profile.json"

def load_knowledge_base() -> dict:
    path = get_kb_path()
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
    except Exception as e:
        print(f"[KnowledgeBase] Notice: Could not read {path}: {e}. Using embedded profile.", flush=True)
    return DEFAULT_KB

def build_context() -> str:
    data = load_knowledge_base()
    return json.dumps(data, ensure_ascii=False, indent=2)
