# Pipeline Co-Pilot container (graded key concept #3: deployability).
# Builds a Cloud Run-ready image that serves the multi-agent system over HTTP.

FROM python:3.12-slim

# Don't buffer stdout/stderr (so logs show up live) and don't write .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first, as their own layer, so code edits don't bust the
# pip cache on every rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the runtime needs: the agent package, the MCP server, and the
# mock CRM data. (.env is git-ignored and intentionally NOT copied — the key is
# injected at deploy time, never baked into the image.)
COPY pipeline_copilot/ ./pipeline_copilot/
COPY mcp_server/ ./mcp_server/
COPY data/ ./data/

# Cloud Run sends traffic to $PORT (default 8080). adk api_server exposes the
# agent as an HTTP API. Shell form is used so $PORT is expanded at runtime.
ENV PORT=8080
EXPOSE 8080
CMD adk api_server . --host 0.0.0.0 --port $PORT
