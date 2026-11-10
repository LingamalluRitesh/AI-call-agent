from pydantic import BaseModel, Field

class CallSummary(BaseModel):
    caller_name: str | None = None
    caller_number: str | None = None
    detected_language: str | None = None
    call_reason: str | None = None
    urgency: str = Field(default="normal", pattern="^(low|normal|high|emergency)$")
    summary: str
    callback_required: bool = True
