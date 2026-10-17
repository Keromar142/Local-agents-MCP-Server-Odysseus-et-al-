# computer-agent

Local file and code tools for **Odysseus**, served as an MCP server over stdio. The repo also includes two standalone console agents (lightweight and vision).

## Tools

| Tool | What it does | Needs approval |
|---|---|---|
| `find_files` | Search files by name across all drives, or under a root folder | No |
| `list_dir` | List a directory | No |
| `get_file_info` | Size, type and modified time | No |
| `get_drives` | List drives and mount points, including USB | No |
| `delete_file` | Delete a file or folder | **Yes** |
| `move_file` | Move or rename a file or folder | **Yes** |
| `create_file` | Create a text file | **Yes** |
| `write_file` | Write or overwrite a text file | **Yes** |
| `run_python` | Run a short Python snippet in a restricted environment | **Yes** |

## How approval works

A tool that needs approval first replies with `confirmation_required` and a description of the action. Odie asks you in chat. If you approve, it calls the tool again with `confirm=true`. You can also save permanent choices in `agent_permissions.json`, which sits next to the script.

## Setup in Odysseus

1. Clone this repo somewhere the Odysseus container can see it. Odysseus runs in Docker, so mount the folder into the container.
2. Go to **Odysseus → Settings → MCP → Add server**:

| Field | Value |
|---|---|
| Transport | `stdio` |
| Command | `python` |
| Args | `["/path/to/computer-agent/mcp_server.py"]` |

3. Save. Odysseus will discover all 9 tools.

> **Note:** The tools run inside the Odysseus container, so they only see the container's files and any folders you mount into it, not your whole PC.

## Standalone agents (optional)

These run in a console with their own y/s/p/n/d permission prompt.

```bash
pip install -r requirements.txt   # mss, Pillow, pyautogui are only needed for the vision agent
python lightweight_agent/agent.py
python vision_agent/agent.py
```

Before running either one, set the model name in `call_local_model()` or `call_vision_model()` to a model you have in Ollama (for example `qwen3:8b`).

## Files

- `mcp_server.py`: MCP server entry point
- `permissions.py`: permission manager and audit log (`agent_permission_log.jsonl`)
- `lightweight_agent/`: text-only agent and the shared file tools
- `vision_agent/`: screenshot-based agent

## License

MIT
