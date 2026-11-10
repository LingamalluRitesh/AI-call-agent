"""
Retention Service.
Automates 30-day recording lifecycle and deletion jobs to comply with privacy policy.
"""

import os
from datetime import datetime
from app.services.database import db_service, supabase_client
from app.config import settings


class RetentionService:
    @staticmethod
    async def purge_expired_recordings() -> int:
        """Finds and purges recordings whose 30-day retention period has elapsed."""
        now = datetime.utcnow().isoformat()
        purged_count = 0

        with db_service._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(db_service._format_query("""
            SELECT id, recording_storage_path FROM call_logs
            WHERE recording_status = 'recording'
              AND recording_retention_until IS NOT NULL
              AND recording_retention_until <= ?
            """), (now,))
            expired_calls = cursor.fetchall()

            for call in expired_calls:
                call_id = call["id"]
                storage_path = call["recording_storage_path"]

                # Remove local file if present
                if storage_path and os.path.exists(storage_path):
                    try:
                        os.remove(storage_path)
                    except Exception as e:
                        print(f"[RetentionService] Local delete failed: {e}")

                # Remove from Supabase Storage if present
                if supabase_client and storage_path and "/" in storage_path:
                    try:
                        parts = storage_path.split("/", 1)
                        supabase_client.storage.from_(parts[0]).remove([parts[1]])
                    except Exception as e:
                        print(f"[RetentionService] Supabase Storage delete failed: {e}")

                cursor.execute(db_service._format_query("""
                UPDATE call_logs
                SET recording_status = 'deleted', recording_storage_path = NULL
                WHERE id = ?
                """), (call_id,))
                purged_count += 1

            conn.commit()

        if purged_count > 0:
            print(f"[RetentionService] Purged {purged_count} expired call recordings (30-day retention).")

        return purged_count


retention_service = RetentionService()
