from typing import Dict, List, Tuple
import re
from .taxonomy import load_taxonomy


def classify_direction(title: str, abstract: str, primary_category: str) -> Tuple[str, Dict[str, float]]:
    tax = load_taxonomy()
    text = f"{title} {abstract}".lower()
    scores = {}
    for direction, cfg in tax.items():
        score = 0.0
        cats = cfg.get("primary_categories", [])
        if primary_category and primary_category in cats:
            score += 3.0
        for kw in cfg.get("keywords", []):
            if re.search(rf"\\b{re.escape(kw.lower())}\\b", text):
                score += 1.0
        scores[direction] = score
    best = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if not best or best[0][1] == 0:
        return None, scores
    return best[0][0], scores
