import json
from pathlib import Path

KB_PATH = Path(__file__).resolve().parents[3] / "knowledge_base" / "profile.json"

def load_knowledge_base() -> dict:
    with KB_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def build_context() -> str:
    data = load_knowledge_base()
    return json.dumps(data, ensure_ascii=False, indent=2)
