# main.py — FastAPI app entry point
from models import StartSessionRequest, StartSessionResponse
from models import SubmitQuizRequest, SubmitQuizResponse
from models import RecommendationRequest, RecommendationResponse
from models import GetPathRequest, GetPathResponse, PathStep
from models import GetExplanationResponse
from dkt_service import get_mastery
from rl_service import get_full_recommendation, get_learning_path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uuid
import json
import bcrypt

from db import init_db, get_connection, save_interaction, get_all_interactions, mark_concept_mastered, get_mastered_concepts, get_overall_mastery, save_rl_reward

# ── Auth request models ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class MarkMasteredRequest(BaseModel):
    student_id: str
    concept_id: int
    score: int
    total: int

class GetSessionRequest(BaseModel):
    student_id: str

# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Pathrix API",
    description="AI-Based Adaptive Learning System — MTech Dissertation 2",
    version="1.0.0",
    lifespan=lifespan
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pathrix.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Pathrix API is running", "version": "1.0.0"}

# ── Auth endpoints ───────────────────────────────────────────────────
@app.post("/register")
def register(request: RegisterRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM students WHERE email = ?", (request.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    student_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()

    cursor.execute("""
        INSERT INTO students (id, name, email, password_hash)
        VALUES (?, ?, ?, ?)
    """, (student_id, request.name, request.email, password_hash))

    conn.commit()
    conn.close()

    return {"student_id": student_id, "name": request.name, "status": "registered"}


@app.post("/login")
def login(request: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE email = ?", (request.email,))
    student = cursor.fetchone()
    conn.close()

    if not student or not bcrypt.checkpw(request.password.encode(), student["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "student_id": student["id"],
        "name": student["name"],
        "token": str(uuid.uuid4())   # simple token for now
    }
@app.get("/check_first_login")
def check_first_login(student_id: str):
    from db import is_first_session
    return {"is_first": is_first_session(student_id)}

# ── Existing endpoints (unchanged) ───────────────────────────────────
@app.post("/start_session", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest):
    conn = get_connection()
    cursor = conn.cursor()

    # Check if active session already exists for this student
    cursor.execute("""
        SELECT session_id FROM sessions 
        WHERE student_id = ? AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
    """, (request.student_id,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return StartSessionResponse(
            session_id=existing["session_id"],
            student_id=request.student_id,
            status="reused"
        )

    session_id = str(uuid.uuid4())
    all_interactions = get_all_interactions(request.student_id)

    cursor.execute("""
        INSERT INTO sessions (session_id, student_id, status, interactions)
        VALUES (?, ?, 'active', ?)
    """, (session_id, request.student_id, json.dumps(all_interactions)))
    
    conn.commit()
    conn.close()
    
    return StartSessionResponse(
        session_id=session_id,
        student_id=request.student_id,
        status="started"
    )

@app.post("/submit_quiz", response_model=SubmitQuizResponse)
def submit_quiz(request: SubmitQuizRequest):
    # 1 — save interaction permanently to DB
    save_interaction(
        request.student_id,
        request.skill_id,
        request.correct,
        request.time_taken_seconds,
        request.timed_out
    )

    # 2 — load full interaction history for this student
    all_interactions = get_all_interactions(request.student_id)

    # 3 — update session with full history
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (request.session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    cursor.execute("""
        UPDATE sessions SET interactions = ? WHERE session_id = ?
    """, (json.dumps(all_interactions), request.session_id))

    conn.commit()
    conn.close()

    return SubmitQuizResponse(
        mastery_updated=True,
        skill_id=request.skill_id,
        correct=request.correct,
        sequence_length=len(all_interactions),
        status="recorded"
    )
    
@app.post("/get_recommendation", response_model=RecommendationResponse)
def get_recommendation(request: RecommendationRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (request.session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    interactions = json.loads(session["interactions"])
    
    # ── Get mastered concept IDs to exclude ──
    student_id = session["student_id"]
    mastered_ids = get_mastered_concepts(student_id)
    
    mastery = get_mastery(interactions)
    result = get_full_recommendation(mastery, interactions, mastered_ids=mastered_ids)

    cursor.execute("""
    UPDATE sessions SET 
        last_recommendation = ?,
        confidence = ?,
        cognitive_load = ?,
        explanation = ?,
        trend = ?
    WHERE session_id = ?
    """, (
        result['recommended_concept'],
        result['confidence'],
        result['cognitive_load'],
        result['explanation'],
        'improving',
        request.session_id
    ))

    conn.commit()
    conn.close()

    return RecommendationResponse(**result)

@app.post("/get_path", response_model=GetPathResponse)
def get_path(request: GetPathRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (request.session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    interactions = json.loads(session["interactions"])
    conn.close()

    mastery = get_mastery(interactions)
    path = get_learning_path(mastery, interactions, steps=request.steps)

    return GetPathResponse(path=[PathStep(**step) for step in path])


@app.get("/get_explanation", response_model=GetExplanationResponse)
def get_explanation(session_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    explanation = session["explanation"]
    confidence = session["confidence"]
    cognitive_load = session["cognitive_load"]
    trend = session["trend"]
    conn.close()

    if not explanation:
        raise HTTPException(status_code=404, detail="No recommendation yet — call /get_recommendation first")

    return GetExplanationResponse(
        explanation=explanation,
        confidence=confidence,
        cognitive_load=cognitive_load,
        trend=trend
    )
    
@app.post("/mark_mastered")
def mark_mastered(request: MarkMasteredRequest):
    # Get mastery BEFORE this quiz
    conn = get_connection()
    row = conn.execute(
        "SELECT mastery_pct FROM student_mastery WHERE student_id=? AND concept_id=?",
        (request.student_id, request.concept_id)
    ).fetchone()
    conn.close()
    mastery_before = row[0] if row else 0.0

    # Save mastery
    mark_concept_mastered(request.student_id, request.concept_id, request.score, request.total)
    
    # Compute mastery after
    mastery_after = round((request.score / request.total) * 100, 2)
    
    # Save reward
    save_rl_reward(
        request.student_id,
        request.concept_id,
        mastery_before,
        mastery_after,
        request.score,
        request.total
    )

    overall = get_overall_mastery(request.student_id)
    return {"status": "mastered", "concept_id": request.concept_id, "overall_mastery": overall}

@app.get("/rewards/{student_id}")
def get_rewards(student_id: str, limit: int = 20):
    conn = get_connection()
    rows = conn.execute("""
        SELECT concept_id, mastery_before, mastery_after, score, total, reward, timestamp
        FROM rl_rewards
        WHERE student_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (student_id, limit)).fetchall()
    conn.close()

    CONCEPT_NAMES = [
        "Variables","Data Types","Operators","Input/Output","Comments",
        "If/Else","Elif","For Loop","While Loop","Break/Continue","Pass",
        "Strings","Lists","Tuples","Sets","Dictionaries","List Slicing",
        "Functions","Arguments","Return Values","Default Args","Scope","Lambda",
        "Base Case","Recursive Functions","Memoization","Classes","Objects",
        "Constructors","Inheritance","Polymorphism","Encapsulation","Modules",
        "Packages","File Read","File Write","Exception Handling","Try/Except",
        "Comprehensions","Iterators","Generators","Decorators","Context Managers",
        "Math","OS","Sys","DateTime","Collections","Itertools","Threading",
        "Multiprocessing","Async/Await","Event Loop","Locks/Semaphores"
    ]

    return [
        {
            "concept": CONCEPT_NAMES[r[0]] if r[0] < len(CONCEPT_NAMES) else f"Concept {r[0]}",
            "mastery_before": round(r[1], 1),
            "mastery_after":  round(r[2], 1),
            "score":          r[3],
            "total":          r[4],
            "reward":         r[5],
            "timestamp":      r[6],
        }
        for r in rows
    ]

@app.get("/student_mastery/{student_id}")
def get_student_mastery(student_id: str):
    mastered = get_mastered_concepts(student_id)
    overall = get_overall_mastery(student_id)
    return {"mastered_concepts": mastered, "overall_mastery": overall, "total": 54}

@app.get("/overall_mastery/{student_id}")
def overall_mastery(student_id: str):
    return {"overall_mastery": get_overall_mastery(student_id)}    
    
@app.get("/admin/students")
def get_admin_students():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students ORDER BY created_at DESC")
    students = cursor.fetchall()

    result = []
    for student in students:
        # Get interaction count
        cursor.execute(
            "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
            (student["id"],)
        )
        interaction_count = cursor.fetchone()[0]

        # Get session count and last recommendation
        cursor.execute(
            "SELECT COUNT(*), MAX(last_recommendation), MAX(confidence), MAX(cognitive_load) FROM sessions WHERE student_id = ?",
            (student["id"],)
        )
        session_data = cursor.fetchone()
        session_count = session_data[0]
        last_recommendation = session_data[1]
        confidence = session_data[2]
        cognitive_load = session_data[3]

        # Calculate avg mastery from interactions
        cursor.execute(
            "SELECT AVG(correct) * 100 FROM interactions WHERE user_id = ?",
            (student["id"],)
        )
        avg_mastery = cursor.fetchone()[0] or 0
        cursor.execute(
            "SELECT COUNT(*) FROM student_mastery WHERE student_id = ? AND mastered = 1",
            (student["id"],)
        )
        mastered_count = cursor.fetchone()[0] or 0
        cursor.execute(
            "SELECT MAX(timestamp) FROM interactions WHERE user_id = ?",
            (student["id"],)
        )
        last_active_row = cursor.fetchone()[0]
        if last_active_row:
            from datetime import datetime
            last_date = last_active_row[:10]
            today = datetime.now().strftime("%Y-%m-%d")
            last_active = "today" if last_date == today else last_date
        else:
            last_active = "never"

        # Determine profile from interaction count
        if interaction_count >= 30:
            profile = 'advanced'
        elif interaction_count >= 15:
            profile = 'intermediate'
        else:
            profile = 'beginner'

        result.append({
            "id": student["id"],
            "name": student["name"],
            "email": student["email"],
            "created_at": student["created_at"],
            "interaction_count": interaction_count,
            "session_count": session_count,
            "avg_mastery": round(avg_mastery, 1),
            "mastered_count": mastered_count,
            "overall_progress": round((mastered_count / 54) * 100, 1),
            "last_recommendation": last_recommendation,
            "confidence": confidence,
            "cognitive_load": cognitive_load,
            "profile": profile,
            "last_active": last_active
        })

    conn.close()
    return {"students": result}