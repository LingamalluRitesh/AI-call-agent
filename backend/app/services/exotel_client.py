"""
Exotel Telephony Client.
Initiates outbound test calls and bridges callers to the AgentStream flow.
"""

from typing import Dict, Any, Optional
import httpx
from app.config import settings


class ExotelClient:
    def __init__(self):
        self.account_sid = settings.exotel_account_sid
        self.api_key = settings.exotel_api_key
        self.api_token = settings.exotel_api_token
        self.exophone = settings.exotel_exophone

    def is_configured(self) -> bool:
        return bool(
            self.account_sid and not self.account_sid.startswith("your_") and
            self.api_key and not self.api_key.startswith("your_") and
            self.api_token and not self.api_token.startswith("your_") and
            self.exophone and not self.exophone.startswith("your_")
        )

    async def initiate_call(
        self,
        to_number: str,
        custom_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connects an outbound call from the ExoPhone to the destination number.
        When answered, Exotel executes the Voicebot / AgentStream flow.
        """
        if not self.is_configured():
            return {
                "success": False,
                "reason": "Exotel credentials are not yet configured in backend/.env (EXOTEL_ACCOUNT_SID, EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_EXOPHONE).",
                "simulated": True
            }

        url = f"https://api.exotel.com/v1/Accounts/{self.account_sid}/Calls/connect.json"
        auth = (self.api_key, self.api_token)

        # Ensure E.164 format
        normalized_number = to_number if to_number.startswith("+") else f"+91{to_number.lstrip('0')}"

        data = {
            "From": normalized_number,
            "To": self.exophone,
            "CallerId": self.exophone,
            "CallType": "trans"
        }
        if custom_field:
            data["CustomField"] = custom_field

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, auth=auth, data=data)
                if resp.status_code in [200, 201]:
                    return {
                        "success": True,
                        "data": resp.json(),
                        "call_sid": resp.json().get("Call", {}).get("Sid")
                    }
                else:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": resp.text
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


exotel_client = ExotelClient()
