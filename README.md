# purdue-dining

A personalized Purdue dining assistant that pulls live menus and tells you what to eat. Works on your phone with ChatGPT or Claude.

## Quick Setup

### ChatGPT (easiest — works on phone)

1. Open ChatGPT → Explore GPTs
2. Search **"Purdue Dining"** by David Gao
3. Start chatting — say "I'm hungry"

Has memory — it remembers your food preferences across conversations.

### Claude (works on phone)

1. Go to [claude.ai](https://claude.ai) → Settings → Connectors
2. Add a custom connector with this URL:
   ```
   https://purdue-dining-mcp-production.up.railway.app/mcp
   ```
3. Open Claude on your phone — the connector syncs automatically
4. Say "I'm hungry"

### Claude Code / Claude Desktop (local MCP — full features)

The local MCP server adds persistent preference tracking, meal history, ratings, and a recommendation engine.

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

| Setup | Live Menus | Preferences | Works on Phone |
|-------|-----------|-------------|----------------|
| ChatGPT GPT | Yes | ChatGPT memory (persistent) | Yes |
| Claude Connector | Yes | In conversation | Yes |
| Local MCP Server | Yes | SQLite (persistent) | No (desktop) |

## How it works

Say things like:
- "I'm hungry"
- "What's open right now?"
- "What's at Wiley for dinner?"
- "The Korean pork at Earhart was great" (saves to memory on ChatGPT)

It checks the live Purdue dining API, filters by what's actually open, and recommends real menu items with station names. Never guesses or makes up food.

## Supported locations

All Purdue dining locations:
- **Dining Courts:** Earhart, Ford, Hillenbrand, Wiley, Windsor
- **On-the-GO:** Earhart, Ford, Windsor, Lawson
- **Quick Bites:** 1bowl at Meredith, Pete's Za at Tarkington, Sushi Boss at Meredith

## Architecture

The remote server (`src/purdue_menu/remote.py`) is a lightweight proxy deployed on Railway. It serves:
- **MCP protocol** at `/mcp` — for Claude connectors
- **REST API** at `/api/whats-open` and `/api/menu/{location}` — for ChatGPT GPT Actions

No database, no user data stored. Preferences live in the AI client. The server just proxies the [Purdue HFS dining API](https://api.hfs.purdue.edu/menus/v2) (public, no auth).

## Privacy

- Zero user data stored on the server
- No API keys or authentication required
- No logging of requests
- Preferences are stored by ChatGPT/Claude on their side, not ours
- Open source — read every line of code

## License

MIT
