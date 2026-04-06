FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project
COPY . .

# Install with uv (project mode, creates venv)
RUN uv venv && uv pip install .

# Railway sets PORT env var automatically
ENV MCP_TRANSPORT=streamable-http
ENV PORT=8000

EXPOSE 8000

CMD ["/app/.venv/bin/purdue-dining-remote"]
