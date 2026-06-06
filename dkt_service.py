# dkt_service.py — DKT model wrapper
# Loads dkt_best_model_v5.pt on startup
# Exposes get_mastery(), get_ability_score(), get_profile()

import torch
import torch.nn as nn
import numpy as np

# ── Model Definition ──────────────────────────────────────────
class DKTModel(nn.Module):
    def __init__(self, num_skills=150, embedding_dim=200, hidden_size=256, num_layers=2, dropout=0.4):
        super(DKTModel, self).__init__()
        self.num_skills = num_skills
        self.hidden_size = hidden_size
        self.embedding = nn.Embedding(num_skills * 2 + 1, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(embedding_dim, hidden_size, num_layers=num_layers,
                            batch_first=True, dropout=dropout)
        self.output_layer = nn.Linear(hidden_size, num_skills)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        emb = self.embedding(x)
        lstm_out, _ = self.lstm(emb)
        out = self.sigmoid(self.output_layer(lstm_out))

# ── Load Model on Startup ─────────────────────────────────────
device = torch.device('cpu')
model = DKTModel().to(device)
model.load_state_dict(torch.load('dkt_best_model_v5.pt', map_location=device))
model.eval()
print("DKT model loaded successfully")

# ── Helper Functions ──────────────────────────────────────────
def encode_interactions(interactions):
    """
    Converts [(skill_id, correct), ...] → padded tensor ready for model
    Encoding: skill_id * 2 + correct + 1
    Returns: torch.LongTensor of shape [1, seq_len]
    """
    if len(interactions) == 0:
        # Empty sequence — return dummy tensor (skill 0, incorrect)
        encoded = [1]
    else:
        encoded = [s * 2 + c + 1 for s, c in interactions]
    return torch.tensor(encoded, dtype=torch.long).unsqueeze(0).to(device)

def get_mastery(interactions):
    """
    Takes [(skill_id, correct), ...] → returns [150] mastery vector
    Uses last timestep of LSTM output as current mastery estimate
    """
    tensor = encode_interactions(interactions)
    with torch.no_grad():
        emb = model.embedding(tensor)
        lstm_out, _ = model.lstm(emb)
        out = torch.sigmoid(model.output_layer(lstm_out))  # [1, seq_len, 150]
    mastery = out[0, -1, :]  # last timestep → [150]
    return mastery

def get_ability_score(mastery):
    """Returns mean mastery as single ability score float"""
    return mastery.mean().item()

def get_profile(ability_score):
    """Maps ability score → beginner / intermediate / advanced"""
    if ability_score < 0.48:
        return 'beginner'
    elif ability_score < 0.60:
        return 'intermediate'
    else:
        return 'advanced'