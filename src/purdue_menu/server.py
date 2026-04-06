"""Purdue Dining MCP Server — personalized food recommendations."""

from mcp.server.fastmcp import FastMCP
from datetime import date, datetime
from typing import Optional

from . import api, db
from .recommender import get_recommendations

mcp = FastMCP(
    name="purdue-dining",
    instructions="""You are a Purdue dining assistant that helps the user decide what to eat.
You learn their preferences over time — what they like, where they eat, how they feel.

IMPORTANT: On first interaction, ALWAYS call get_started first.
- If it says the user is new (no preferences or ratings), walk them through setup
  conversationally — ask about allergies, food they love, food they hate, where they
  usually eat, and any diet goals. Use set_preference to save each answer.
- If it says the user is AWAY FROM CAMPUS, do NOT proactively call dining tools.
  Just chat normally. Only use dining tools if they explicitly ask about menus or dining.
  Mention they can say "I'm back on campus" to re-enable proactive dining suggestions.

When they say "I'm hungry" or "I'm at Wiley", use the what_should_i_eat tool.
When they say "I'm leaving campus" or "going on vacation", use set_campus_status(false).
When they say "I'm back" or "back on campus", use set_campus_status(true).
When they tell you what they ate or rate food, use log_meal or rate_item.
Be casual and helpful. You know the Purdue dining courts.""",
)


@mcp.tool()
def set_campus_status(on_campus: bool) -> str:
    """Toggle whether the user is currently on/near Purdue campus.

    Use this when someone says "I'm leaving campus", "going on break",
    "I'm back at Purdue", etc. When off-campus, the assistant won't
    proactively suggest dining tools.

    Args:
        on_campus: True if at/near Purdue, False if away (vacation, break, etc.)
    """
    db.set_preference("on_campus", str(on_campus).lower())
    if on_campus:
        return "Welcome back! Campus dining tools are active again. Say 'I'm hungry' anytime."
    else:
        return "Got it — dining suggestions paused. Say 'I'm back on campus' when you return!"


@mcp.tool()
def get_started() -> str:
    """Check if the user is new and needs onboarding setup.

    ALWAYS call this on the first interaction in a conversation.
    Returns the user's current profile status — if they're new (no preferences,
    no ratings), the assistant should walk them through a friendly setup chat.

    The setup should feel conversational, not like a form. Ask about:
    1. Any food allergies or dietary restrictions
    2. Foods they love (favorites)
    3. Foods they hate (dislikes)
    4. Which dining courts they usually go to
    5. Any diet goals (high protein, vegetarian, etc.)

    Then use set_preference to save each answer.
    """
    prefs = db.get_preferences()
    ratings = db.get_ratings(limit=1)
    meals = db.get_meal_history(limit=1)

    total_prefs = sum(len(v) for v in prefs.values())
    has_ratings = len(ratings) > 0
    has_meals = len(meals) > 0

    # Check campus status
    campus_values = prefs.get("on_campus", [])
    on_campus = campus_values[0] != "false" if campus_values else True

    if total_prefs == 0 and not has_ratings and not has_meals:
        return (
            "NEW_USER: This user has no preferences, ratings, or meal history. "
            "They need onboarding! Walk them through a quick, friendly setup chat. "
            "Ask about allergies, favorite foods, foods they dislike, where they usually eat, "
            "and any diet goals. Use set_preference to save each answer as you go. "
            "Keep it conversational — don't dump all questions at once. "
            "After setup, show them what's available right now with whats_open."
        )

    # Returning user — show their profile summary
    lines = ["RETURNING_USER: Profile loaded."]
    if not on_campus:
        lines.append("  ⚠️ AWAY FROM CAMPUS — do NOT proactively call dining tools.")
        lines.append("  Only use dining tools if the user explicitly asks about menus.")
    lines.append(f"  Preferences: {total_prefs} set")
    if has_ratings:
        all_ratings = db.get_ratings(limit=10000)
        lines.append(f"  Ratings: {len(all_ratings)} items rated")
    if has_meals:
        all_meals = db.get_meal_history(limit=10000)
        lines.append(f"  Meals logged: {len(all_meals)}")
        loc_freq = db.get_location_frequency()
        if loc_freq:
            top = max(loc_freq, key=loc_freq.get)
            lines.append(f"  Top location: {top} ({loc_freq[top]} visits)")

    # Show profile (exclude on_campus from display — it's internal)
    display_prefs = {k: v for k, v in prefs.items() if k != "on_campus"}
    if display_prefs:
        lines.append("\n  Current profile:")
        for key, values in display_prefs.items():
            lines.append(f"    {key}: {', '.join(values)}")

    return "\n".join(lines)


@mcp.tool()
async def check_time() -> str:
    """Get current time context for dining decisions.

    Returns the current time, day, meal period, and any urgency notes.
    Use this to factor time into food recommendations — it matters whether it's
    7 AM on a Monday or 8 PM on a Saturday.
    """
    # Fetch real hours for accurate urgency info
    try:
        locations_data = await api.get_locations()
        upcoming_meals = api.parse_upcoming_meals(locations_data)
    except Exception:
        upcoming_meals = None

    ctx = api.get_time_context(upcoming_meals=upcoming_meals)
    lines = [
        f"🕐 {ctx['time']} — {ctx['day']}",
        f"🍽 Current meal: {ctx['meal_type']}",
        f"📌 {ctx['urgency']}",
    ]
    if ctx["is_weekend"]:
        lines.append("📅 Weekend — some locations may have different hours or serve brunch")
    return "\n".join(lines)


@mcp.tool()
async def whats_open() -> str:
    """Check what Purdue dining locations are currently open.

    Returns a list of open locations with their current meal period and hours.
    Use this when someone asks "what's open?" or "where can I eat right now?"
    """
    locations = await api.get_locations()
    meals = api.parse_upcoming_meals(locations)
    now = datetime.now().astimezone()
    current_time = now.strftime("%I:%M %p")

    open_now = [m for m in meals if m["is_open"]]
    coming_soon = [m for m in meals if m["start"] > now]

    lines = []
    if open_now:
        lines.append(f"Open right now ({current_time}):\n")
        for m in sorted(open_now, key=lambda x: x["location"]):
            mins_left = int((m["end"] - now).total_seconds() / 60)
            closing_note = f" — closes in {mins_left} min!" if mins_left <= 30 else ""
            lines.append(f"• {m['location']} — {m['meal_name']} ({m['start_fmt']} - {m['end_fmt']}){closing_note}")
    else:
        lines.append(f"Nothing is open right now ({current_time}).")

    if coming_soon:
        # Show up to 5 upcoming meals
        upcoming = sorted(coming_soon, key=lambda x: x["start"])[:5]
        lines.append("\nComing up:")
        for m in upcoming:
            lines.append(f"• {m['location']} — {m['meal_name']} ({m['start_fmt']} - {m['end_fmt']})")

    if not open_now and not coming_soon:
        lines.append("No upcoming meals found. Dining may be closed for the day or the API doesn't have today's data yet.")

    return "\n".join(lines)


@mcp.tool()
async def get_menu(location: str, meal: Optional[str] = None) -> str:
    """Get today's menu for a specific dining location.

    Args:
        location: Dining location name (e.g. "wiley", "ford", "earhart", "hillenbrand",
                  "windsor", "1bowl", "petes za", "sushi boss", or full names)
        meal: Optional meal filter — "breakfast", "lunch", or "dinner"

    Use this when someone asks "what's at Wiley?" or "show me the Ford menu".
    """
    menu_data = await api.get_menu(location)

    if "error" in menu_data:
        return menu_data["error"]

    items = api.extract_items_from_menu(menu_data, meal_filter=meal)
    loc_name = menu_data.get("Location", location)

    if not items:
        meal_note = f" for {meal}" if meal else ""
        return f"No items found at {loc_name}{meal_note} today. The location may be closed."

    # Group by meal then station
    by_meal: dict[str, dict[str, list[str]]] = {}
    for item in items:
        mt = item["meal_type"]
        st = item["station"]
        by_meal.setdefault(mt, {}).setdefault(st, []).append(item["name"])

    lines = [f"📋 Menu for {loc_name} — {date.today().strftime('%A, %B %d')}:\n"]
    for meal_name, stations in by_meal.items():
        lines.append(f"\n🍽 {meal_name}")
        for station_name, item_names in stations.items():
            lines.append(f"  [{station_name}]")
            for name in item_names:
                lines.append(f"    • {name}")

    return "\n".join(lines)


@mcp.tool()
async def what_should_i_eat(
    location: Optional[str] = None,
    mood: Optional[str] = None,
    hunger_level: Optional[int] = None,
) -> str:
    """Get personalized food recommendations based on your preferences and what's available.

    This is THE main tool. Use it when someone says "I'm hungry", "what should I eat?",
    "I'm at Wiley", or anything about deciding what to eat.

    Args:
        location: Optional — specific dining location. If not given, checks all open locations.
        mood: Optional — how the user feels (e.g. "tired", "stressed", "great", "lazy")
        hunger_level: Optional — 1 (snack) to 5 (starving)
    """
    # Fetch real hours from the API for accurate time context
    try:
        locations_data = await api.get_locations()
        upcoming_meals = api.parse_upcoming_meals(locations_data)
    except Exception:
        upcoming_meals = None

    time_ctx = api.get_time_context(upcoming_meals=upcoming_meals)
    current_meal = time_ctx["meal_type"]
    # "Late Lunch" isn't an API meal type — map to what the API uses
    meal_filter = "Lunch" if current_meal == "Late Lunch" else current_meal
    all_items = []

    if location:
        resolved = api.resolve_location(location)
        if not resolved:
            return f"I don't recognize '{location}'. Try: wiley, ford, earhart, hillenbrand, windsor, 1bowl, petes za, sushi boss"
        menu = await api.get_menu(location)
        if "error" not in menu:
            all_items = api.extract_items_from_menu(menu, meal_filter=meal_filter)
            # If no items for current meal, try without filter
            if not all_items:
                all_items = api.extract_items_from_menu(menu)
    else:
        # Check all dining courts
        for loc in api.LOCATIONS:
            try:
                menu = await api.get_menu(loc)
                if "error" not in menu:
                    items = api.extract_items_from_menu(menu, meal_filter=meal_filter)
                    if not items:
                        items = api.extract_items_from_menu(menu)
                    all_items.extend(items)
            except Exception:
                continue

    if not all_items:
        return "No menus available right now. Dining courts may be closed or the API might not have today's data yet."

    recs = get_recommendations(all_items, mood=mood, hunger_level=hunger_level, top_n=5)

    if not recs:
        return "Couldn't find recommendations matching your preferences. Try broadening your criteria."

    # Format response
    lines = []
    context_parts = []
    if location:
        context_parts.append(f"at {recs[0].get('location', location)}")
    if mood:
        context_parts.append(f"feeling {mood}")
    if hunger_level:
        hunger_labels = {1: "snack mode", 2: "a little hungry", 3: "hungry", 4: "very hungry", 5: "starving"}
        context_parts.append(hunger_labels.get(hunger_level, f"hunger {hunger_level}/5"))

    header = f"🕐 {time_ctx['time']} — {current_meal}"
    if time_ctx["urgency"] != "normal hours":
        header += f" ⚠️ {time_ctx['urgency']}"
    lines.append(header)

    rec_header = "Here's what I'd recommend"
    if context_parts:
        rec_header += f" ({', '.join(context_parts)})"
    rec_header += ":"
    lines.append(rec_header)
    lines.append("")

    for i, rec in enumerate(recs, 1):
        loc_tag = f" @ {rec['location']}" if not location else ""
        station_tag = f" [{rec['station']}]" if rec.get('station') else ""
        score_tag = f" (score: {rec['score']})" if rec['score'] > 0 else ""
        lines.append(f"{i}. {rec['name']}{loc_tag}{station_tag}{score_tag}")
        if rec.get("reasons"):
            for reason in rec["reasons"]:
                lines.append(f"   → {reason}")
        lines.append("")

    prefs = db.get_preferences()
    total_ratings = len(db.get_ratings(limit=1000))
    if total_ratings == 0:
        lines.append("💡 Tip: Rate items with rate_item or log meals with log_meal to get better recommendations!")

    return "\n".join(lines)


@mcp.tool()
def log_meal(
    item_name: str,
    location: Optional[str] = None,
    meal_type: Optional[str] = None,
    mood: Optional[str] = None,
    hunger_level: Optional[int] = None,
    rating: Optional[int] = None,
    notes: Optional[str] = None,
) -> str:
    """Log a meal you ate. This builds your taste profile over time.

    Use this when someone says "I had the chicken at Wiley" or "just ate at Ford, it was great".

    Args:
        item_name: What you ate (e.g. "Grilled Chicken", "Pasta Primavera")
        location: Where you ate (e.g. "wiley", "ford")
        meal_type: "breakfast", "lunch", or "dinner" (auto-detected if not given)
        mood: How you're feeling (e.g. "tired", "great", "stressed")
        hunger_level: 1 (snack) to 5 (starving)
        rating: 1-5 rating of the food
        notes: Any additional notes
    """
    if meal_type is None:
        meal_type = api.get_current_meal_type()

    resolved_loc = None
    if location:
        resolved_loc = api.resolve_location(location) or location

    db.log_meal(
        item_name=item_name,
        location=resolved_loc,
        meal_type=meal_type,
        mood=mood,
        hunger_level=hunger_level,
        notes=notes,
    )

    if rating is not None:
        rating = max(1, min(5, rating))
        db.add_rating(item_name, rating, location=resolved_loc, meal_type=meal_type)

    parts = [f"Logged: {item_name}"]
    if resolved_loc:
        parts.append(f"at {resolved_loc}")
    if mood:
        parts.append(f"(feeling {mood})")
    if rating:
        parts.append(f"— rated {rating}/5")

    return " ".join(parts) + " ✓"


@mcp.tool()
def rate_item(item_name: str, rating: int, location: Optional[str] = None) -> str:
    """Rate a food item from 1-5. Quick way to build your taste profile.

    Use this when someone says "the chicken was great" or "that pasta was a 2".

    Args:
        item_name: Name of the food item
        rating: 1 (terrible) to 5 (amazing)
        location: Optional — where you had it
    """
    rating = max(1, min(5, rating))
    resolved_loc = None
    if location:
        resolved_loc = api.resolve_location(location) or location

    db.add_rating(item_name, rating, location=resolved_loc)

    stars = "⭐" * rating
    return f"Rated {item_name} {rating}/5 {stars}"


@mcp.tool()
def set_preference(key: str, value: str) -> str:
    """Set a dietary preference, allergy, or food preference.

    Use this to set up the user's profile. Examples:
    - set_preference("allergy", "peanuts")
    - set_preference("dislike", "tofu")
    - set_preference("favorite", "grilled chicken")
    - set_preference("favorite_location", "wiley")
    - set_preference("vegetarian", "true")
    - set_preference("diet", "high protein")

    Args:
        key: Preference type — "allergy", "dislike", "favorite", "favorite_location",
             "vegetarian", "diet", or any custom key
        value: The preference value
    """
    db.set_preference(key, value)
    return f"Preference set: {key} = {value} ✓"


@mcp.tool()
def remove_preference(key: str, value: Optional[str] = None) -> str:
    """Remove a preference.

    Args:
        key: Preference type to remove
        value: Specific value to remove. If not given, removes ALL preferences with this key.
    """
    db.remove_preference(key, value)
    if value:
        return f"Removed preference: {key} = {value}"
    return f"Removed all '{key}' preferences"


@mcp.tool()
def get_preferences() -> str:
    """View your current food preference profile.

    Shows allergies, dislikes, favorites, dietary preferences, etc.
    """
    prefs = db.get_preferences()
    if not prefs:
        return "No preferences set yet. Use set_preference to configure allergies, dislikes, favorites, etc."

    lines = ["Your food profile:\n"]
    labels = {
        "allergy": "🚫 Allergies",
        "dislike": "👎 Dislikes",
        "favorite": "❤️ Favorites",
        "favorite_location": "📍 Favorite Locations",
        "vegetarian": "🌱 Vegetarian",
        "diet": "🎯 Diet Goals",
    }
    for key, values in prefs.items():
        label = labels.get(key, f"📝 {key.title()}")
        lines.append(f"{label}: {', '.join(values)}")

    return "\n".join(lines)


@mcp.tool()
def get_history(limit: int = 10) -> str:
    """View your recent meal history and ratings.

    Args:
        limit: Number of recent entries to show (default 10)
    """
    meals = db.get_meal_history(limit=limit)
    ratings = db.get_ratings(limit=limit)

    if not meals and not ratings:
        return "No meal history yet. Use log_meal or rate_item to start building your profile!"

    lines = []

    if meals:
        lines.append("Recent meals:\n")
        for m in meals:
            parts = [f"• {m['item_name']}"]
            if m.get("location"):
                parts.append(f"@ {m['location']}")
            if m.get("meal_type"):
                parts.append(f"({m['meal_type']})")
            if m.get("mood"):
                parts.append(f"— feeling {m['mood']}")
            if m.get("timestamp"):
                parts.append(f"[{m['timestamp'][:10]}]")
            lines.append(" ".join(parts))

    if ratings:
        lines.append("\nRecent ratings:\n")
        for r in ratings:
            stars = "⭐" * r["rating"]
            loc = f" @ {r['location']}" if r.get("location") else ""
            lines.append(f"• {r['item_name']}: {stars}{loc}")

    # Summary stats
    all_ratings = db.get_ratings(limit=10000)
    loc_freq = db.get_location_frequency()
    if all_ratings or loc_freq:
        lines.append(f"\n📊 Stats: {len(all_ratings)} ratings, {len(db.get_meal_history(limit=10000))} meals logged")
        if loc_freq:
            top_loc = max(loc_freq, key=loc_freq.get)
            lines.append(f"📍 Most visited: {top_loc} ({loc_freq[top_loc]} times)")

    return "\n".join(lines)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
