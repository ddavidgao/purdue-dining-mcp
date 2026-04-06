# purdue-dining

A personalized Purdue dining assistant that pulls live menus and tells you what to eat. Works with Claude, ChatGPT, or as a local MCP server.

## Quick Setup

### ChatGPT (works on phone)

1. Go to [chat.openai.com](https://chat.openai.com) → Explore GPTs → Create
2. Paste the contents of [`PROMPT.md`](PROMPT.md) into the **Instructions** field
3. Under **Actions**, click "Create new action" and import [`openapi.yaml`](openapi.yaml)
4. Set Authentication to **None**
5. Save and use — works on ChatGPT mobile app too

Share your GPT link with friends and they can use it immediately.

### Claude (works on phone)

1. Go to [claude.ai](https://claude.ai) → Projects → New Project
2. Paste the contents of [`PROMPT.md`](PROMPT.md) into the **Custom Instructions**
3. Start chatting — Claude will fetch menus when you ask

Note: Claude uses web fetch to call the API. No Actions/plugins needed.

### Claude Code / Claude Desktop (MCP — full features)

The MCP server adds persistent preference tracking, meal history, ratings, and a recommendation engine on top of the base experience.

Add to your settings:

```json
{
  "mcpServers": {
    "purdue-dining": {
      "command": "uvx",
      "args": ["purdue-dining"]
    }
  }
}
```

## What You Get

| Setup | Live Menus | Preferences | Meal History | Ratings | Works on Phone |
|-------|-----------|-------------|--------------|---------|----------------|
| ChatGPT GPT | Yes (API Actions) | In conversation | In conversation | In conversation | Yes |
| Claude Project | Yes (web fetch) | In project instructions | In conversation | In conversation | Yes |
| MCP Server | Yes | SQLite (persistent) | SQLite (persistent) | SQLite (persistent) | No (desktop only) |

## MCP Server Tools

If using the MCP server, you get these additional tools:

| Tool | What it does |
|---|---|
| `get_started` | First-time onboarding — walks you through setting up preferences |
| `what_should_i_eat` | Personalized recommendations based on your history + live menus |
| `get_menu` | Full menu for any dining location |
| `whats_open` | Which locations are open right now (real-time from API) |
| `check_time` | Current meal period + urgency based on actual closing times |
| `log_meal` | Log what you ate with mood/rating/notes |
| `rate_item` | Quick 1-5 rating for a food item |
| `set_preference` | Set allergies, dislikes, favorites, diet goals |
| `get_preferences` | View your current food profile |
| `get_history` | See your meal history and stats |

## How it works

1. **First time?** Tell it your allergies, favorites, dislikes, where you usually eat, and diet goals.

2. **Use it daily.** Say things like:
   - "I'm hungry"
   - "I'm at Wiley, what should I eat?"
   - "What's open right now?"
   - "The chicken tacos at Ford were great"

3. **It gets smarter** (MCP version). The recommendation engine scores items based on your ratings, eating patterns, mood, hunger level, and location preferences.

## Supported locations

All 12 Purdue dining locations:
- **Dining Courts:** Earhart, Ford, Hillenbrand, Wiley, Windsor
- **On-the-GO:** Earhart, Ford, Windsor, Lawson
- **Quick Bites:** 1bowl at Meredith, Pete's Za at Tarkington, Sushi Boss at Meredith

## Files

- `PROMPT.md` — Universal prompt for ChatGPT/Claude setup
- `openapi.yaml` — OpenAPI spec for ChatGPT Actions (Purdue dining API)
- `src/` — MCP server source code

## Data

MCP server stores preferences locally in SQLite. ChatGPT/Claude setups keep preferences in conversation context. The only external call is to the [Purdue HFS dining API](https://api.hfs.purdue.edu/menus/v2) (public, no auth required).

## License

MIT
