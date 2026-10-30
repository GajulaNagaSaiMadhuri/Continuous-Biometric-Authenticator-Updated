import sqlite3
from datetime import datetime
import os
try:
    from config import DATABASE, EMBEDDINGS_DIR
except ImportError:
    DATABASE = "authentication.db"
    EMBEDDINGS_DIR = "data/embeddings"


def get_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DATABASE)
    return conn


def create_database():
    """Creates all required tables while preserving existing schemas."""
    connection = get_connection()
    cursor = connection.cursor()

    # 1. Existing authentication_logs table (preserved 100%)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authentication_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            similarity REAL,
            failed_attempts INTEGER
        )
    """)

    # Check if username column exists in authentication_logs, if not add it non-destructively
    cursor.execute("PRAGMA table_info(authentication_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    if "username" not in columns:
        try:
            cursor.execute("ALTER TABLE authentication_logs ADD COLUMN username TEXT DEFAULT 'System'")
        except Exception:
            pass

    # 2. Multi-user accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'Authorized User',
            feature_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def log_authentication(status, similarity, failed_attempts, username="Registered User"):
    """
    Logs an authentication attempt. Fully backward compatible with:
    log_authentication(status, similarity, failed_attempts)
    """
    connection = get_connection()
    cursor = connection.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if username column exists
    cursor.execute("PRAGMA table_info(authentication_logs)")
    columns = [col[1] for col in cursor.fetchall()]

    if "username" in columns:
        cursor.execute("""
            INSERT INTO authentication_logs
            (timestamp, status, similarity, failed_attempts, username)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            status,
            float(similarity) if similarity is not None else 0.0,
            int(failed_attempts),
            str(username) if username else "Registered User"
        ))
    else:
        cursor.execute("""
            INSERT INTO authentication_logs
            (timestamp, status, similarity, failed_attempts)
            VALUES (?, ?, ?, ?)
        """, (
            timestamp,
            status,
            float(similarity) if similarity is not None else 0.0,
            int(failed_attempts)
        ))

    connection.commit()
    connection.close()


def show_logs():
    """
    Returns records matching exact signature used by dashboard.py & view_logs.py.
    Columns: (id, timestamp, status, similarity, failed_attempts)
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, timestamp, status,
               similarity, failed_attempts
        FROM authentication_logs
        ORDER BY id DESC
    """)

    records = cursor.fetchall()
    connection.close()
    return records


def get_logs_extended(limit=100):
    """Returns detailed logs for the modern web dashboard."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(authentication_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    has_username = "username" in columns

    if has_username:
        cursor.execute(f"""
            SELECT id, timestamp, status, similarity, failed_attempts, username
            FROM authentication_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
    else:
        cursor.execute(f"""
            SELECT id, timestamp, status, similarity, failed_attempts, 'Registered User' as username
            FROM authentication_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    records = cursor.fetchall()
    connection.close()

    logs = []
    for r in records:
        logs.append({
            "id": r[0],
            "timestamp": r[1],
            "status": r[2],
            "similarity": round(float(r[3]), 4) if r[3] is not None else 0.0,
            "failed_attempts": r[4],
            "username": r[5] if len(r) > 5 and r[5] else "Registered User"
        })
    return logs


# ==========================================
# MULTI-USER MANAGEMENT FUNCTIONS
# ==========================================

def add_user(username, full_name, email, feature_path, role="Authorized User"):
    """Registers a new user in the database."""
    connection = get_connection()
    cursor = connection.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
            INSERT INTO users (username, full_name, email, role, feature_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username.strip().lower(), full_name.strip(), email.strip() if email else "", role, feature_path, timestamp))
        connection.commit()
        user_id = cursor.lastrowid
        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, str(e)
    finally:
        connection.close()


def get_user_by_username(username):
    """Retrieves a user by their unique username."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, full_name, email, role, feature_path, created_at
        FROM users
        WHERE LOWER(username) = LOWER(?)
    """, (username.strip(),))

    row = cursor.fetchone()
    connection.close()

    if row:
        return {
            "id": row[0],
            "username": row[1],
            "full_name": row[2],
            "email": row[3],
            "role": row[4],
            "feature_path": row[5],
            "created_at": row[6]
        }
    return None


def get_user_by_id(user_id):
    """Retrieves a user by their user ID."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, full_name, email, role, feature_path, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))

    row = cursor.fetchone()
    connection.close()

    if row:
        return {
            "id": row[0],
            "username": row[1],
            "full_name": row[2],
            "email": row[3],
            "role": row[4],
            "feature_path": row[5],
            "created_at": row[6]
        }
    return None


def get_all_users():
    """Retrieves all registered users."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, full_name, email, role, feature_path, created_at
        FROM users
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    connection.close()

    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "username": row[1],
            "full_name": row[2],
            "email": row[3],
            "role": row[4],
            "feature_path": row[5],
            "created_at": row[6]
        })
    return users


def get_security_metrics():
    """Calculates security stats for the dashboard."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM authentication_logs")
    total_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM authentication_logs WHERE status = 'AUTHENTICATED'")
    authenticated_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM authentication_logs WHERE status = 'UNAUTHORIZED'")
    unauthorized_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM authentication_logs WHERE status = 'SESSION LOCKED'")
    locked_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    connection.close()

    pass_rate = round((authenticated_count / total_logs * 100), 1) if total_logs > 0 else 100.0

    return {
        "total_logs": total_logs,
        "authenticated_count": authenticated_count,
        "unauthorized_count": unauthorized_count,
        "locked_count": locked_count,
        "total_users": total_users,
        "pass_rate": pass_rate
    }


if __name__ == "__main__":
    create_database()
    print("Database tables initialized successfully.")
    print("Existing records count:", len(show_logs()))