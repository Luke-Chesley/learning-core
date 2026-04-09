import subprocess
from langchain_core.tools import tool

from .common import resolve_workspace_only_path, resolve_workspace_path


@tool
def read_file(path: str) -> str:
    """Read the full contents of a file. Returns the text or an error message."""
    resolved = resolve_workspace_path(path)
    try:
        return resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found: {resolved}"
    except Exception as e:
        return f"Error reading {resolved}: {e}"
