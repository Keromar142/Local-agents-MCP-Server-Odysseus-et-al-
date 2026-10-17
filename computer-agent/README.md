# Local Computer Agent

Two fully local computer-using agents + an **MCP server** that works perfectly with **Odysseus** (the self-hosted AI workspace).

Both the standalone agents and the MCP server share the same **permission system**, so dangerous actions (delete, move, overwrite, run code, etc.) always ask for confirmation unless you explicitly allow them for the session or permanently.

---

## Recommended way: MCP Server for Odysseus

This is the cleanest integration. Odysseus already speaks MCP, so you just point it at our server.

### 1. Install (one time)

```bash
git clone https://github.com/YOUR_USERNAME/computer-agent.git
cd computer-agent
# No extra packages required for the lightweight tools + MCP server
```

### 2. Add the MCP server inside Odysseus

1. Open Odysseus → **Settings → MCP** (or Integrations → MCP)
2. Click **Add server**
3. Choose transport: **stdio**
4. Fill in:

| Field     | Value                                      |
|-----------|--------------------------------------------|
| Name      | `computer-agent` (or any name you like)   |
| Command   | `python` (or full path to your python)    |
| Args      | `["/full/path/to/computer-agent/mcp_server.py"]` |

Example Args on Linux/macOS:
```json
["/home/you/computer-agent/mcp_server.py"]
```

Example on Windows:
```json
["C:\\Users\\you\\computer-agent\\mcp_server.py"]
```

5. Save → Odysseus will start the server and discover the tools.

### 3. Tools that appear

- `find_files` – search the whole machine + USB by name
- `list_dir`
- `get_file_info`
- `get_drives`
- `delete_file` (asks permission)
- `move_file` (asks permission)
- `create_file` / `write_file` (asks permission)
- `run_python` (asks permission)

When a high-risk tool is called, a clear console prompt appears in the terminal where the MCP server is running (or in Odysseus logs depending on how it is launched). You can allow once / for the session / permanently / deny.

---

## Two Standalone Agents (optional)

| Version | Best for | Requires | Capabilities |
|---------|----------|----------|--------------|
| **Lightweight** (`lightweight_agent/`) | Very small models (1.7B–4B) | Almost nothing | Find any file (incl. USB), list dirs, create/move/delete, run Python |
| **Vision** (`vision_agent/`) | Machines that can run a multimodal model | `mss`, `Pillow`, `pyautogui` + vision LLM | Everything above + see the screen, click, type, scroll |

### Quick start for standalone agents

```bash
# Lightweight (text-only)
python -m lightweight_agent.agent

# Vision (needs extra packages)
pip install -r requirements.txt
python -m vision_agent.agent
```

You must implement the tiny `call_local_model()` / `call_vision_model()` functions (examples for Ollama are in the source comments).

---

## Permission System (shared by everything)

When the agent/MCP wants to do something risky you see:

```
════════════════════════════════════════════════════════════════
  AGENT REQUESTS PERMISSION
════════════════════════════════════════════════════════════════
  Tool:        delete_file
  Action:      Delete: /home/user/old_report.pdf
────────────────────────────────────────────────────────────────
  [y]  Yes – allow this once
  [s]  Yes – allow for the rest of this session
  [p]  Yes – allow permanently
  [n]  No
  [d]  Deny permanently (never ask again)
════════════════════════════════════════════════════════════════
```

- Permanent decisions are stored in `agent_permissions.json`
- Every decision is logged to `agent_permission_log.jsonl`
- You can open an interactive manager at any time:

```python
from permissions import permissions
permissions.interactive_menu()
```

---

## Project Structure

```
computer-agent/
├── mcp_server.py                 ← MCP server for Odysseus (recommended)
├── permissions.py                ← Shared permission + logging system
├── requirements.txt              ← Only needed for the vision agent
├── README.md
├── LICENSE
├── .gitignore
├── lightweight_agent/            ← Standalone text-only agent
│   ├── agent.py
│   └── tools.py
└── vision_agent/                 ← Standalone screenshot + mouse agent
    ├── agent.py
    └── tools.py
```

---

## Safety Notes

- High-risk tools always start in “Ask” mode.
- You can permanently deny any tool.
- Vision agent has `pyautogui.FAILSAFE = True` (move mouse to top-left corner to abort).
- `run_python` uses a restricted set of builtins.
- The MCP server prints permission prompts to **stderr** / the terminal that launched it so they stay visible.

---

## License

MIT
