"""
Shared Permission Manager for both Vision and Lightweight agents.
Supports session vs permanent permissions, confirmation prompts,
revocation, and full audit logging.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict
from pathlib import Path
import json
import sys
from datetime import datetime
import threading


class Permission(Enum):
    DENIED = "denied"
    ASK = "ask"
    ALLOWED = "allowed"


@dataclass
class ToolPermission:
    level: Permission = Permission.ASK
    permanent: bool = False


@dataclass
class LogEntry:
    timestamp: str
    tool: str
    action: str          # granted_once | granted_session | granted_permanent | denied | revoked
    description: str
    user_choice: str


class PermissionManager:
    def __init__(
        self,
        config_path: str = "agent_permissions.json",
        log_path: str = "agent_permission_log.jsonl",
    ):
        self.config_path = Path(__file__).resolve().parent / config_path
        self.log_path = Path(__file__).resolve().parent / log_path
        self.mcp_confirm = False
        self.needs_confirm = None
        self.session: Dict[str, ToolPermission] = {}
        self.lock = threading.Lock()
        self.load()

        # Sensible defaults – high-risk tools start as ASK
        self.defaults = {
            "delete_file": Permission.ASK,
            "delete_folder": Permission.ASK,
            "overwrite_file": Permission.ASK,
            "run_shell": Permission.ASK,
            "run_python": Permission.ASK,
            "move_file": Permission.ASK,
            "create_file": Permission.ASK,
            "write_file": Permission.ASK,
            "list_dir": Permission.ALLOWED,
            "read_file": Permission.ALLOWED,
            "copy_file": Permission.ALLOWED,
            "find_files": Permission.ALLOWED,
            "get_file_info": Permission.ALLOWED,
            "get_drives": Permission.ALLOWED,
            "screenshot": Permission.ALLOWED,
            "click": Permission.ALLOWED,
            "type": Permission.ALLOWED,
            "press": Permission.ALLOWED,
            "scroll": Permission.ALLOWED,
            "move_mouse": Permission.ALLOWED,
        }

    def load(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                for tool, info in data.items():
                    self.session[tool] = ToolPermission(
                        level=Permission(info["level"]),
                        permanent=info.get("permanent", False),
                    )
            except Exception as e:
                print(f"[Permissions] Warning: could not load config: {e}", file=sys.stderr)

    def save_permanent(self):
        data = {
            tool: {
                "level": perm.level.value,
                "permanent": True,
            }
            for tool, perm in self.session.items()
            if perm.permanent
        }
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def log(self, tool: str, action: str, description: str, user_choice: str):
        entry = LogEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            tool=tool,
            action=action,
            description=description,
            user_choice=user_choice,
        )
        with self.lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.__dict__) + "\n")

    def get(self, tool: str) -> Permission:
        if tool in self.session:
            return self.session[tool].level
        return self.defaults.get(tool, Permission.ASK)

    def set(self, tool: str, level: Permission, permanent: bool = False):
        self.session[tool] = ToolPermission(level=level, permanent=permanent)
        if permanent:
            self.save_permanent()

    def revoke(self, tool: str, permanent: bool = False):
        """Revoke a tool. permanent=True also removes it from permanent storage."""
        if tool in self.session:
            del self.session[tool]
        if permanent and self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if tool in data:
                    del data[tool]
                    self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception:
                pass
        self.log(tool, "revoked", f"Permission revoked (permanent={permanent})", "user")

    def request_permission(self, tool: str, description: str) -> bool:
        current = self.get(tool)

        if current == Permission.DENIED:
            print(f"\n[Permission] DENIED for '{tool}'", file=sys.stderr)
            self.log(tool, "denied", description, "auto-denied")
            return False

        if current == Permission.ALLOWED:
            return True

        # MCP mode (stdin is the JSON-RPC pipe): never prompt on the console.
        # The model must ask the user in chat, then re-call with confirm=true.
        if not sys.stdin.isatty():
            if self.mcp_confirm:
                self.log(tool, "granted_once", description, "mcp_confirm")
                return True
            self.needs_confirm = description
            return False

        # ASK mode – console UI
        print("\n" + "═" * 64, file=sys.stderr)
        print("  AGENT REQUESTS PERMISSION", file=sys.stderr)
        print("═" * 64, file=sys.stderr)
        print(f"  Tool:        {tool}", file=sys.stderr)
        print(f"  Action:      {description}", file=sys.stderr)
        print("─" * 64, file=sys.stderr)
        print("  [y]  Yes – allow this once", file=sys.stderr)
        print("  [s]  Yes – allow for the rest of this session", file=sys.stderr)
        print("  [p]  Yes – allow permanently", file=sys.stderr)
        print("  [n]  No", file=sys.stderr)
        print("  [d]  Deny permanently (never ask again)", file=sys.stderr)
        print("═" * 64, file=sys.stderr)

        while True:
            choice = input("  Your choice: ").strip().lower()
            if choice in {"y", "s", "p", "n", "d"}:
                break
            print("  Invalid choice. Please enter y / s / p / n / d", file=sys.stderr)

        if choice == "y":
            self.log(tool, "granted_once", description, "y")
            return True
        elif choice == "s":
            self.set(tool, Permission.ALLOWED, permanent=False)
            self.log(tool, "granted_session", description, "s")
            return True
        elif choice == "p":
            self.set(tool, Permission.ALLOWED, permanent=True)
            self.log(tool, "granted_permanent", description, "p")
            return True
        elif choice == "d":
            self.set(tool, Permission.DENIED, permanent=True)
            self.log(tool, "denied", description, "d")
            return False
        else:  # n
            self.log(tool, "denied", description, "n")
            return False

    # ---------- Console management UI ----------
    def show_status(self):
        print("\n" + "═" * 64, file=sys.stderr)
        print("  CURRENT PERMISSIONS", file=sys.stderr)
        print("═" * 64, file=sys.stderr)
        all_tools = sorted(set(list(self.defaults.keys()) + list(self.session.keys())))
        for tool in all_tools:
            level = self.get(tool)
            permanent = self.session.get(tool, ToolPermission()).permanent
            flag = " (permanent)" if permanent else ""
            print(f"  {tool:<22} → {level.value}{flag}", file=sys.stderr)
        print("═" * 64, file=sys.stderr)

    def interactive_menu(self):
        """Simple console GUI for managing permissions mid-session."""
        while True:
            print("\n" + "─" * 40, file=sys.stderr)
            print("  PERMISSION MANAGER", file=sys.stderr)
            print("─" * 40, file=sys.stderr)
            print("  1. Show current permissions", file=sys.stderr)
            print("  2. Grant tool for this session", file=sys.stderr)
            print("  3. Grant tool permanently", file=sys.stderr)
            print("  4. Revoke tool (session only)", file=sys.stderr)
            print("  5. Revoke tool permanently", file=sys.stderr)
            print("  6. View recent log", file=sys.stderr)
            print("  0. Exit menu", file=sys.stderr)
            print("─" * 40, file=sys.stderr)

            choice = input("  Select: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.show_status()
            elif choice in {"2", "3", "4", "5"}:
                tool = input("  Tool name: ").strip()
                if not tool:
                    print("  No tool name entered.", file=sys.stderr)
                    continue
                if choice == "2":
                    self.set(tool, Permission.ALLOWED, permanent=False)
                    print(f"  → '{tool}' allowed for this session", file=sys.stderr)
                elif choice == "3":
                    self.set(tool, Permission.ALLOWED, permanent=True)
                    print(f"  → '{tool}' allowed permanently", file=sys.stderr)
                elif choice == "4":
                    self.revoke(tool, permanent=False)
                    print(f"  → '{tool}' revoked for this session", file=sys.stderr)
                elif choice == "5":
                    self.revoke(tool, permanent=True)
                    print(f"  → '{tool}' revoked permanently", file=sys.stderr)
            elif choice == "6":
                self.show_recent_log()
            else:
                print("  Invalid option", file=sys.stderr)

    def show_recent_log(self, n: int = 15):
        if not self.log_path.exists():
            print("  No log entries yet.", file=sys.stderr)
            return
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        print("\n" + "═" * 64, file=sys.stderr)
        print(f"  LAST {min(n, len(lines))} LOG ENTRIES", file=sys.stderr)
        print("═" * 64, file=sys.stderr)
        for line in lines[-n:]:
            try:
                entry = json.loads(line)
                print(
                    f"  {entry['timestamp']} | {entry['action']:<18} | "
                    f"{entry['tool']:<15} | {entry['description'][:40]}"
                )
            except Exception:
                continue
        print("═" * 64, file=sys.stderr)


# Global instance used by both agents
permissions = PermissionManager()
