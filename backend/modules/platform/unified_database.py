"""
unified_database.py - Unified SQLite Database for ANT
Replaces scattered JSON files with single SQLite database
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
import threading


class UnifiedDatabase:
    """
    Single SQLite database for all ANT data.
    Local-first SQLite approach.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return

        if db_path is None:
            # Default location: user data directory
            data_dir = Path.home() / ".ant" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "ant_database.db"

        self.db_path = str(db_path)
        self._local = threading.local()
        self._initialized = True

        # Initialize database
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def _init_database(self):
        """Initialize database schema"""
        with self._transaction() as conn:
            cursor = conn.cursor()

            # Conversations table (replaces JSON files)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pinned BOOLEAN DEFAULT FALSE,
                    archived BOOLEAN DEFAULT FALSE,
                    category TEXT DEFAULT 'general',
                    tags TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    messages TEXT  -- JSON array of messages
                )
            """)

            # Settings table (replaces config.json)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    category TEXT DEFAULT 'general',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # API Keys table (replaces secure-api-keys.json)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    provider TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    encrypted BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Analytics table (replaces analytics JSON files)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_data TEXT,  -- JSON
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    user_id TEXT
                )
            """)

            # Documents table (for RAG)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT,
                    content TEXT,
                    file_hash TEXT UNIQUE,
                    file_size INTEGER,
                    mime_type TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    metadata TEXT  -- JSON
                )
            """)

            # Document chunks for RAG
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,  -- JSON array
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Voice models table (replaces voice_models JSON)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voice_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    model_path TEXT,
                    config TEXT,  -- JSON
                    is_custom BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Jobs table (for job tracker)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    position TEXT NOT NULL,
                    status TEXT DEFAULT 'applied',
                    applied_date TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    url TEXT,
                    notes TEXT,
                    salary TEXT,
                    location TEXT,
                    tags TEXT,  -- JSON array
                    metadata TEXT  -- JSON
                )
            """)

            # Interview sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    type TEXT DEFAULT 'mock',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    duration INTEGER,  -- seconds
                    questions TEXT,  -- JSON array
                    responses TEXT,  -- JSON array
                    feedback TEXT,  -- JSON object
                    score INTEGER,
                    metadata TEXT  -- JSON
                )
            """)

            # Cache table (replaces memory cache)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_pinned ON conversations(pinned)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")

            conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════════
    # CONVERSATIONS (replaces conversation JSON files)
    # ═══════════════════════════════════════════════════════════════════════════════

    def save_conversation(self, conversation: Dict[str, Any]) -> bool:
        """Save or update a conversation"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO conversations
                    (id, title, created_at, updated_at, pinned, archived, category, tags, metadata, messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation.get('id'),
                    conversation.get('title', 'Untitled'),
                    conversation.get('created_at', datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    conversation.get('pinned', False),
                    conversation.get('archived', False),
                    conversation.get('category', 'general'),
                    json.dumps(conversation.get('tags', [])),
                    json.dumps(conversation.get('metadata', {})),
                    json.dumps(conversation.get('messages', []))
                ))
            return True
        except Exception as e:
            print(f"[Database] Failed to save conversation: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            print(f"[Database] Failed to get conversation: {e}")
            return None

    def list_conversations(
        self,
        category: Optional[str] = None,
        pinned_only: bool = False,
        archived: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations with optional filters"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM conversations WHERE archived = ?"
                params = [archived]

                if category:
                    query += " AND category = ?"
                    params.append(category)

                if pinned_only:
                    query += " AND pinned = TRUE"

                query += " ORDER BY pinned DESC, updated_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"[Database] Failed to list conversations: {e}")
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Failed to delete conversation: {e}")
            return False

    def pin_conversation(self, conversation_id: str, pinned: bool = True) -> bool:
        """Pin or unpin a conversation"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversations SET pinned = ?, updated_at = ? WHERE id = ?",
                    (pinned, datetime.now().isoformat(), conversation_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Failed to pin conversation: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════════
    # SETTINGS (replaces config.json)
    # ═══════════════════════════════════════════════════════════════════════════════

    def set_setting(self, key: str, value: Any, category: str = 'general') -> bool:
        """Save a setting"""
        try:
            value_type = type(value).__name__
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)

            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO settings (key, value, value_type, category, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, value, value_type, category, datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"[Database] Failed to set setting: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, value_type FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    value, value_type = row['value'], row['value_type']
                    return self._cast_value(value, value_type)
                return default
        except Exception as e:
            print(f"[Database] Failed to get setting: {e}")
            return default

    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Get all settings in a category"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, value_type FROM settings WHERE category = ?", (category,))
                rows = cursor.fetchall()
                return {row['key']: self._cast_value(row['value'], row['value_type']) for row in rows}
        except Exception as e:
            print(f"[Database] Failed to get settings: {e}")
            return {}

    def delete_setting(self, key: str) -> bool:
        """Delete a setting"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Failed to delete setting: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════════
    # API KEYS (replaces secure-api-keys.json)
    # ═══════════════════════════════════════════════════════════════════════════════

    def save_api_key(self, provider: str, api_key: str, encrypted: bool = True) -> bool:
        """Save an API key"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO api_keys (provider, api_key, encrypted, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (provider, api_key, encrypted, datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"[Database] Failed to save API key: {e}")
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get an API key"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT api_key FROM api_keys WHERE provider = ?", (provider,))
                row = cursor.fetchone()
                return row['api_key'] if row else None
        except Exception as e:
            print(f"[Database] Failed to get API key: {e}")
            return None

    def list_api_keys(self) -> List[str]:
        """List all stored API key providers"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT provider FROM api_keys")
                rows = cursor.fetchall()
                return [row['provider'] for row in rows]
        except Exception as e:
            print(f"[Database] Failed to list API keys: {e}")
            return []

    def delete_api_key(self, provider: str) -> bool:
        """Delete an API key"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM api_keys WHERE provider = ?", (provider,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Failed to delete API key: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════════
    # ANALYTICS (replaces analytics JSON files)
    # ═══════════════════════════════════════════════════════════════════════════════

    def record_analytics_event(self, event_type: str, event_data: Dict[str, Any],
                               session_id: Optional[str] = None,
                               user_id: Optional[str] = None) -> bool:
        """Record an analytics event"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO analytics (event_type, event_data, session_id, user_id)
                    VALUES (?, ?, ?, ?)
                """, (event_type, json.dumps(event_data), session_id, user_id))
            return True
        except Exception as e:
            print(f"[Database] Failed to record analytics: {e}")
            return False

    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for the last N days"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM analytics
                    WHERE timestamp > datetime('now', '-{} days')
                    GROUP BY event_type
                """.format(days))
                rows = cursor.fetchall()

                summary = {row['event_type']: row['count'] for row in rows}
                summary['total_events'] = sum(summary.values())
                summary['period_days'] = days
                return summary
        except Exception as e:
            print(f"[Database] Failed to get analytics: {e}")
            return {}

    def get_analytics_events(self, event_type: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Get analytics events with optional filtering"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                if event_type:
                    cursor.execute(
                        "SELECT * FROM analytics WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                        (event_type, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM analytics ORDER BY timestamp DESC LIMIT ?",
                        (limit,)
                    )
                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"[Database] Failed to get analytics events: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════════
    # CACHE (replaces in-memory cache)
    # ═══════════════════════════════════════════════════════════════════════════════

    def cache_set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set a cached value with optional TTL"""
        try:
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now().timestamp() + ttl_seconds

            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache (key, value, expires_at)
                    VALUES (?, ?, ?)
                """, (key, json.dumps(value), expires_at))
            return True
        except Exception as e:
            print(f"[Database] Failed to set cache: {e}")
            return False

    def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value, returns None if expired"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()

                if not row:
                    return None

                # Check expiration
                if row['expires_at'] and datetime.now().timestamp() > row['expires_at']:
                    cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                return json.loads(row['value'])
        except Exception as e:
            print(f"[Database] Failed to get cache: {e}")
            return None

    def cache_delete(self, key: str) -> bool:
        """Delete a cached value"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Failed to delete cache: {e}")
            return False

    def cache_clear_expired(self) -> int:
        """Clear expired cache entries, returns count cleared"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                    (datetime.now().timestamp(),)
                )
                return cursor.rowcount
        except Exception as e:
            print(f"[Database] Failed to clear expired cache: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════════════════
    # DOCUMENTS (for RAG)
    # ═══════════════════════════════════════════════════════════════════════════════

    def save_document(self, document: Dict[str, Any]) -> bool:
        """Save a document"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO documents
                    (id, filename, file_path, content, file_hash, file_size, mime_type, metadata, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.get('id'),
                    document.get('filename'),
                    document.get('file_path'),
                    document.get('content'),
                    document.get('file_hash'),
                    document.get('file_size'),
                    document.get('mime_type'),
                    json.dumps(document.get('metadata', {})),
                    document.get('processed', False)
                ))
            return True
        except Exception as e:
            print(f"[Database] Failed to save document: {e}")
            return False

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
        except Exception as e:
            print(f"[Database] Failed to get document: {e}")
            return None

    def list_documents(self, processed_only: bool = False) -> List[Dict[str, Any]]:
        """List all documents"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                if processed_only:
                    cursor.execute("SELECT * FROM documents WHERE processed = TRUE ORDER BY uploaded_at DESC")
                else:
                    cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"[Database] Failed to list documents: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════════

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to dictionary"""
        result = dict(row)
        # Parse JSON fields
        json_fields = ['tags', 'metadata', 'messages', 'event_data', 'questions',
                       'responses', 'feedback', 'config', 'embedding']
        for field in json_fields:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except:
                    pass
        return result

    def _cast_value(self, value: str, value_type: str) -> Any:
        """Cast a value to its proper type"""
        if value_type == 'bool':
            return value.lower() == 'true'
        elif value_type == 'int':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type in ('dict', 'list'):
            try:
                return json.loads(value)
            except:
                return value
        return value

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                stats = {}

                tables = ['conversations', 'settings', 'api_keys', 'analytics',
                         'documents', 'voice_models', 'jobs', 'interview_sessions', 'cache']

                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        stats[table] = cursor.fetchone()[0]
                    except:
                        stats[table] = 0

                # Database file size
                if os.path.exists(self.db_path):
                    stats['database_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                else:
                    stats['database_size_mb'] = 0

                return stats
        except Exception as e:
            print(f"[Database] Failed to get stats: {e}")
            return {}

    def vacuum(self) -> bool:
        """Optimize database (VACUUM)"""
        try:
            with self._transaction() as conn:
                conn.execute("VACUUM")
            return True
        except Exception as e:
            print(f"[Database] Vacuum failed: {e}")
            return False

    def backup(self, backup_path: str) -> bool:
        """Create a database backup"""
        try:
            with self._transaction() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
            return True
        except Exception as e:
            print(f"[Database] Backup failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Singleton instance
db = UnifiedDatabase()


# Convenience functions for direct import
def get_db() -> UnifiedDatabase:
    """Get the unified database instance"""
    return db


__all__ = ['UnifiedDatabase', 'db', 'get_db']
