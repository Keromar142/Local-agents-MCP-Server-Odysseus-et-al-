"""
Lightweight Computer Agent – text-only version for very small models (1.7B–4B).
No screenshots or vision required. Works by searching the filesystem and running code.
"""

import json
import sys
from pathlib import Path

# Allow importing from parent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from permissions import permissions
from tools import (
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

TOOLS = {
    "find_files": find_files,
    "list_dir": list_dir,
    "get_file_info": get_file_info,
    "delete_file": safe_delete,
    "move_file": safe_move,
    "create_file": safe_create_file,
    "write_file": safe_write_file,
    "run_python": run_python,
    "get_drives": get_all_drives,
}

TOOL_DESCRIPTIONS = """
Available tools:
- find_files(name: str, root: str = None, extensions: list = None, max_results: int = 50)
  Search for files by name across the whole computer (including USB).
- list_dir(path: str = ".")
- get_file_info(path: str)
- delete_file(path: str)
- move_file(src: str, dst: str)
- create_file(path: str, content: str = "")
- write_file(path: str, content: str)
- run_python(code: str)
- get_drives() -> list of all drives including USB / external
"""


def call_local_model(prompt: str) -> str:
    """
    Replace this function with whatever local backend you use
    (Ollama, llama.cpp, LM Studio, etc.).

    Example for Ollama:
        import ollama
        response = ollama.chat(
            model="qwen2:1.5b",   # or your 1.7B / 4B model name
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    """
    raise NotImplementedError(
        "Please implement call_local_model() with your local 1.7B or 4B model."
    )


def lightweight_agent(goal: str, max_steps: int = 15):
    history = []
    print(f"\n[Lightweight Agent] Goal: {goal}")
    print("Type 'menu' during any permission prompt to open the permission manager.\n")

    for step in range(max_steps):
        prompt = f"""You are a careful file and code assistant running on a local computer.
You can only use the tools listed below. Always reply with valid JSON only.

Goal: {goal}

{TOOL_DESCRIPTIONS}

Previous steps: {history[-3:] if history else "None"}

Reply with ONLY a JSON object in this exact format:
{{
  "thought": "short reasoning",
  "tool": "tool_name",
  "args": {{}},
  "done": false
}}
When the goal is fully complete set "done": true and use tool "none".
"""

        try:
            raw = call_local_model(prompt)
        except NotImplementedError as e:
            print(str(e))
            print("\nExiting. Implement call_local_model() first.")
            return
        except Exception as e:
            print(f"Model call failed: {e}")
            continue

        # Try to extract JSON even if the model adds extra text
        try:
            # Find the first { ... } block
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                plan = json.loads(raw[start:end])
            else:
                plan = json.loads(raw)
        except Exception:
            print("Model returned invalid JSON. Raw response:")
            print(raw[:500])
            continue

        if plan.get("done") is True or plan.get("tool") in (None, "none", "done"):
            print("\nGoal completed.")
            break

        tool_name = plan.get("tool")
        args = plan.get("args", {}) or {}

        if tool_name not in TOOLS:
            print(f"Unknown tool: {tool_name}")
            history.append({"tool": tool_name, "args": args, "result": "unknown tool"})
            continue

        print(f"\n→ {tool_name}({args})")
        try:
            result = TOOLS[tool_name](**args)
        except TypeError as e:
            result = {"status": "error", "message": f"Bad arguments: {e}"}
        except Exception as e:
            result = {"status": "error", "message": str(e)}

        print(f"  Result: {str(result)[:400]}")
        history.append({
            "tool": tool_name,
            "args": args,
            "result": result,
        })

    print("\nAgent finished.")


if __name__ == "__main__":
    print("Lightweight Computer Agent (text-only, small models)")
    print("----------------------------------------------------")
    goal = input("What would you like me to do? ").strip()
    if goal:
        lightweight_agent(goal)
    else:
        print("No goal entered.")
