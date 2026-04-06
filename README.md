# purdue-dining

An MCP server that connects to Purdue's dining API and gives you personalized food recommendations. It learns what you like over time — after a few weeks of rating meals, you just say "I'm hungry" and it knows what to suggest.

## Install

### Claude Code (recommended)

Add to your Claude Code settings (project or global):

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

Restart Claude Code. The tools will be available immediately.

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

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

### From source

```bash
git clone https://github.com/ddavidgao/purdue-dining-mcp.git
cd purdue-dining-mcp
uv run purdue-dining
```

## Tools

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

1. **First time?** The server detects you're new and walks you through a quick setup — allergies, favorites, dislikes, where you usually eat.

2. **Use it daily.** Say things like:
   - "I'm at Wiley, what should I eat?"
   - "What's open right now?"
   - "I just had the chicken tacos at Ford, they were great" (logs + rates)
   - "I'm stressed and starving, what to eat?"

3. **It gets smarter.** The recommendation engine scores items based on:
   - Your direct ratings
   - Fuzzy matching (rates "Chicken Tacos" highly? It'll suggest "Wiley's Chicken Tacos")
   - Where you eat most often
   - Mood patterns (what you eat when stressed vs. happy)
   - Hunger level (hearty items when you're starving)
   - Novelty bonus (tries to surface things you haven't had)

## Supported locations

All 12 Purdue dining locations:
- **Dining Courts:** Earhart, Ford, Hillenbrand, Wiley, Windsor
- **On-the-GO:** Earhart, Ford, Windsor, Lawson
- **Quick Bites:** 1bowl at Meredith, Pete's Za at Tarkington, Sushi Boss at Meredith

## Data

Your preferences and meal history are stored locally in a SQLite database at `data/preferences.db` inside the package directory. Nothing is sent anywhere except the Purdue dining API (public, no auth).

## License

MIT
