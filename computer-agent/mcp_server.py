#!/usr/bin/env python3
"""
Computer Agent MCP Server
=========================
Exposes the safe file / code tools (with permission system) over the
Model Context Protocol (stdio).

This is the recommended way to use the computer-agent tools inside
Odysseus (Settings → MCP → Add server).

Usage (from the computer-agent directory):
    python mcp_server.py

Odysseus will start it as a subprocess and discover the tools.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Dict, List

# Make sure we can import the local modules
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from permissions import permissions
from lightweight_agent.tools import (
    find_files,
    list_dir,
    get_file_info,
    safe_delete,
    safe_move,
    safe_create_file,
    safe_write_file,
    run_python,
    get_all_drives,
)


# ---------------------------------------------------------------------------
# Tool definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "find_files",
        "description": (
            "Search for files by name (case-insensitive) across the whole machine "
            "or a specific root. Also searches USB / external drives when root is omitted. "
            "Returns a list of full paths (max 50 by default)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Substring to search for in the filename"},
                "root": {"type": "string", "description": "Optional starting directory. Omit to search all drives including USB."},
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of extensions (e.g. [\"pdf\", \"docx\"])",
                },
                "max_results": {"type": "integer", "description": "Maximum number of results (default 50)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_dir",
        "description": "List the contents of a directory. Returns a list of full paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default \".\")"},
            },
        },
    },
    {
        "name": "get_file_info",
        "description": "Get basic information about a file or directory (size, type, modified time).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full path to the file or directory"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_drives",
        "description": "Return a list of all available drives / mount points, including USB and external drives.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "delete_file",
        "description": (
            "Delete a file or folder. HIGH-RISK: the user will be prompted for confirmation "
            "unless they have previously granted permanent or session permission."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full path to delete"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": (
            "Move or rename a file/folder. Requires user confirmation unless previously allowed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "src": {"type": "string", "description": "Source path"},
                "dst": {"type": "string", "description": "Destination path"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "create_file",
        "description": "Create a new text file with optional content. Requires confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full path of the new file"},
                "content": {"type": "string", "description": "Optional text content"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a text file. Requires confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full path of the file"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute a short Python snippet in a restricted environment. "
            "Requires user confirmation. Useful for calculations or small data transforms."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code to run"},
            },
            "required": ["code"],
        },
    },
]


# Map tool name → actual Python function
HANDLERS = {
    "find_files": find_files,
    "list_dir": list_dir,
    "get_file_info": get_file_info,
    "get_drives": get_all_drives,
    "delete_file": safe_delete,
    "move_file": safe_move,
    "create_file": safe_create_file,
    "write_file": safe_write_file,
    "run_python": run_python,
}


# ---------------------------------------------------------------------------
# Minimal MCP JSON-RPC over stdio
# ---------------------------------------------------------------------------

# --- Odysseus/MCP confirmation flow -------------------------------------------
from permissions import Permission as _Perm

for _t in TOOLS:
    _ask = permissions.defaults.get(_t["name"]) == _Perm.ASK
    _t["annotations"] = {"readOnlyHint": not _ask, "destructiveHint": _ask}
    if _ask:
        _t["inputSchema"].setdefault("properties", {})["confirm"] = {
            "type": "boolean",
            "description": "Set true ONLY after the user explicitly approved this exact action in chat.",
        }


def _prep(arguments: dict) -> dict:
    arguments = dict(arguments)
    permissions.mcp_confirm = bool(arguments.pop("confirm", False))
    permissions.needs_confirm = None
    return arguments


def _wrap(result):
    if permissions.needs_confirm:
        return {"status": "confirmation_required",
                "action": permissions.needs_confirm,
                "message": "Ask the user to approve this action. If they say yes, call the same tool again with confirm=true."}
    return result


def send(msg: dict) -> None:
    """Write a single JSON-RPC message to stdout (followed by newline)."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> None:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "computer-agent",
                    "version": "1.0.0",
                },
            }
            send({"jsonrpc": "2.0", "id": req_id, "result": result})

        elif method == "notifications/initialized":
            # No response needed for notifications
            return

        elif method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            })

        elif method == "tools/call":
            name = params.get("name")
            arguments = _prep(params.get("arguments") or {})

            if name not in HANDLERS:
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                })
                return

            try:
                result = HANDLERS[name](**arguments)
                # MCP expects content array
                text = json.dumps(_wrap(result), indent=2, default=str)
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                })
            except Exception as e:
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}],
                        "isError": True,
                    },
                })

        elif method == "ping":
            send({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            # Method not found
            if req_id is not None:
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })

    except Exception as e:
        if req_id is not None:
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            })


def main() -> None:
    # Important: keep stdout clean for JSON-RPC. All logging goes to stderr.
    print("computer-agent MCP server started (stdio)", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            handle_request(req)
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {line[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"Unhandled error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
