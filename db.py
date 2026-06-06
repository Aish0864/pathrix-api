# db.py — SQLite connection and table setup

import sqlite3

DB_PATH = "pathrix.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'active',
        interactions TEXT DEFAULT '[]',
        last_recommendation TEXT DEFAULT NULL,
        confidence TEXT DEFAULT NULL,
        cognitive_load TEXT DEFAULT NULL,
        explanation TEXT DEFAULT NULL,
        trend TEXT DEFAULT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id            TEXT,
        skill_id           INTEGER,
        correct            INTEGER,
        time_taken_seconds INTEGER DEFAULT 0,
        timed_out          INTEGER DEFAULT 0,
        timestamp          DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_mastery (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        concept_id INTEGER,
        mastered   INTEGER DEFAULT 0,
        mastery_pct REAL DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, concept_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rl_rewards (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      TEXT,
        concept_id      INTEGER,
        mastery_before  REAL,
        mastery_after   REAL,
        score           INTEGER,
        total           INTEGER,
        reward          REAL,
        timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("DB initialised — all tables ready")

def save_interaction(user_id, skill_id, correct, time_taken=0, timed_out=0):
    conn = get_connection()
    conn.execute(
        """INSERT INTO interactions 
           (user_id, skill_id, correct, time_taken_seconds, timed_out) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, skill_id, int(correct), int(time_taken), int(timed_out))
    )
    conn.commit()
    conn.close()

def get_all_interactions(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT skill_id, correct FROM interactions WHERE user_id = ? ORDER BY timestamp ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows]

def is_first_session(user_id):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count == 0

def mark_concept_mastered(student_id, concept_id, score, total):
    mastery_pct = round((score / total) * 100, 2)
    conn = get_connection()
    conn.execute("""
        INSERT INTO student_mastery (student_id, concept_id, mastered, mastery_pct, updated_at)
        VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(student_id, concept_id) DO UPDATE SET
            mastered = 1,
            mastery_pct = excluded.mastery_pct,
            updated_at = CURRENT_TIMESTAMP
    """, (student_id, concept_id, mastery_pct))
    conn.commit()
    conn.close()

def get_mastered_concepts(student_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT concept_id FROM student_mastery WHERE student_id = ? AND mastered = 1",
        (student_id,)
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_overall_mastery(student_id):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM student_mastery WHERE student_id = ? AND mastered = 1",
        (student_id,)
    ).fetchone()[0]
    conn.close()
    return round((count / 54) * 100, 2)

def save_rl_reward(student_id, concept_id, mastery_before, mastery_after, score, total):
    reward = round((mastery_after - mastery_before) / 100, 3)
    conn = get_connection()
    conn.execute("""
        INSERT INTO rl_rewards 
            (student_id, concept_id, mastery_before, mastery_after, score, total, reward)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, concept_id, mastery_before, mastery_after, score, total, reward))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()