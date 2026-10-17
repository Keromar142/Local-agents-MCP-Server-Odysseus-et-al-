"""
Tools for the Vision agent (screenshot + mouse/keyboard version).
Requires a multimodal model that can understand images.
"""

from pathlib import Path
import shutil
import subprocess
import sys
import io
import base64

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from permissions import permissions

try:
    import mss
    from PIL import Image
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.25
except ImportError:
    print("Warning: mss / Pillow / pyautogui not installed. Vision features will not work.")
    mss = None
    Image = None
    pyautogui = None


def take_screenshot_b64() -> str:
    """Capture the primary monitor and return a base64 PNG string."""
    if mss is None or Image is None:
        raise RuntimeError("mss and Pillow are required for screenshots")

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary
        img = sct.grab(monitor)
        pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


def click(x: int, y: int, button: str = "left") -> dict:
    if pyautogui is None:
        return {"status": "error", "message": "pyautogui not available"}
    pyautogui.click(x, y, button=button)
    return {"status": "success", "message": f"Clicked ({x}, {y})"}


def type_text(text: str, interval: float = 0.05) -> dict:
    if pyautogui is None:
        return {"status": "error", "message": "pyautogui not available"}
    pyautogui.write(text, interval=interval)
    return {"status": "success", "message": f"Typed: {text[:50]}..."}


def press_key(key: str) -> dict:
    if pyautogui is None:
        return {"status": "error", "message": "pyautogui not available"}
    pyautogui.press(key)
    return {"status": "success", "message": f"Pressed {key}"}


def scroll(amount: int) -> dict:
    if pyautogui is None:
        return {"status": "error", "message": "pyautogui not available"}
    pyautogui.scroll(amount)
    return {"status": "success", "message": f"Scrolled {amount}"}


def move_mouse(x: int, y: int) -> dict:
    if pyautogui is None:
        return {"status": "error", "message": "pyautogui not available"}
    pyautogui.moveTo(x, y)
    return {"status": "success", "message": f"Moved mouse to ({x}, {y})"}


# ---------- File system tools (same permission system) ----------

def list_dir(path: str = ".") -> list:
    try:
        return [str(p) for p in Path(path).iterdir()]
    except Exception as e:
        return [f"Error: {e}"]


def read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {e}"


def safe_delete(path: str) -> dict:
    description = f"Delete: {path}"
    if not permissions.request_permission("delete_file", description):
        return {"status": "cancelled", "message": "User denied deletion"}

    try:
        p = Path(path)
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        else:
            return {"status": "error", "message": "Path does not exist"}
        return {"status": "success", "message": f"Deleted {path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def safe_move(src: str, dst: str) -> dict:
    description = f"Move '{src}' → '{dst}'"
    if not permissions.request_permission("move_file", description):
        return {"status": "cancelled", "message": "User denied move"}

    try:
        shutil.move(src, dst)
        return {"status": "success", "message": f"Moved {src} → {dst}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def safe_create_file(path: str, content: str = "") -> dict:
    description = f"Create file: {path}"
    if not permissions.request_permission("create_file", description):
        return {"status": "cancelled", "message": "User denied create"}

    try:
        Path(path).write_text(content, encoding="utf-8")
        return {"status": "success", "message": f"Created {path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def safe_write_file(path: str, content: str) -> dict:
    description = f"Write/overwrite file: {path}"
    if not permissions.request_permission("write_file", description):
        return {"status": "cancelled", "message": "User denied write"}

    try:
        Path(path).write_text(content, encoding="utf-8")
        return {"status": "success", "message": f"Wrote {path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def safe_run_shell(command: str) -> dict:
    description = f"Run shell command: {command}"
    if not permissions.request_permission("run_shell", description):
        return {"status": "cancelled", "message": "User denied shell command"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
