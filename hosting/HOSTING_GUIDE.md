# Hosting PersonalKB (the MCP server + client)

Every other project on this AI track ends its hosting story with a public Streamlit URL.
This one is different, on purpose: PersonalKB is a CLI and a library, not a web app, and
its most convincing demo is not a browser tab at all. It is the real Claude Desktop app on
your own machine, talking to your own server, calling your own tools live, in a normal
chat. That costs nothing, needs no deploy, and is the single most compelling thing you can
show in an interview or record for a README GIF. Everything else here (GitHub, CI, an
optional remote HTTP deploy) is worth doing too, but Step 3 is the one to actually go do
first.

Here is the whole plan:

1. **A GitHub repo** -- your code, online, public, with a README that lands the project fast.
2. **Local install** -- get `mcp_kb` running on your own machine with the seeded notes database.
3. **Connect it to Claude Desktop** -- the star of the show. Real MCP, real tool calls, zero cost.
4. **Keyless CI** -- GitHub runs the 40-test suite on every push, no secret required anywhere.
5. **(Stretch) Remote HTTP hosting** -- a Dockerfile so someone else could point an MCP
   client at a real URL, the roadmap's own stretch goal ("publish it so others can install it").

A note on layout before you start: the repo root is the real, tested code itself --
`mcp_kb/`, `tests/`, `generate_data.py`, and `requirements.txt` sit directly at the root,
next to this `hosting/` folder. Every command below runs from that repo root.

---

## Step 0 -- Install Git and make a GitHub account

Git tracks versions of your files on your laptop. GitHub is the website that stores a copy
online so other people (and recruiters) can see it. Different things: Git is local, GitHub
lives on the internet. You need both.

1. Install Git from https://git-scm.com/download/win, clicking Next through every screen.
2. Open a **new** PowerShell window (it has to be new to pick up the install) and check:

   ```powershell
   git --version
   ```

3. Sign up at https://github.com with your real email (`mathuransada@gmail.com` is the one
   on file), verify it, and pick a username you would be happy putting on a CV.
4. Tell Git who you are, once per machine:

   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "mathuransada@gmail.com"
   ```

---

## Step 1 -- Know what goes in the repo and what must not

`.gitignore` already exists and excludes the things that should never be
committed:

```
__pycache__/
*.pyc
.pytest_cache/
data/
.env
*.egg-info/
```

The two worth understanding:

- **`.env`** -- if you ever set `ANTHROPIC_API_KEY` to try `ask --real`, this file holds a
  real secret. A key is a password. Commit it and it is on the public internet forever
  (Git keeps history; deleting it in a later commit does not erase it, and bots scrape
  GitHub for leaked keys within minutes). The repo ships `.env.example`
  instead, listing the variable names with blank values -- that one is safe and meant to be
  committed.
- **`data/`** -- the seeded `notes.db` is generated, not authored, so it is not committed.
  `generate_data.py` recreates it deterministically (same 15 notes, same 18 tags) on any
  machine, any time -- that is Step 2 below.

You will also want the repo root `.gitignore` (the same file as above) to carry a few more
common lines:

```
.env
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
.ipynb_checkpoints/
```

Rule of thumb: source code, config, docs, and the knowledge/notebooks/labs material go in;
secrets and machine-specific junk (venvs, caches, the generated notes database) stay out.

---

## Step 2 -- Install it locally and seed the data

From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python generate_data.py
```

`generate_data.py` is idempotent (safe to re-run) and prints what it made:

```
data\notes.db: 15 notes, 18 tags
```

Confirm the package actually works before you touch GitHub or Claude Desktop:

```powershell
python -m mcp_kb tools
python -m mcp_kb ask "what's the weather in Paris" --verbose
pytest -q
```

You should see 4 tools (`search_notes`, `add_note`, `list_tags`, `get_weather`), 1 resource
(`notebook://summary`), 1 prompt (`research_prompt`); the Paris question routes to
`get_weather` and answers "Paris: clear sky, 18C (offline demo data)"; and pytest reports
**40 passed, 1 skipped** (the skip is the one test that needs a real `ANTHROPIC_API_KEY` --
completely normal with no key set).

If you would rather install it as an editable package (so `mcp_kb` is importable from any
folder, not just from the repo root), use `pip install -e .` instead of `pip
install -r requirements.txt`. Either way works for everything in this guide; the editable
install is only worth doing if you plan to run `python -m mcp_kb ...` from somewhere other
than the repo root.

Then push it, the same way as every other project on this track:

```powershell
git init
git add .
git commit -m "Initial commit: PersonalKB, an MCP server + client"
git status
git ls-files
```

Check `git status` says `nothing to commit, working tree clean`, and scan `git ls-files`
for a bare `.env` (there should not be one -- `.env.example` is fine and expected). Then, on
github.com, create a new **empty** repository (no auto README/.gitignore/license -- name it
something like `personal-kb-mcp`), and:

```powershell
git branch -M main
git remote add origin https://github.com/YOURNAME/personal-kb-mcp.git
git push -u origin main
```

The first push opens a browser sign-in -- do it. Refresh the GitHub page; your files (and
this README) are there.

---

## Step 3 -- Connect it to the real Claude Desktop app (the star of the show)

This is the payoff. Every other project on this track fakes an LLM call offline by default
and only spends real money once you flip a `--real` flag. This project's actual point is
the MCP *protocol* layer, and that layer has never been mocked anywhere in this codebase --
every test spawns a real server and speaks real JSON-RPC. Wiring the real server into the
real Claude Desktop app is the natural conclusion of that: no more subprocess spawned by a
test, an actual model in an actual chat window deciding to call your tools.

Official references for this step (read these if anything below is unclear or if Claude
Desktop's UI has changed since this was written):

- https://modelcontextprotocol.io/docs/develop/connect-local-servers
- https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop

### 3a. Prerequisites

- Claude Desktop installed (https://claude.ai/download). Check Claude menu -> "Check for
  Updates..." so you are on a current build.
- Step 2 already done: dependencies installed, `python generate_data.py` run at least once.
- Find the exact Python executable you want Claude Desktop to launch. Claude Desktop spawns
  the `command` you give it directly -- it does not go through your shell profile or a
  virtualenv activation script -- so "just `python`" only works if that resolves correctly
  with no terminal open at all. Get the full path:

  ```powershell
  python -c "import sys; print(sys.executable)"
  ```

  On the machine this guide was written on, that printed
  `C:\Users\divya\miniconda3\python.exe`. Yours will differ; use your own.

### 3b. Edit the config file

The config lives at:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Easiest way to find/create it: open Claude Desktop -> Claude menu -> Settings -> Developer
tab -> Edit Config. That creates the file if it does not exist yet and opens it in your
default editor.

Add a `personal-kb` entry under `mcpServers`. Here is the exact block, with the two paths
you need to replace:

```json
{
  "mcpServers": {
    "personal-kb": {
      "command": "C:\\Users\\divya\\miniconda3\\python.exe",
      "args": ["-m", "mcp_kb.server"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\mcp-server-client"
      }
    }
  }
}
```

Replace `command` with the exact path Step 3a printed, and replace the `PYTHONPATH` value
with the absolute path to **your own** clone of this repo (the repo root). Windows JSON needs
double backslashes (`\\`) in paths, as shown above.

**Why the `PYTHONPATH` entry, and not a `cwd` field:** the official docs' own config
examples (both linked above) only ever show three keys on a server entry -- `command`,
`args`, and `env` -- there is no `cwd` key anywhere in them. Without it, `python -m
mcp_kb.server` needs to find the `mcp_kb` package somehow, and the only two ways to do that
without an editable install are (a) run with the working directory already set to
the repo root, which Claude Desktop's config has no field for, or (b) tell Python
where to look via `PYTHONPATH`, which it does have a field for (`env`). This was verified
directly: running `python -m mcp_kb.server` from an unrelated folder with no `PYTHONPATH`
set fails with `ModuleNotFoundError: No module named 'mcp_kb'`; setting `PYTHONPATH` to the
absolute repo root path fixes it from any working directory. The docs'
own troubleshooting section uses this exact same trick for a different problem (a
`${APPDATA}`-not-expanding issue with an `npx`-based server), by adding the resolved value
into that server's own `env` block -- same idea, same mechanism, different variable.

You do **not** need to set `MCP_KB_DB_PATH`. The server resolves its own database path
from its own file location (`data/notes.db`), not from the process's
working directory, so it finds the right file regardless of how Claude Desktop launched it.
Two env vars worth adding if you want them, in the same `env` block as `PYTHONPATH`:

- `"MCP_KB_LIVE_WEATHER": "1"` -- switches `get_weather` from the offline demo table to a
  real, keyless call to open-meteo.com.
- You do **not** need `ANTHROPIC_API_KEY` here. That variable is only read by `mcp_kb`'s own
  `ask --real` CLI command, for running the agent loop standalone outside Claude Desktop.
  Inside Claude Desktop, Claude Desktop *is* the model -- your server only ever supplies
  tools, resources, and a prompt template; it never calls an LLM itself.

Save the file.

### 3c. Restart Claude Desktop completely

Not just close the window -- quit it fully (check the system tray / menu bar for a
lingering process) and reopen it. The app only reads `claude_desktop_config.json` at
startup.

### 3d. Verify it

After restarting, open a **new** chat. Look for a small tool/hammer indicator near the
message box -- click it and you should see PersonalKB's 4 tools listed. Then just ask it
something:

> search my notes about python

or

> what's the weather in Paris

Claude should visibly decide to call `search_notes` or `get_weather` (Claude Desktop shows
you the call and asks for your approval before running it, same as any other local MCP
server), then answer using the real result that came back over the real protocol. If you
ask it to remember something ("add a note that I prefer oat milk, tag it 'preferences'"),
it can call `add_note` too -- that one actually writes into your real local `notes.db`, so
expect it to show up on your next `search_notes` call.

### Troubleshooting

- **Server does not show up / no hammer icon.** Restart Claude Desktop completely first --
  it only reads the config at launch. Then re-check the config JSON: a stray trailing
  comma or an unescaped backslash is enough to make the whole file fail to parse. Confirm
  both paths (`command` and the `PYTHONPATH` value) are absolute, not relative, and that
  they actually exist on disk.
- **Check the logs.** Claude Desktop writes MCP-specific logs to:
  - Windows: `%APPDATA%\Claude\logs\` (`mcp.log` for general connection info,
    `mcp-server-personal-kb.log` for this server's own stderr output -- the name is derived
    from the key you used in `mcpServers`).
  - macOS: `~/Library/Logs/Claude/`.

  On Windows, a quick way to look: `type "%APPDATA%\Claude\logs\mcp-server-personal-kb.log"`.
- **Prove the command works outside Claude Desktop first.** Open a terminal and run the
  exact same command Claude Desktop would run, with the same `PYTHONPATH` set:

  ```powershell
  $env:PYTHONPATH = "C:\path\to\your\mcp-server-client"
  C:\path\to\your\python.exe -m mcp_kb.server
  ```

  If this crashes or prints `ModuleNotFoundError`, fix that first -- Claude Desktop will
  hit the exact same error, just silently, in its own log file instead of your terminal.
- **Tool calls fail silently, or the model never offers to call a tool.** Check the
  per-server log above for a Python traceback. If the server started fine but Claude just
  never reaches for a tool, try being explicit ("use your PersonalKB tools to search my
  notes for...") -- like any tool-use decision, it is the model choosing, not guaranteed.
- **Using conda or a venv?** Whatever `python` resolves to in your normal terminal is
  usually *not* what Claude Desktop will run, because it never activates anything -- it
  just executes the literal `command` path you gave it. Always use the full path from
  `sys.executable` (Step 3a), never a bare `"python"`, unless you have specifically put
  that exact interpreter on the system-wide PATH that Windows uses for all processes (not
  just your shell's).

---

## Step 4 -- Keyless CI

The suite is 40 tests, all offline, and one that self-skips without a key -- there is
nothing for CI to need a secret for. Copy the workflow already in this folder:

```powershell
mkdir .github\workflows
copy hosting\github_actions\tests.yml .github\workflows\tests.yml
git add .github\workflows\tests.yml
git commit -m "Add CI: keyless pytest on every push"
git push
```

Open the repo's **Actions** tab. You should see it install `requirements.txt`,
run `generate_data.py`, then `pytest tests -q`, ending
green with **40 passed, 1 skipped**. No `ANTHROPIC_API_KEY` or any other secret is
configured anywhere in the workflow, and none is needed: `tests/test_agent_real.py` is
decorated `@pytest.mark.skipif(not has_api_key(), ...)`, so it skips itself the instant the
key is absent -- which it always is on a public runner unless you deliberately add one.

Once it is green, grab the status badge (Actions page -> `...` -> **Create status badge**)
and paste it at the top of the root `README.md`.

---

## Step 5 (stretch) -- Remote HTTP hosting

The roadmap's own stretch goal is "publish it so others can install it" -- meaning point a
*remote* MCP client at a real URL instead of spawning the server as a local subprocess.
`mcp_kb.server --http` already speaks the streamable-HTTP transport for exactly this; the
piece that was missing is a container and somewhere free to run it.

**Be honest with yourself about scope here:** this section is written and verified as far
as "the Docker image builds, runs, and answers a real MCP request" -- that part was
actually tested (see the note in `hosting/Dockerfile`'s header). Actually clicking through
a hosting provider's own signup/dashboard flow and getting a public URL live is something
only you can do with your own account, and is genuinely optional for this project -- the
Claude Desktop demo in Step 3 is already the strongest, cost-free proof this thing works.
Treat this section as documented-and-ready, not deployed-for-you.

### 5a. Build and run it locally first

```powershell
copy hosting\Dockerfile Dockerfile
docker build -t personal-kb-mcp .
docker run -p 8765:8765 personal-kb-mcp
```

Then, from another terminal, confirm it is really speaking MCP (a plain browser GET will
correctly fail -- MCP needs a POST with a specific `Accept` header):

```powershell
curl http://127.0.0.1:8765/mcp
```

Expect **406** (wrong method/headers -- this is correct and matches the protocol, not a
bug). A real client (or `mcp_kb ask --transport http --http-url http://127.0.0.1:8765/mcp`)
completes a proper `initialize` handshake against the same URL and gets back
`protocolVersion: "2025-06-18"` and `serverInfo.name: "PersonalKB"`. Delete the copied
`Dockerfile` out of the repo root again afterward (`hosting/` is where it lives).

### 5b. Deploy it -- Render (recommended, matches the rest of this AI track)

This track's CI/CD project (`18-cicd-cloud-deployment/`) settled on Render's free tier as
the default Docker host, so this project uses the same one for consistency:

1. Push the root `Dockerfile` (the copy from 5a) to your GitHub repo.
2. Sign up free at https://render.com (sign in with GitHub -- no credit card needed).
3. **New** -> **Web Service**, connect your repo, leave **Root Directory**
   blank (the repo root), runtime **Docker**. Render finds the `Dockerfile` there and builds
   it.
4. Leave the health-check path **blank**. This server has no plain `GET /` route -- only
   `POST /mcp` with specific headers -- so a default health check expecting a 200 on `/`
   would misreport the service as unhealthy even while it is working correctly. Render's
   Docker web services do not require a health-check path; they only need the container to
   be listening on the port they inject.
5. Render sets its own `PORT` environment variable at deploy time. You do not need to do
   anything about it: the Dockerfile's `CMD` already reads `${PORT}` at container start
   (falling back to 8765 only when it is unset), verified locally by running the same image
   with `-e PORT=9999` and confirming it rebinds to 9999 with no rebuild.
6. Deploy. Render gives you a URL like `https://personal-kb-mcp.onrender.com`. Point a real
   MCP client at `https://personal-kb-mcp.onrender.com/mcp` the same way you would at the
   local `http://127.0.0.1:8765/mcp` URL.

Free-tier honesty: Render's free web services spin down after about 15 minutes of no
traffic and take roughly 30 to 60 seconds to wake back up on the next request. That is
normal free-tier behavior, not a bug -- mention it if you are demoing the live URL to
someone.

### Alternative -- Google Cloud Run

If you would rather use GCP:

```powershell
gcloud run deploy personal-kb-mcp --source . --region us-central1 --allow-unauthenticated
```

`--source .` hands Cloud Run the directory with the (copied-in) `Dockerfile` and builds it
for you. Same `PORT` story as Render: Cloud Run injects its own value and the Dockerfile
already handles it. Set `MCP_KB_LIVE_WEATHER=1` via `--set-env-vars` if you want the remote
deploy to use real weather data too.

---

## Step 6 -- Pin the repo

On your GitHub profile page, **Customize your pins**, tick `personal-kb-mcp`. Now it is one
of the first things a recruiter sees.

---

## Common Git mistakes (troubleshooting)

**You committed `.env` by accident.** Treat the key as compromised -- go revoke/rotate it
at https://console.anthropic.com immediately if you had pushed. Then untrack it (this does
not erase it from history, which is exactly why you rotate rather than rely on deleting):

```powershell
git rm --cached .env
git commit -m "Remove committed .env"
git push
```

**`error: failed to push` / push rejected.** The remote has commits yours does not, usually
because GitHub auto-added a README/license when you created the repo:

```powershell
git pull origin main --rebase
git push
```

Next time, create the repo completely empty.

**Authentication fails on push.** GitHub does not accept your account password in the
terminal anymore. Easiest: install the GitHub CLI (https://cli.github.com), then `gh auth
login`. Or generate a Personal Access Token (Settings -> Developer settings -> Tokens
(classic), `repo` scope) and paste it as the password when prompted.

**`git: command not found` right after installing.** Close every terminal window and open a
fresh one.
