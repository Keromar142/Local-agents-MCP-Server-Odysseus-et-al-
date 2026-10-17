"""
Vision Computer Agent – uses screenshots + a multimodal model
to see the desktop and control mouse/keyboard.
Also includes the same safe file tools and permission system.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from permissions import permissions
from tools import (
    take_screenshot_b64,
    click,
    type_text,
    press_key,
    scroll,
    move_mouse,
    list_dir,
    read_file,
    safe_delete,
    safe_move,
    safe_create_file,
    safe_write_file,
    safe_run_shell,
)

TOOLS = {
    "click": click,
    "type": type_text,
    "press": press_key,
    "scroll": scroll,
    "move_mouse": move_mouse,
    "list_dir": list_dir,
    "read_file": read_file,
    "delete_file": safe_delete,
    "move_file": safe_move,
    "create_file": safe_create_file,
    "write_file": safe_write_file,
    "run_shell": safe_run_shell,
}


def call_vision_model(prompt: str, image_b64: str) -> str:
    """
    Replace this function with your local multimodal backend.

    Example for Ollama:
        import ollama
        response = ollama.chat(
            model="llava",               # or qwen2.5-vl, minicpm-v, etc.
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [image_b64]
            }]
        )
        return response["message"]["content"]
    """
    raise NotImplementedError(
        "Please implement call_vision_model() with your local multimodal model."
    )


def vision_agent(goal: str, max_steps: int = 25):
    history = []
    print(f"\n[Vision Agent] Goal: {goal}")
    print("Move mouse to top-left corner at any time to abort (pyautogui FAILSAFE).")
    print("Type 'menu' during any permission prompt to open the permission manager.\n")

    for step in range(max_steps):
        try:
            screenshot_b64 = take_screenshot_b64()
        except Exception as e:
            print(f"Screenshot failed: {e}")
            break

        prompt = f"""You are a careful computer-using agent that can see the screen.
Goal: {goal}

Previous actions: {history[-4:] if history else "None"}

Respond ONLY with valid JSON:
{{
  "thought": "brief reasoning about what you see and what to do next",
  "action": "tool_name",
  "args": {{}},
  "done": false
}}
Available tools: {list(TOOLS.keys())}
When the goal is complete set "done": true.
"""

        try:
            raw = call_vision_model(prompt, screenshot_b64)
        except NotImplementedError as e:
            print(str(e))
            print("\nExiting. Implement call_vision_model() first.")
            return
        except Exception as e:
            print(f"Model call failed: {e}")
            continue

        try:
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

        if plan.get("done") is True:
            print("\nGoal completed.")
            break

        action = plan.get("action")
        args = plan.get("args", {}) or {}

        if action not in TOOLS:
            print(f"Unknown action: {action}")
            history.append({"action": action, "args": args, "result": "unknown"})
            continue

        print(f"\n→ {action}({args})")
        try:
            result = TOOLS[action](**args)
        except TypeError as e:
            result = {"status": "error", "message": f"Bad arguments: {e}"}
        except Exception as e:
            result = {"status": "error", "message": str(e)}

        print(f"  Result: {result}")
        history.append({
            "action": action,
            "args": args,
            "result": result,
        })

    print("\nAgent finished.")


if __name__ == "__main__":
    print("Vision Computer Agent (screenshots + multimodal model)")
    print("-----------------------------------------------------")
    goal = input("What would you like me to do? ").strip()
    if goal:
        vision_agent(goal)
    else:
        print("No goal entered.")
