# models.py — Pydantic request/response schemas

from pydantic import BaseModel
from typing import Optional

# /start_session
class StartSessionRequest(BaseModel):
    student_id: str

class StartSessionResponse(BaseModel):
    session_id: str
    student_id: str
    status: str

# /submit_quiz
class SubmitQuizRequest(BaseModel):
    session_id: str
    student_id: str        # ← added for persistent interactions
    skill_id: int
    correct: int           # 0 or 1
    time_taken_seconds: int
    timed_out: bool

class SubmitQuizResponse(BaseModel):
    mastery_updated: bool
    skill_id: int
    correct: int
    sequence_length: int
    status: str

# /get_recommendation
class RecommendationRequest(BaseModel):
    session_id: str

class RecommendationResponse(BaseModel):
    recommended_concept: str
    q_value: float
    confidence: str
    ability_score: float
    profile: str
    cognitive_load: str
    suggestion: str
    explanation: str

# /get_path
class PathStep(BaseModel):
    step: int
    concept: str
    q_value: float

class GetPathRequest(BaseModel):
    session_id: str
    steps: int = 6

class GetPathResponse(BaseModel):
    path: list[PathStep]

# /get_explanation
class GetExplanationResponse(BaseModel):
    explanation: str
    confidence: str
    cognitive_load: str
    trend: str