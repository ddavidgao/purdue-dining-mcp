"""Lightweight remote MCP server — no database, just Purdue API proxy.

Preferences live in the client (ChatGPT memory, Claude project instructions).
This server only fetches live menus and hours from the Purdue HFS API.
"""

import os
from datetime import date, datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import api

mcp = FastMCP(
    name="purdue-dining",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    instructions="""You are a Purdue dining assistant. You help students decide what to eat.

Use the tools to check live menus and hours. NEVER guess or make up menu items.
If a tool call fails, say so honestly — don't fabricate fallback menus.

The user's preferences (allergies, favorites, dislikes, diet goals) are stored
on YOUR side (in memory/project instructions), not on this server. Use them
to filter the menu results you get back from the tools.""",
)


@mcp.tool()
async def whats_open() -> str:
    """Check what Purdue dining locations are currently open right now.

    Returns open locations with meal period and hours, plus upcoming meals.
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
            lines.append(
                f"• {m['location']} — {m['meal_name']} "
                f"({m['start_fmt']} - {m['end_fmt']}){closing_note}"
            )
    else:
        lines.append(f"Nothing is open right now ({current_time}).")

    if coming_soon:
        upcoming = sorted(coming_soon, key=lambda x: x["start"])[:5]
        lines.append("\nComing up:")
        for m in upcoming:
            lines.append(
                f"• {m['location']} — {m['meal_name']} "
                f"({m['start_fmt']} - {m['end_fmt']})"
            )

    if not open_now and not coming_soon:
        lines.append("No upcoming meals found. Dining may be closed for the day.")

    return "\n".join(lines)


@mcp.tool()
async def get_menu(location: str, meal: Optional[str] = None) -> str:
    """Get today's menu for a specific dining location.

    Args:
        location: Dining location name (e.g. "wiley", "ford", "earhart",
                  "hillenbrand", "windsor", "1bowl", "petes za", "sushi boss")
        meal: Optional meal filter — "breakfast", "lunch", or "dinner"
    """
    menu_data = await api.get_menu(location)

    if "error" in menu_data:
        return menu_data["error"]

    items = api.extract_items_from_menu(menu_data, meal_filter=meal)
    loc_name = menu_data.get("Location", location)

    if not items:
        meal_note = f" for {meal}" if meal else ""
        return f"No items found at {loc_name}{meal_note} today. The location may be closed."

    by_meal: dict[str, dict[str, list[str]]] = {}
    for item in items:
        mt = item["meal_type"]
        st = item["station"]
        by_meal.setdefault(mt, {}).setdefault(st, []).append(item["name"])

    lines = [f"Menu for {loc_name} — {date.today().strftime('%A, %B %d')}:\n"]
    for meal_name, stations in by_meal.items():
        lines.append(f"\n{meal_name}")
        for station_name, item_names in stations.items():
            lines.append(f"  [{station_name}]")
            for name in item_names:
                lines.append(f"    • {name}")

    return "\n".join(lines)


def main():
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
