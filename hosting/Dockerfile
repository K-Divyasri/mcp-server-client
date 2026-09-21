# Dockerfile for the OPTIONAL remote/HTTP hosting path (the roadmap's stretch
# goal: "publish it so others can install it"). This is the one file in
# hosting/ that is not meant to live here permanently -- copy it INTO
# the repo root before building, so the repo root stays exactly
# the pytest-verified package with nothing extra sitting in it:
#
#   copy hosting\Dockerfile Dockerfile
#   docker build -t personal-kb-mcp .
#   docker run -p 8765:8765 personal-kb-mcp
#
# Verified locally (docker build + docker run + a real MCP POST /mcp
# initialize round-trip returning protocolVersion 2025-06-18 and
# serverInfo.name "PersonalKB") -- see HOSTING_GUIDE.md's remote-hosting
# section for exactly how that was checked, and to redo it yourself before
# trusting a public deploy.
FROM python:3.12-slim

WORKDIR /app

# Dependencies before code, so this layer only rebuilds when requirements.txt
# actually changes -- the same layer-caching lesson from every other
# Dockerfile in this AI track.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_kb/ ./mcp_kb/
COPY generate_data.py .

# The streamable-HTTP transport must bind 0.0.0.0, not the 127.0.0.1 default
# baked into mcp_kb/server.py. 127.0.0.1 only accepts connections from
# inside the container itself -- no host, proxy, or router outside the
# container can ever reach it, so a container that skipped this line would
# build and start clean and then look "broken" from the outside for a
# reason that never shows up in the container's own logs.
ENV MCP_KB_HTTP_HOST=0.0.0.0
ENV MCP_KB_HTTP_PORT=8765

# Seed the notes database at build time, so the image is self-contained and
# has notes to search on its very first request (data/ is git-ignored in
# the source repo -- see .gitignore -- this is what
# regenerates it inside the image).
RUN python generate_data.py

EXPOSE 8765

# Shell form on purpose, not exec-form JSON: free container hosts
# (Render, Cloud Run, Fly.io, HF Spaces) inject their OWN "PORT" environment
# variable at container start, a different number depending on the host and
# not chosen by you, and only a shell expands "${PORT}" at runtime. Locally,
# PORT is unset, so this falls back to the 8765 set above. Verified both
# ways: a plain `docker run` binds 8765; `docker run -e PORT=9999 ...` binds
# 9999 instead, with the exact same image.
CMD sh -c "MCP_KB_HTTP_PORT=${PORT:-8765} exec python -m mcp_kb.server --http"
