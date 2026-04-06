"""Recommendation engine that scores menu items based on user history."""

from . import db
from difflib import SequenceMatcher
from typing import Optional


def _similarity(a: str, b: str) -> float:
    """Fuzzy string similarity between two item names."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def score_items(
    available_items: list[dict],
    mood: Optional[str] = None,
    hunger_level: Optional[int] = None,
) -> list[dict]:
    """Score and rank available menu items based on user preferences.

    Each item gets a score from multiple signals:
    - Direct ratings (strongest signal)
    - Similar item ratings (fuzzy name match)
    - Location frequency (where you eat most)
    - Mood correlation (what you eat when feeling X)
    - Novelty bonus (haven't tried it yet)

    Returns items sorted by score descending, with reasoning.
    """
    if not available_items:
        return []

    # Load user data
    rated_items = db.get_all_rated_items()  # {name_lower: avg_rating}
    prefs = db.get_preferences()
    location_freq = db.get_location_frequency()
    allergens_to_avoid = set(v.lower() for v in prefs.get("allergy", []))
    dislikes = set(v.lower() for v in prefs.get("dislike", []))
    favorites = set(v.lower() for v in prefs.get("favorite", []))

    # Mood-based items
    mood_items = []
    if mood:
        mood_items = [name.lower() for name in db.get_mood_items(mood)]

    total_meals = sum(location_freq.values()) if location_freq else 0

    scored = []
    for item in available_items:
        name = item["name"]
        name_lower = name.lower()
        reasons = []
        score = 0.0

        # --- Filter: skip allergens and dislikes ---
        item_allergens = set(a.lower() for a in item.get("allergens", []))
        if allergens_to_avoid & item_allergens:
            continue
        if name_lower in dislikes or any(d in name_lower for d in dislikes):
            continue

        # --- Signal 1: Direct rating (0-5 points) ---
        if name_lower in rated_items:
            avg = rated_items[name_lower]
            score += avg
            reasons.append(f"You rated this {avg:.1f}/5")

        # --- Signal 2: Similar item ratings (0-3 points) ---
        if name_lower not in rated_items:
            best_sim = 0.0
            best_match = ""
            best_rating = 0.0
            for rated_name, rating in rated_items.items():
                sim = _similarity(name_lower, rated_name)
                if sim > 0.6 and sim > best_sim:
                    best_sim = sim
                    best_match = rated_name
                    best_rating = rating
            if best_sim > 0.6:
                bonus = best_rating * best_sim * 0.6
                score += bonus
                reasons.append(f"Similar to '{best_match}' ({best_rating:.1f}/5)")

        # --- Signal 3: Favorite item boost (2 points) ---
        if name_lower in favorites or any(f in name_lower for f in favorites):
            score += 2.0
            reasons.append("One of your favorites")

        # --- Signal 4: Location preference (0-1 points) ---
        loc = item.get("location", "")
        if loc and total_meals > 0:
            loc_count = location_freq.get(loc, 0)
            loc_ratio = loc_count / total_meals
            if loc_ratio > 0.2:
                score += loc_ratio
                reasons.append(f"You eat here often ({loc_count} times)")

        # --- Signal 5: Mood correlation (0-1.5 points) ---
        if mood_items and name_lower in mood_items:
            score += 1.5
            reasons.append(f"You've eaten this when feeling {mood}")

        # --- Signal 6: Vegetarian preference ---
        if "vegetarian" in prefs and item.get("vegetarian"):
            score += 1.0
            reasons.append("Vegetarian")

        # --- Signal 7: Novelty bonus (0.5 points) ---
        if name_lower not in rated_items and not any(_similarity(name_lower, r) > 0.8 for r in rated_items):
            score += 0.5
            reasons.append("Haven't tried this yet")

        # --- Signal 8: Hunger level boost for hearty items ---
        # Simple heuristic: items from certain stations tend to be more filling
        if hunger_level and hunger_level >= 4:
            hearty_keywords = ["grill", "entrée", "entree", "roast", "steak", "burger", "pasta", "rice"]
            station_lower = item.get("station", "").lower()
            if any(kw in name_lower or kw in station_lower for kw in hearty_keywords):
                score += 0.5
                reasons.append("Hearty option for big hunger")

        if not reasons:
            reasons.append("Available now")

        scored.append({
            **item,
            "score": round(score, 2),
            "reasons": reasons,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def get_recommendations(
    available_items: list[dict],
    mood: Optional[str] = None,
    hunger_level: Optional[int] = None,
    top_n: int = 5,
) -> list[dict]:
    """Get top N recommended items with reasoning."""
    scored = score_items(available_items, mood=mood, hunger_level=hunger_level)
    return scored[:top_n]
