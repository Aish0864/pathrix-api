# seed_demo.py — run once from pathrix-api/
# python seed_demo.py

import sqlite3
import bcrypt
import random
from datetime import datetime, timedelta

DB_PATH = "pathrix.db"

DEMO_USERS = [
    { "name": "Arjun Demo", "email": "arjun@demo.com", "password": "demo123", "mastered_count": 8  },
    { "name": "Priya Demo",  "email": "priya@demo.com",  "password": "demo123", "mastered_count": 24 },
    { "name": "Rahul Demo",  "email": "rahul@demo.com",  "password": "demo123", "mastered_count": 41 },
]

def rand_time(days=30):
    delta = timedelta(days=random.randint(0,days), hours=random.randint(0,23))
    return (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")

conn = sqlite3.connect(DB_PATH)

for user in DEMO_USERS:
    existing = conn.execute("SELECT id FROM students WHERE email=?", (user["email"],)).fetchone()
    if existing:
        print(f"Skipping {user['email']} — already exists")
        continue

    uid = __import__('uuid').uuid4().__str__()
    pw  = bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt()).decode()
    conn.execute("INSERT INTO students (id,name,email,password_hash,created_at) VALUES (?,?,?,?,?)",
                 (uid, user["name"], user["email"], pw, rand_time(30)))

    n = user["mastered_count"]
    for cid in range(n):
        score = random.randint(3,5)
        pct   = round((score/5)*100, 2)
        conn.execute("""
            INSERT INTO student_mastery (student_id,concept_id,mastered,mastery_pct,updated_at)
            VALUES (?,?,1,?,?)
            ON CONFLICT(student_id,concept_id) DO UPDATE SET mastered=1,mastery_pct=excluded.mastery_pct
        """, (uid, cid, pct, rand_time(20)))
        conn.execute("INSERT INTO interactions (user_id,skill_id,correct,time_taken_seconds,timed_out) VALUES (?,?,1,?,0)",
                     (uid, cid, random.randint(5,25)))

    print(f"Created {user['email']} — {n} concepts mastered")

conn.commit()
conn.close()
print("Done. Login: arjun/priya/rahul @demo.com — password: demo123")