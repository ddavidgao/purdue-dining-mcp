"""Purdue dining API client."""

import httpx
from datetime import datetime, date
from typing import Optional

BASE_URL = "https://api.hfs.purdue.edu/menus/v2"

# API "Name" field — this is what goes in the URL path
LOCATIONS = [
    "1bowl at Meredith Hall",
    "Earhart",
    "Earhart On-the-GO!",
    "Ford",
    "Ford On-the-GO!",
    "Hillenbrand",
    "Lawson On-the-GO!",
    "Pete's Za at Tarkington Hall",
    "Sushi Boss at Meredith Hall",
    "Wiley",
    "Windsor",
    "Windsor On-the-GO!",
]

# Friendly aliases → API Name
LOCATION_ALIASES: dict[str, str] = {
    "earhart": "Earhart",
    "earhart dining court": "Earhart",
    "ford": "Ford",
    "ford dining court": "Ford",
    "hillenbrand": "Hillenbrand",
    "hillenbrand dining court": "Hillenbrand",
    "wiley": "Wiley",
    "wiley dining court": "Wiley",
    "windsor": "Windsor",
    "windsor dining court": "Windsor",
    "1bowl": "1bowl at Meredith Hall",
    "petes": "Pete's Za at Tarkington Hall",
    "petes za": "Pete's Za at Tarkington Hall",
    "pete's za": "Pete's Za at Tarkington Hall",
    "sushi boss": "Sushi Boss at Meredith Hall",
    "earhart otg": "Earhart On-the-GO!",
    "ford otg": "Ford On-the-GO!",
    "windsor otg": "Windsor On-the-GO!",
    "lawson otg": "Lawson On-the-GO!",
    "lawson": "Lawson On-the-GO!",
    "meredith": "1bowl at Meredith Hall",
}


def resolve_location(name: str) -> Optional[str]:
    """Resolve a location alias or partial name to the full API name."""
    lower = name.lower().strip()

    # Check direct aliases
    if lower in LOCATION_ALIASES:
        return LOCATION_ALIASES[lower]

    # Check if it's already a full name
    for loc in LOCATIONS:
        if loc.lower() == lower:
            return loc

    # Fuzzy: check if the input is a substring of any location
    for loc in LOCATIONS:
        if lower in loc.lower():
            return loc

    return None


async def get_locations() -> list[dict]:
    """Fetch all dining locations with their current status."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(f"{BASE_URL}/locations", headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json().get("Location", [])


async def get_menu(location: str, menu_date: Optional[date] = None) -> dict:
    """Fetch menu for a specific location and date.

    Returns the full menu response including meals, stations, and items.
    """
    if menu_date is None:
        menu_date = date.today()

    resolved = resolve_location(location)
    if resolved is None:
        return {"error": f"Unknown location: '{location}'. Known locations: {', '.join(LOCATIONS)}"}

    date_str = menu_date.strftime("%m-%d-%Y")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(
            f"{BASE_URL}/locations/{resolved}/{date_str}/",
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            return {"error": f"No menu data for {resolved} on {date_str} (HTTP {resp.status_code})"}
        return resp.json()


def get_current_meal_type() -> str:
    """Determine the current meal type based on time of day."""
    hour = datetime.now().hour
    if hour < 10:
        return "Breakfast"
    elif hour < 14:
        return "Lunch"
    elif hour < 17:
        return "Late Lunch"
    else:
        return "Dinner"


def get_time_context() -> dict:
    """Get rich time context for recommendations."""
    now = datetime.now()
    hour = now.hour
    day_of_week = now.strftime("%A")
    is_weekend = day_of_week in ("Saturday", "Sunday")

    meal_type = get_current_meal_type()

    # Dining courts typically close around 8-9 PM
    if hour >= 20:
        urgency = "late — dining courts may be closing soon"
    elif hour >= 19:
        urgency = "getting late for dinner"
    elif 14 <= hour < 17:
        urgency = "between meals — limited options"
    else:
        urgency = "normal hours"

    return {
        "time": now.strftime("%I:%M %p"),
        "day": day_of_week,
        "is_weekend": is_weekend,
        "meal_type": meal_type,
        "hour": hour,
        "urgency": urgency,
    }


def extract_items_from_menu(menu_data: dict, meal_filter: Optional[str] = None) -> list[dict]:
    """Extract a flat list of food items from a menu response.

    Each item includes: name, station, meal_type, location, vegetarian, allergens.
    """
    items = []
    location = menu_data.get("Location", "Unknown")

    for meal in menu_data.get("Meals", []):
        meal_name = meal.get("Name", "")
        if meal_filter and meal_name.lower() != meal_filter.lower():
            continue
        if not meal.get("Status") == "Open":
            continue

        for station in meal.get("Stations", []):
            station_name = station.get("Name", "")
            for item in station.get("Items", []):
                items.append({
                    "name": item.get("Name", ""),
                    "station": station_name,
                    "meal_type": meal_name,
                    "location": location,
                    "vegetarian": item.get("IsVegetarian", False),
                    "allergens": [a.get("Name", "") for a in item.get("Allergens", []) if a.get("Value", False)],
                })

    return items
