"""
Tools for the Lightweight (text-only) agent.
Designed for very small models (1.7B–4B). No vision / screenshots.
"""

from pathlib import Path
import os
import shutil
import platform
import string
from typing import List, Optional
import sys

# Add parent directory so we can import the shared permissions module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from permissions import permissions


def get_all_drives() -> List[str]:
    """Return all available drives / mount points, including USB / external drives."""
    system = platform.system()
    drives = []

    if system == "Windows":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
    else:
        # Linux / macOS
        drives.append("/")
        for base in ["/media", "/mnt", "/Volumes"]:
            p = Path(base)
            if p.exists():
                try:
                    drives.extend([str(d) for d in p.iterdir() if d.is_dir()])
                except PermissionError:
                    continue

    return drives


def find_files(
    name: str,
    root: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    max_results: int = 50,
) -> List[str]:
    """
    Search for files by name (case-insensitive) across the whole machine
    or a specific root. Also searches USB / external drives when root is None.
    """
    results = []
    roots = [root] if root else get_all_drives()

    name_lower = name.lower()
    extensions = [e.lower().lstrip(".") for e in (extensions or [])]

    for start in roots:
        try:
            for dirpath, _, filenames in os.walk(start):
                for fname in filenames:
                    full = Path(dirpath) / fname
                    if name_lower in fname.lower():
                        if not extensions or full.suffix.lower().lstrip(".") in extensions:
                            results.append(str(full))
                            if len(results) >= max_results:
                                return results
        except (PermissionError, OSError):
            continue  # skip inaccessible folders

    return results


def list_dir(path: str = ".") -> List[str]:
    try:
        return [str(p) for p in Path(path).iterdir()]
    except Exception as e:
        return [f"Error: {e}"]


def get_file_info(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"error": "Path does not exist"}
    try:
        stat = p.stat()
        return {
            "path": str(p),
            "size_bytes": stat.st_size,
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
            "modified": stat.st_mtime,
        }
    except Exception as e:
        return {"error": str(e)}


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


def run_python(code: str) -> dict:
    """
    Execute a small Python snippet.
    Restricted on purpose for safety with tiny models.
    """
    description = f"Run Python code:\n{code[:200]}{'...' if len(code) > 200 else ''}"
    if not permissions.request_permission("run_python", description):
        return {"status": "cancelled", "message": "User denied code execution"}

    # Very basic restricted environment
    safe_builtins = {
        "print": print,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "abs": abs,
        "round": round,
        "True": True,
        "False": False,
        "None": None,
    }

    import io, contextlib
    env = {"__builtins__": safe_builtins}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, env)
        safe_locals = {k: repr(v) for k, v in env.items() if not k.startswith("_")}
        return {"status": "success", "output": buf.getvalue()[:10000], "locals": safe_locals}
    except Exception as e:
        return {"status": "error", "message": str(e)}
