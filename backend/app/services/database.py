"""
Database & Storage Service.
Supports:
1. Neon PostgreSQL Cloud Database (via psycopg2) when NEON_DATABASE_URL is provided.
2. Supabase (PostgreSQL + Private Storage Bucket) when credentials are provided.
3. Local SQLite + Local File Storage fallback for instant offline/developer use.
"""

import os
import uuid
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.config import settings

# Initialize Supabase client if configured
supabase_client = None
if settings.supabase_url and settings.supabase_service_role_key:
    try:
        from supabase import create_client
        supabase_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        print("[Database] Connected to Supabase Cloud.", flush=True)
    except Exception as e:
        print(f"[Database] Warning: Supabase client init failed: {e}. Falling back.", flush=True)


class DatabaseService:
    def __init__(self):
        self.neon_url = (settings.neon_database_url or settings.database_url or "").strip()
        self.sqlite_db_path = os.path.join(settings.local_data_dir, "call_assistant.db")
        self.is_neon = False
        self._neon_pool = None

        if self.neon_url:
            self.is_neon = self._init_neon()
        
        if not self.is_neon:
            print("[Database] Using local SQLite database at:", self.sqlite_db_path, flush=True)
            self._init_sqlite()

    @property
    def use_neon(self) -> bool:
        return self.is_neon

    @contextmanager
    def _get_connection(self):
        """Unified high-performance pooled connection context manager."""
        if self.is_neon and self._neon_pool:
            conn = self._neon_pool.getconn()
            try:
                yield conn
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    self._neon_pool.putconn(conn)
                except Exception:
                    pass
        else:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def _format_query(self, query: str) -> str:
        """Adapts SQL parameter placeholders between SQLite (?) and PostgreSQL (%s)."""
        if self.is_neon:
            return query.replace("?", "%s")
        return query

    def _init_neon(self) -> bool:
        """Initializes tables on Neon PostgreSQL cloud database and creates persistent connection pool."""
        try:
            import psycopg2.pool
            from psycopg2.extras import RealDictCursor

            dsn = self.neon_url
            if "sslmode=" not in dsn:
                sep = "&" if "?" in dsn else "?"
                dsn = f"{dsn}{sep}sslmode=require"

            self._neon_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=dsn,
                cursor_factory=RealDictCursor,
                connect_timeout=10
            )
            conn = self._neon_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    provider_call_id TEXT UNIQUE,
                    caller_name TEXT,
                    caller_number TEXT,
                    detected_language TEXT,
                    call_reason TEXT,
                    urgency TEXT DEFAULT 'normal',
                    summary TEXT,
                    callback_required INTEGER DEFAULT 1,
                    preferred_callback_time TEXT,
                    status TEXT DEFAULT 'received',
                    recording_status TEXT DEFAULT 'not_started',
                    recording_storage_path TEXT,
                    recording_retention_until TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    created_at TEXT
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_transcripts (
                    id TEXT PRIMARY KEY,
                    call_id TEXT NOT NULL REFERENCES call_logs(id) ON DELETE CASCADE,
                    speaker TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT
                );
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_recording_consents (
                    id TEXT PRIMARY KEY,
                    call_id TEXT NOT NULL REFERENCES call_logs(id) ON DELETE CASCADE,
                    consent TEXT NOT NULL,
                    disclosure_text TEXT NOT NULL,
                    disclosure_language TEXT,
                    captured_at TEXT
                );
                """)
            conn.commit()
            print("[Database] [OK] Successfully connected to Neon PostgreSQL Cloud Database!", flush=True)
            self._auto_migrate_sqlite_to_neon()
            return True
        except Exception as e:
            print(f"[Database] [ALERT] Failed to connect to Neon PostgreSQL: {e}", flush=True)
            print("[Database] Falling back to local SQLite.", flush=True)
            return False
        finally:
            if conn and self._neon_pool:
                try:
                    self._neon_pool.putconn(conn)
                except Exception:
                    pass

    def _auto_migrate_sqlite_to_neon(self):
        """Automatically migrates existing SQLite call records to Neon if Neon is empty."""
        neon_conn = None
        try:
            if not os.path.exists(self.sqlite_db_path) or not self._neon_pool:
                return

            neon_conn = self._neon_pool.getconn()
            with neon_conn.cursor() as n_cur:
                n_cur.execute("SELECT COUNT(*) as cnt FROM call_logs")
                neon_count = n_cur.fetchone()["cnt"]

                if neon_count > 0:
                    print(f"[Database] Neon PostgreSQL currently holds {neon_count} calls.", flush=True)
                    return

                # Read from local SQLite
                sq_conn = sqlite3.connect(self.sqlite_db_path)
                sq_conn.row_factory = sqlite3.Row
                sq_cur = sq_conn.cursor()

                sq_cur.execute("SELECT * FROM call_logs")
                calls = [dict(r) for r in sq_cur.fetchall()]
                if not calls:
                    sq_conn.close()
                    return

                print(f"[Database] Migrating {len(calls)} calls from SQLite to Neon PostgreSQL...", flush=True)

                for c in calls:
                    cols = list(c.keys())
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    insert_query = f"INSERT INTO call_logs ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
                    n_cur.execute(insert_query, list(c.values()))

                sq_cur.execute("SELECT * FROM call_transcripts")
                transcripts = [dict(r) for r in sq_cur.fetchall()]
                for t in transcripts:
                    cols = list(t.keys())
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    n_cur.execute(f"INSERT INTO call_transcripts ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", list(t.values()))

                sq_cur.execute("SELECT * FROM call_recording_consents")
                consents = [dict(r) for r in sq_cur.fetchall()]
                for cs in consents:
                    cols = list(cs.keys())
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join(cols)
                    n_cur.execute(f"INSERT INTO call_recording_consents ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING", list(cs.values()))

                sq_conn.close()
            neon_conn.commit()
            print(f"[Database] [OK] Successfully migrated {len(calls)} calls to Neon PostgreSQL!", flush=True)
        except Exception as e:
            print(f"[Database] Migration notice: {e}", flush=True)
        finally:
            if neon_conn and self._neon_pool:
                try:
                    self._neon_pool.putconn(neon_conn)
                except Exception:
                    pass

    def _init_sqlite(self):
        """Initializes local SQLite tables."""
        with sqlite3.connect(self.sqlite_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                provider_call_id TEXT UNIQUE,
                caller_name TEXT,
                caller_number TEXT,
                detected_language TEXT,
                call_reason TEXT,
                urgency TEXT DEFAULT 'normal',
                summary TEXT,
                callback_required INTEGER DEFAULT 1,
                preferred_callback_time TEXT,
                status TEXT DEFAULT 'received',
                recording_status TEXT DEFAULT 'not_started',
                recording_storage_path TEXT,
                recording_retention_until TEXT,
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_transcripts (
                id TEXT PRIMARY KEY,
                call_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (call_id) REFERENCES call_logs(id) ON DELETE CASCADE
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS call_recording_consents (
                id TEXT PRIMARY KEY,
                call_id TEXT NOT NULL,
                consent TEXT NOT NULL,
                disclosure_text TEXT NOT NULL,
                disclosure_language TEXT,
                captured_at TEXT,
                FOREIGN KEY (call_id) REFERENCES call_logs(id) ON DELETE CASCADE
            )
            """)
            conn.commit()

    async def create_call(self, provider_call_id: str, caller_number: str = "Unknown") -> str:
        call_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        retention_until = (datetime.utcnow() + timedelta(days=settings.recording_retention_days)).isoformat()

        if supabase_client:
            try:
                data = {
                    "id": call_id,
                    "user_id": str(uuid.uuid4()),
                    "provider_call_id": provider_call_id,
                    "caller_number": caller_number,
                    "status": "in_progress",
                    "recording_status": "awaiting_consent",
                    "recording_retention_until": retention_until,
                    "started_at": now
                }
                supabase_client.table("call_logs").insert(data).execute()
                return call_id
            except Exception as e:
                print(f"[Database] Supabase insert failed: {e}. Falling back.", flush=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = self._format_query("""
            INSERT INTO call_logs (id, provider_call_id, caller_number, status, recording_status, recording_retention_until, started_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """)
            cursor.execute(q, (call_id, provider_call_id, caller_number, "in_progress", "awaiting_consent", retention_until, now, now))

        return call_id

    async def add_transcript(self, call_id: str, speaker: str, content: str):
        t_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        if supabase_client:
            try:
                supabase_client.table("call_transcripts").insert({
                    "id": t_id,
                    "call_id": call_id,
                    "speaker": speaker,
                    "content": content,
                    "created_at": now
                }).execute()
                return
            except Exception as e:
                print(f"[Database] Supabase transcript insert failed: {e}", flush=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = self._format_query("""
            INSERT INTO call_transcripts (id, call_id, speaker, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """)
            cursor.execute(q, (t_id, call_id, speaker, content, now))

    async def record_consent(self, call_id: str, consent: str, disclosure_text: str, disclosure_language: str = "en"):
        c_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        recording_status = "recording" if consent == "yes" else "declined"

        if supabase_client:
            try:
                supabase_client.table("call_recording_consents").insert({
                    "id": c_id,
                    "call_id": call_id,
                    "consent": consent,
                    "disclosure_text": disclosure_text,
                    "disclosure_language": disclosure_language,
                    "captured_at": now
                }).execute()
                supabase_client.table("call_logs").update({
                    "recording_status": recording_status
                }).eq("id", call_id).execute()
                return
            except Exception as e:
                print(f"[Database] Supabase consent insert failed: {e}", flush=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            q1 = self._format_query("""
            INSERT INTO call_recording_consents (id, call_id, consent, disclosure_text, disclosure_language, captured_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """)
            cursor.execute(q1, (c_id, call_id, consent, disclosure_text, disclosure_language, now))

            q2 = self._format_query("UPDATE call_logs SET recording_status = ? WHERE id = ?")
            cursor.execute(q2, (recording_status, call_id))

    async def finalize_call(
        self,
        call_id: str,
        caller_name: Optional[str] = None,
        detected_language: Optional[str] = None,
        call_reason: Optional[str] = None,
        urgency: str = "normal",
        summary: Optional[str] = None,
        callback_required: bool = True,
        preferred_callback_time: Optional[str] = None,
        recording_storage_path: Optional[str] = None,
        recording_status: Optional[str] = None
    ):
        now = datetime.utcnow().isoformat()

        fields = {
            "status": "completed",
            "caller_name": caller_name,
            "detected_language": detected_language,
            "call_reason": call_reason,
            "urgency": urgency,
            "summary": summary,
            "callback_required": 1 if callback_required else 0,
            "preferred_callback_time": preferred_callback_time,
            "ended_at": now
        }
        if recording_storage_path:
            fields["recording_storage_path"] = recording_storage_path
        if recording_status:
            fields["recording_status"] = recording_status

        if supabase_client:
            try:
                supa_fields = {k: (bool(v) if k == "callback_required" else v) for k, v in fields.items()}
                supabase_client.table("call_logs").update(supa_fields).eq("id", call_id).execute()
                return
            except Exception as e:
                print(f"[Database] Supabase finalize_call update failed: {e}", flush=True)

        set_clauses = [f"{k} = ?" for k in fields.keys()]
        values = list(fields.values()) + [call_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = self._format_query(f"UPDATE call_logs SET {', '.join(set_clauses)} WHERE id = ?")
            cursor.execute(q, values)

    async def save_recording(self, call_id: str, wav_bytes: bytes) -> Optional[str]:
        filename = f"{call_id}.wav"

        if supabase_client:
            try:
                bucket = settings.supabase_recordings_bucket
                res = supabase_client.storage.from_(bucket).upload(filename, wav_bytes, {"content-type": "audio/wav"})
                storage_path = f"{bucket}/{filename}"
                print(f"[Database] Uploaded recording to Supabase Storage: {storage_path}", flush=True)
                return storage_path
            except Exception as e:
                print(f"[Database] Supabase storage upload failed: {e}. Saving locally.", flush=True)

        local_path = os.path.join(settings.local_recordings_dir, filename)
        with open(local_path, "wb") as f:
            f.write(wav_bytes)
        print(f"[Database] Saved recording locally: {local_path}", flush=True)
        return local_path

    async def list_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        if supabase_client:
            try:
                resp = supabase_client.table("call_logs").select("*").order("created_at", desc=True).limit(limit).execute()
                return resp.data or []
            except Exception as e:
                print(f"[Database] Supabase list_calls failed: {e}", flush=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = self._format_query("SELECT * FROM call_logs ORDER BY created_at DESC LIMIT ?")
            cursor.execute(q, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            q_call = self._format_query("SELECT * FROM call_logs WHERE id = ? OR provider_call_id = ?")
            cursor.execute(q_call, (call_id, call_id))
            row = cursor.fetchone()
            if not row:
                return None
            call = dict(row)

            q_tx = self._format_query("SELECT * FROM call_transcripts WHERE call_id = ? ORDER BY created_at ASC")
            cursor.execute(q_tx, (call["id"],))
            call["transcripts"] = [dict(t) for t in cursor.fetchall()]

            q_cs = self._format_query("SELECT * FROM call_recording_consents WHERE call_id = ?")
            cursor.execute(q_cs, (call["id"],))
            call["consents"] = [dict(c) for c in cursor.fetchall()]

            return call

    async def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = """
            SELECT 
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN callback_required = 1 AND status = 'completed' THEN 1 ELSE 0 END), 0) as pending,
                COALESCE(SUM(CASE WHEN recording_status = 'recording' THEN 1 ELSE 0 END), 0) as recorded,
                COALESCE(SUM(CASE WHEN urgency IN ('emergency', 'high') THEN 1 ELSE 0 END), 0) as emergency
            FROM call_logs;
            """
            cursor.execute(q)
            row = cursor.fetchone()
            total = int(row["total"] if isinstance(row, dict) else row[0])
            pending = int(row["pending"] if isinstance(row, dict) else row[1])
            recorded = int(row["recorded"] if isinstance(row, dict) else row[2])
            emergency = int(row["emergency"] if isinstance(row, dict) else row[3])

            return {
                "total_calls": total,
                "calls_today": total,
                "unread_messages": pending,
                "recorded_calls": recorded,
                "emergency_calls": emergency,
                "assistant_status": "ready",
                "database_engine": "neon_postgresql" if self.is_neon else "local_sqlite"
            }


db_service = DatabaseService()
