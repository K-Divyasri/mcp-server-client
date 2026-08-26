# Deploy checklist -- PersonalKB (MCP server + client)

This is the project's "definition of done." Walk it top to bottom. Do not tick a box you
have not actually verified by running the command -- "should work" is not the same as
"works." Commands assume you are inside `build_from_scratch/` unless noted.

## Runs locally, offline

- [ ] Fresh virtual environment, dependencies installed cleanly:
      `python -m venv .venv ; .\.venv\Scripts\Activate.ps1` then `pip install -r requirements.txt`
- [ ] `python generate_data.py` prints `data\notes.db: 15 notes, 18 tags`.
- [ ] `python -m mcp_kb tools` lists 4 tools, 1 resource (`notebook://summary`), 1 prompt
      (`research_prompt`), with no API key set.
- [ ] `python -m mcp_kb ask "what's the weather in Paris" --verbose` answers offline and
      shows the `get_weather` call in its trace.
- [ ] `pytest -q` is all green: **40 passed, 1 skipped** (the skip is the real-Claude test,
      correctly self-skipping with no `ANTHROPIC_API_KEY` set).

## Secrets are clean

- [ ] `build_from_scratch/.gitignore` contains `.env`, `__pycache__/`, `.pytest_cache/`,
      `data/`, `*.egg-info/`; the root `.gitignore` contains `.env` and
      `build_from_scratch/.env` too.
- [ ] `git status` shows `.env` is NOT tracked.
- [ ] `git ls-files` contains no bare `.env` (only `.env.example`).
- [ ] No API key is hardcoded anywhere in the source.

## Pushed to GitHub

- [ ] Repo created empty on github.com (no auto README/license), named `personal-kb-mcp`
      (or your own choice), public.
- [ ] `git init` -> `git add .` -> `git commit` -> `git branch -M main` ->
      `git remote add origin ...` -> `git push -u origin main`, run from the **project
      root** (`24-mcp-server-client/`), not from inside `build_from_scratch/`.
- [ ] Files visible on the GitHub repo page after a refresh.

## CI is green and keyless

- [ ] `.github/workflows/tests.yml` (copied from `hosting/github_actions/tests.yml`) is
      committed and pushed.
- [ ] The Actions tab shows a completed green run: install deps, `generate_data.py`, then
      `pytest tests -q` reporting 40 passed, 1 skipped.
- [ ] Confirmed no secret is configured on the repo for this workflow, and none was needed.

## Connected to Claude Desktop and verified a real tool call

This is the one that actually matters most for this project -- do not skip it.

- [ ] `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
      `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) has a
      `personal-kb` entry under `mcpServers`, with `command` as the full, absolute path to
      your Python executable and `env.PYTHONPATH` as the full, absolute path to your own
      `build_from_scratch/` folder.
- [ ] Claude Desktop was fully quit and restarted (not just the window closed) after saving
      the config.
- [ ] A new chat shows PersonalKB's tools under the tool/hammer indicator.
- [ ] Asked "search my notes about python" (or similar) and watched Claude actually call
      `search_notes` and answer from the real result, with your approval prompt shown.
- [ ] Asked "what's the weather in Paris" (or similar) and watched Claude call
      `get_weather`.
- [ ] If something did not show up: checked `%APPDATA%\Claude\logs\mcp-server-personal-kb.log`
      (Windows) or the macOS equivalent under `~/Library/Logs/Claude/`, and re-ran the exact
      `command` + `PYTHONPATH` combination directly in a terminal to see the real error.

## (Optional) Deployed the HTTP server remotely

- [ ] `docker build -t personal-kb-mcp .` succeeds locally, with `hosting/Dockerfile`
      copied into `build_from_scratch/` first.
- [ ] `docker run -p 8765:8765 personal-kb-mcp` starts; `curl http://127.0.0.1:8765/mcp`
      returns 406 (correct: it needs a real POST + `initialize` body, not a browser GET).
- [ ] A real MCP client (or `python -m mcp_kb ask --transport http --http-url
      http://127.0.0.1:8765/mcp "..."`) completes a real `initialize` handshake against the
      running container.
- [ ] The copied `Dockerfile` was removed from `build_from_scratch/` again afterward, so
      that folder stays exactly the pytest-verified package.
- [ ] (Only if you actually deployed it) a public URL from Render or Cloud Run answers the
      same way a local container does, and `MCP_KB_HTTP_HOST=0.0.0.0` is set (it is, by
      default, in `hosting/Dockerfile`).

## Repo pinned

- [ ] `personal-kb-mcp` is pinned on your GitHub profile so it shows up first.

When every box is ticked, the project is done and presentable. The Claude Desktop section
is the one worth actually screenshotting or recording -- it is the part no other project on
this track can show.
