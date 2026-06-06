# rl_service.py — RL + XAI wrapper
# Loads concept_graph.json + q_table_session6_final.pkl on startup
# Exposes get_full_recommendation() as single entry point

import json
import pickle
import numpy as np
import torch

# ── Load on Startup ───────────────────────────────────────────
with open('concept_graph.json', 'r') as f:
    concept_graph = json.load(f)

with open('q_table_final.pkl', 'rb') as f:
    q_table = pickle.load(f)

concept_nodes = [concept_graph[str(i)] for i in range(len(concept_graph))]
concept_names = [node['name'] for node in concept_nodes]
concept_lookup = {node['name']: node for node in concept_nodes}

print(f"RL service loaded — {len(concept_names)} concepts, {len(q_table)} Q-states")

# ── State Builder ─────────────────────────────────────────────
def normalize_mastery(mastery):
    mn, mx = mastery.min().item(), mastery.max().item()
    if mx - mn < 1e-6:
        return mastery
    return (mastery - mn) / (mx - mn)

def build_rl_state(mastery, profile, student_idx=0):
    mastery_norm = normalize_mastery(mastery)
    state = np.zeros(54)

    if profile == 'beginner':
        for cid in range(54):
            level = concept_nodes[cid]['level']
            start, end = level * 15, level * 15 + 15
            state[cid] = mastery_norm[start:end].mean().item()

    elif profile == 'intermediate':
        np.random.seed(student_idx)
        for i in range(11):
            state[i] = np.random.uniform(0.8, 1.0)
        for cid in range(11, 54):
            level = concept_nodes[cid]['level']
            start, end = level * 15, level * 15 + 15
            state[cid] = mastery_norm[start:end].mean().item()

    elif profile == 'advanced':
        np.random.seed(student_idx)
        for i in range(25):
            state[i] = np.random.uniform(0.8, 1.0)
        for cid in range(25, 54):
            level = concept_nodes[cid]['level']
            start, end = level * 15, level * 15 + 15
            state[cid] = mastery_norm[start:end].mean().item()

    thresh = {'beginner': 0.35, 'intermediate': 0.45, 'advanced': 0.55}[profile]
    discrete = []
    for val in state:
        if val < thresh:
            discrete.append(0)
        elif val < 0.6:
            discrete.append(1)
        else:
            discrete.append(2)
    return tuple(discrete)

# ── Nearest State Fallback ────────────────────────────────────
def find_nearest_nonzero_state(rl_state, max_search=200000):
    rl_arr = np.array(rl_state)
    best_state = None
    best_dist = float('inf')
    best_q = None

    for i, (state, qvals) in enumerate(q_table.items()):
        if i >= max_search:
            break
        if np.max(qvals) == 0.0:
            continue
        dist = np.sum(np.array(state) != rl_arr)
        if dist < best_dist:
            best_dist = dist
            best_state = state
            best_q = qvals

    return best_state, best_dist, best_q

# ── Cognitive Load ────────────────────────────────────────────
def compute_cognitive_load(interactions):
    recent = interactions[-5:] if len(interactions) >= 5 else interactions
    if len(recent) == 0:
        return {'load_level': 'low', 'fail_rate': 0.0,
                'suggestion': 'No interactions yet — start with basics'}
    total = len(recent)
    fails = sum(1 for _, correct in recent if correct == 0)
    fail_rate = fails / total
    if fail_rate >= 0.6:
        load_level = 'high'
        suggestion = 'Review easier concepts before proceeding'
    elif fail_rate >= 0.3:
        load_level = 'medium'
        suggestion = 'Proceed with recommended concept, monitor progress'
    else:
        load_level = 'low'
        suggestion = 'Student ready — proceed to next level'
    return {'load_level': load_level, 'fail_rate': fail_rate, 'suggestion': suggestion}

# ── Confidence ────────────────────────────────────────────────
def get_confidence(best_q, tag):
    if tag == 'level-order':
        return 'low'
    elif best_q >= 5.0:
        return 'high'
    elif best_q >= 2.0:
        return 'medium'
    else:
        return 'low'

# ── WHY String ────────────────────────────────────────────────
def build_why_string(mastery, recommended, profile, best_q, tag):
    info = concept_lookup[recommended]
    prereq_thresh = {'beginner': 0.35, 'intermediate': 0.45, 'advanced': 0.55}[profile]
    target_idx = concept_names.index(recommended)
    target_mastery = mastery[target_idx].item()
    pct = int(target_mastery * 100)

    # Prerequisite check
    prereq_met, prereq_total = 0, 0
    for prereq_id in info.get('prerequisites', []):
        prereq_name = concept_names[prereq_id]
        prereq_idx = concept_names.index(prereq_name)
        prereq_mastery = mastery[prereq_idx].item()
        if prereq_mastery >= prereq_thresh:
            prereq_met += 1
        prereq_total += 1

    # Natural language
    if prereq_total == 0:
        prereq_text = "no prerequisites needed"
    elif prereq_met == prereq_total:
        prereq_text = "all prerequisites are met"
    else:
        prereq_text = f"{prereq_met} of {prereq_total} prerequisites are met"

    if pct == 0:
        mastery_text = "you haven't started it yet"
    elif pct < 60:
        mastery_text = f"your mastery is at {pct}%"
    else:
        mastery_text = f"your mastery is at {pct}% — you're close to mastering it"

    return f"{recommended} is recommended because {mastery_text} and {prereq_text}."

# ── Single Entry Point ────────────────────────────────────────
def get_full_recommendation(mastery, interactions, student_idx=0):
    """
    Single entry point for main.py
    mastery: [150] tensor from DKT
    interactions: [(skill_id, correct), ...] list
    Returns: dict with all recommendation fields
    """
    from dkt_service import get_ability_score, get_profile
    ability = get_ability_score(mastery)
    profile = get_profile(ability)

    # Q-table lookup
    rl_state = build_rl_state(mastery, profile, student_idx)

    if rl_state in q_table:
        q_values = q_table[rl_state]
        best_action = int(np.argmax(q_values))
        best_q = float(np.max(q_values))
        tag = 'Q-learned'
    else:
        nearest_state, dist, nearest_q = find_nearest_nonzero_state(rl_state)
        if nearest_state is not None and dist <= 5 and np.max(nearest_q) > 1.0:
            best_action = int(np.argmax(nearest_q))
            best_q = float(np.max(nearest_q))
            tag = f'Q-approximated (Hamming={dist})'
        else:
            best_action = next((i for i in range(54) if mastery[i].item() < 0.5), 0)
            best_q = 0.0
            tag = 'level-order'

    recommended = concept_names[best_action]
    info = concept_lookup[recommended]
    confidence = get_confidence(best_q, tag)
    load = compute_cognitive_load(interactions)
    explanation = build_why_string(mastery, recommended, profile, best_q, tag)

    return {
        'recommended_concept': f"{recommended} L{info['level']}",
        'q_value': round(best_q, 2),
        'confidence': confidence,
        'ability_score': round(ability, 4),
        'profile': profile,
        'cognitive_load': load['load_level'],
        'suggestion': load['suggestion'],
        'explanation': explanation
    }
    
# ── Learning Path ─────────────────────────────────────────────
def simulate_mastery_gain(mastery, concept_idx, gain=0.6):
    mastery = mastery.clone()
    mastery[concept_idx] = min(1.0, mastery[concept_idx].item() + gain)
    level = concept_nodes[concept_idx]['level']
    start, end = level * 15, level * 15 + 15
    for i in range(start, min(end, 150)):
        mastery[i] = min(1.0, mastery[i].item() + 0.35)
    return mastery

def get_learning_path(mastery, interactions, steps=6, student_idx=0):
    """
    Loop N steps — get recommendation, simulate gain, repeat.
    Returns ordered list of {step, concept, q_value}.
    """
    path = []
    current_mastery = mastery.clone()

    for step in range(1, steps + 1):
        result = get_full_recommendation(current_mastery, interactions, student_idx)
        concept_name = result['recommended_concept'].split(' L')[0]  # strip level suffix
        concept_idx = concept_names.index(concept_name) if concept_name in concept_names else 0

        path.append({
            'step': step,
            'concept': result['recommended_concept'],
            'q_value': result['q_value']
        })

        # Simulate mastery gain on recommended concept
        current_mastery = simulate_mastery_gain(current_mastery, concept_idx)

    return path

def get_full_recommendation(mastery, interactions, student_idx=0, mastered_ids=None):
    from dkt_service import get_ability_score, get_profile
    ability = get_ability_score(mastery)
    profile = get_profile(ability)

    rl_state = build_rl_state(mastery, profile, student_idx)

    if rl_state in q_table:
        q_values = q_table[rl_state].copy()
        # ── Mask out already-mastered concepts ──
        if mastered_ids:
            for mid in mastered_ids:
                if mid < len(q_values):
                    q_values[mid] = -999
        best_action = int(np.argmax(q_values))
        best_q = float(q_table[rl_state][best_action])
        tag = 'Q-learned'
    else:
        nearest_state, dist, nearest_q = find_nearest_nonzero_state(rl_state)
        if nearest_state is not None and dist <= 5 and np.max(nearest_q) > 1.0:
            nearest_q = nearest_q.copy()
            if mastered_ids:
                for mid in mastered_ids:
                    if mid < len(nearest_q):
                        nearest_q[mid] = -999
            best_action = int(np.argmax(nearest_q))
            best_q = float(np.max(nearest_q))
            tag = f'Q-approximated (Hamming={dist})'
        else:
            best_action = next((i for i in range(54)
                                if i not in (mastered_ids or [])
                                and mastery[i].item() < 0.5), 0)
            best_q = 0.0
            tag = 'level-order'

    recommended = concept_names[best_action]
    info = concept_lookup[recommended]
    confidence = get_confidence(best_q, tag)
    load = compute_cognitive_load(interactions)
    explanation = build_why_string(mastery, recommended, profile, best_q, tag)

    return {
        'recommended_concept': f"{recommended} L{info['level']}",
        'q_value': round(best_q, 2),
        'confidence': confidence,
        'ability_score': round(ability, 4),
        'profile': profile,
        'cognitive_load': load['load_level'],
        'suggestion': load['suggestion'],
        'explanation': explanation
    }