"""
Notification Service.
Dispatches Android push notifications (via Firebase Cloud Messaging) for incoming call summaries and urgent alerts.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings


class NotificationService:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    async def notify_call_summary(
        self,
        call_id: str,
        caller_number: str,
        caller_name: Optional[str],
        urgency: str,
        summary: str,
        callback_required: bool
    ) -> bool:
        title = f"[{urgency.upper()}] Call from {caller_name or caller_number}"
        body = f"{summary[:140]}..." if len(summary) > 140 else summary

        record = {
            "call_id": call_id,
            "title": title,
            "body": body,
            "urgency": urgency,
            "caller_number": caller_number,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "delivered"
        }
        self.history.append(record)
        print(f"[NotificationService] [ALERT] Dispatched Android Alert: {title}")
        print(f"                      Body: {body}")

        # Real FCM push if server key and recipient token are configured
        if settings.fcm_server_key and settings.ritesh_android_fcm_token:
            url = "https://fcm.googleapis.com/fcm/send"
            headers = {
                "Authorization": f"key={settings.fcm_server_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "to": settings.ritesh_android_fcm_token,
                "priority": "high",
                "notification": {
                    "title": title,
                    "body": body,
                    "sound": "default"
                },
                "data": {
                    "call_id": call_id,
                    "urgency": urgency,
                    "callback_required": str(callback_required)
                }
            }
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    return resp.status_code == 200
            except Exception as e:
                print(f"[NotificationService] FCM post failed: {e}")
                return False

        return True


notification_service = NotificationService()
