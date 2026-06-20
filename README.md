# Pathrix — AI-Based Adaptive Learning System

> An intelligent learning platform that personalises Python concept recommendations using Deep Knowledge Tracing (DKT) and Reinforcement Learning (Q-Learning), with natural language explanations for every recommendation.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-brightgreen)](https://pathrix-frontend.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Render-blue)](https://pathrix-api.onrender.com)
[![Frontend Repo](https://img.shields.io/badge/Frontend-GitHub-black)](https://github.com/Aish0864/pathrix-frontend)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.12-red)](https://pytorch.org)

---

## Live System

| Component | URL |
|---|---|
| Frontend | https://pathrix-frontend.vercel.app |
| Backend API | https://pathrix-api.onrender.com |
| API Docs | https://pathrix-api.onrender.com/docs |

### Demo Credentials

| Role | Email | Password |
|---|---|---|
| Beginner Student | arjun@demo.com | demo123 |
| Intermediate Student | priya@demo.com | demo123 |
| Advanced Student | rahul@demo.com | demo123 |
| Admin | admin | admin123 |

---

## What is Pathrix?

Most e-learning platforms assign the same fixed content sequence to all learners regardless of prior knowledge. An advanced learner who already knows the basics is forced to start from the beginning. A beginner placed in advanced content too early becomes overwhelmed. In both cases the learner disengages.

**Pathrix solves this by:**

1. Estimating what each learner knows using a Deep Knowledge Tracing (DKT) model
2. Recommending the next concept using a Q-Learning agent trained on a 54-node Python curriculum graph
3. Explaining every recommendation in plain English
4. Monitoring cognitive load throughout the session

---

## Key Results

| Metric | Target | Result | Status |
|---|---|---|---|
| AUC-ROC | ≥ 0.75 | **0.7927** | ✅ PASS |
| RMSE | ≤ 0.45 | **0.4092** | ✅ PASS |
| Path Efficiency | ≥ 80% | **96.2%** | ✅ PASS |
| Completion Rate | ≥ 75% | **80.0%** | ✅ PASS |
| Normalised Learning Gain | ≥ 0.40 | **0.8220** | ✅ PASS |
| Explainability Score | ≥ 4.0/5 | **4.4/5** | ✅ PASS |

**User Study:** 22 real users, 566 interactions, survey scores 4.4–4.7/5 across all items.

---

## System Architecture

```
React Frontend (Vercel)
        │
        │ HTTP/REST
        ▼
FastAPI Backend (Render)
        │
   ┌────┴────┐
   │         │
   ▼         ▼
DKT Module  RL Agent
(PyTorch    (Q-Learning
 LSTM)       Q-Table)
   │         │
   └────┬────┘
        │
        ▼
   XAI Layer
(WHY String Generator)
        │
        ▼
  PostgreSQL DB
  (5 tables)
```

### Request Flow

```
1. User answers quiz
2. Interaction stored → (skill_id, correct) pair
3. DKT module processes full history → mastery vector [150]
4. RL agent builds 54-tuple state from mastery vector
5. Q-table lookup with three-tier fallback
6. XAI layer generates natural language explanation
7. Recommendation + WHY string returned to frontend
```

---

## AI Components

### Deep Knowledge Tracing (DKT)

| Parameter | Value |
|---|---|
| Architecture | 2-layer LSTM |
| Hidden size | 256 |
| Embedding dim | 200 |
| Dropout | 0.4 |
| Output | Mastery vector [150] |
| Parameters | 1,094,078 |
| Dataset | ASSISTments 2009-2010 |
| Training students | 3,222 |
| Validation students | 805 |
| AUC-ROC | 0.7927 |
| RMSE | 0.4092 |

**Encoding:** `skill_id × 2 + correct` → unique token per skill-response pair

### Q-Learning Agent

| Parameter | Value |
|---|---|
| Concepts | 54 Python nodes |
| State space | 3^54 theoretical |
| Visited states (training) | 5,074,554 |
| Deployed states | 162,821 (compressed) |
| Training episodes | 10,000 |
| Best run reward | 870 (Run 8) |
| Learning rate α | 0.1 |
| Discount factor γ | 0.9 |
| Exploration rate ε | 0.1 |

**Reward function:** mastery gain + speed bonus − wrong answer penalty (−0.3) − timeout penalty (−0.5)

**Three-tier fallback:**
1. Exact Q-table lookup
2. Hamming distance nearest neighbour (distance ≤ 5, Q > 1.0)
3. Level-order default (first unmastered concept)

**Deployment compression:** Full Q-table was 2.72GB. States with Q-value < 2.0 pruned → 93.8MB deployed version.

### XAI Layer

Every recommendation includes a natural language explanation built from:
- Recommended concept name and current mastery %
- Q-value → confidence tier (High: Q ≥ 5.0, Medium: Q ≥ 2.0, Low: Q < 2.0)
- Failure rate over last 5 interactions → cognitive load (High: ≥ 0.6, Medium: ≥ 0.3, Low: < 0.3)

**Example:** *"Strings is recommended because you haven't started it yet and all prerequisites are met. Confidence: MEDIUM. Cognitive load: LOW."*

---

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI |
| ML Framework | PyTorch 2.12 (CPU-only for deployment) |
| Database (local) | SQLite |
| Database (deployed) | PostgreSQL (Render) |
| Authentication | bcrypt + session tokens |
| Language | Python 3.11 |

### Frontend
| Component | Technology |
|---|---|
| Framework | React |
| Screens | 15+ |
| Deployment | Vercel |

### Infrastructure
| Component | Service |
|---|---|
| Backend hosting | Render (free tier) |
| Frontend hosting | Vercel |
| Database | Render PostgreSQL |
| Model training | Google Colab (T4 GPU) |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /register | Register new student |
| POST | /login | Student login |
| POST | /admin/login | Admin login |
| POST | /submit_quiz | Submit quiz interaction |
| GET | /get_recommendation | Get next concept recommendation |
| GET | /get_mastery | Get current mastery vector |
| GET | /get_progress | Get learner progress summary |
| GET | /admin/students | List all students (admin) |
| GET | /admin/student/{id} | Get student details (admin) |
| GET | /admin/pipeline | View AI pipeline status (admin) |
| GET | /admin/ab_comparison | A/B comparison data (admin) |
| GET | /health | Health check |

Full interactive docs: https://pathrix-api.onrender.com/docs

---

## Database Schema

```
students
├── id (UUID, PK)
├── name
├── email (unique)
├── password_hash
└── created_at

sessions
├── id (UUID, PK)
├── student_id (FK)
├── profile (beginner/intermediate/advanced)
└── created_at

interactions
├── id (UUID, PK)
├── student_id (FK)
├── skill_id
├── correct (boolean)
└── created_at

student_mastery
├── id (UUID, PK)
├── student_id (FK)
├── concept_id
├── mastery_score
└── updated_at

rl_rewards
├── id (UUID, PK)
├── student_id (FK)
├── concept_id
├── reward
└── created_at
```

---

## Project Structure

```
pathrix-api/
├── main.py                    # FastAPI app, all endpoints
├── db.py                      # Database connection + queries
├── models.py                  # Pydantic request/response models
├── dkt_service.py             # DKT inference service
├── rl_service.py              # Q-Learning agent + XAI layer
├── concept_graph.json         # 54-node Python curriculum graph
├── dkt_best_model_v5.pt       # Trained DKT model (4MB)
├── q_table_final.pkl          # Compressed Q-table (93.8MB)
├── compress_qtable_v3.py      # Q-table compression script
├── seed_demo.py               # Demo user seeding script
├── requirements.txt           # Python dependencies
└── runtime.txt                # Python 3.11 for Render
```

---

## How to Run Locally

### Prerequisites
```bash
Python 3.11
Node.js 18+ (for frontend)
```

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/Aish0864/pathrix-api
cd pathrix-api

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn main:app --reload
```

API will be available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### Environment Variables

For local development, SQLite is used by default (no setup needed).

For PostgreSQL deployment, set:
```
DATABASE_URL=postgresql://user:password@host/dbname
```

### Seed Demo Users

```bash
python seed_demo.py
```

Creates demo accounts: arjun@demo.com, priya@demo.com, rahul@demo.com

### Frontend Setup

```bash
git clone https://github.com/Aish0864/pathrix-frontend
cd pathrix-frontend
npm install
npm start
```

Frontend at `http://localhost:3000`

---

## Python Concept Graph

54 concepts across 10 curriculum levels:

```
Level 1:  Variables, Data Types, Strings, Input/Output
Level 2:  Operators, String Methods, Type Conversion
Level 3:  Conditionals, Loops (For, While)
Level 4:  Functions, Parameters, Return Values
Level 5:  Lists, Tuples, Dictionaries, Sets
Level 6:  Modules, File I/O
Level 7:  Exception Handling, Comprehensions
Level 8:  OOP Basics, Classes, Objects
Level 9:  Decorators, Generators, Multiprocessing
Level 10: Advanced Topics
```

---

## Ablation Study — DKT Model Selection

| Model | Hidden | Val Loss | AUC-ROC | Accuracy |
|---|---|---|---|---|
| v2 | 128 | 0.5488 | 0.7850 | 75.03% |
| v3 | 256 | 0.5430 | 0.7888 | 75.30% |
| v3r2 | 256 | 0.5381 | 0.7876 | 75.07% |
| v4 | 256 | 0.5368 | 0.7857 | 75.06% |
| **v5** | **256** | **0.5372** | **0.7927** | **75.51%** |
| v6 | 256* | 0.5326 | 0.7662 | 73.69% |

*v6 used embedding_dim=256 — lower loss but worse AUC, demonstrating BCE loss and AUC measure different properties.

**Selected: v5** — best AUC-ROC, early stopping at epoch 9.

---

## Research Context

This system was developed as an MTech Computer Engineering dissertation at Vidyalankar Institute of Technology, Wadala, Maharashtra, India.

**Guide:** Dr. Kavita P. Shirsat

**Survey Paper:** "Bridging Knowledge Tracing and Path Planning in AI-Based Personalized Learning: A Systematic Survey" — submitted to International Journal of Educational Technology in Higher Education (Springer, Q1)

### Novelty

No existing system combines all four components in a single deployed framework:

| System | KT | RL | XAI | Cog. Load | Deployed |
|---|---|---|---|---|---|
| Tong & Ren 2025 | DKT | ❌ | ❌ | ✅ | ❌ |
| Fu 2025 | DKT | Policy Grad | ❌ | ❌ | ❌ |
| APPEAL 2023 | ❌ | DQN | ❌ | ❌ | ❌ |
| **Pathrix** | **DKT** | **Q-Learn** | **✅** | **✅** | **✅** |

---

## Limitations

- DKT trained on ASSISTments mathematics data (domain mismatch with Python)
- Small user study cohort (22 users, single session)
- No control group — learning benefit vs non-adaptive not formally measured
- Cognitive load estimated from failure rate (behavioural proxy only)
- Offline Q-Learning policy — does not update from real interactions
- 54 concepts only — limited Python curriculum coverage

---

## Future Work

- Train DKT on Python-specific interaction dataset
- Implement online RL policy updating from real user sessions
- Expand concept graph to 150+ nodes (OOP, Django, NumPy, Pandas)
- A/B test against non-adaptive baseline
- Longitudinal multi-session evaluation
- Mobile responsive frontend

---

## Author

**Aishwarya Nalawade**
MTech Computer Engineering
Vidyalankar Institute of Technology, Wadala, Maharashtra, India

---

## Frontend Repository

👉 https://github.com/Aish0864/pathrix-frontend
