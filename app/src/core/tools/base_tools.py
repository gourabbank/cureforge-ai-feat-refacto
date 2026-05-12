from langchain_core.tools import tool
from app.src.core.tools.hypothesis_bank import HYPOTHESIS_BANK_TOOLS
import os


@tool
def read_file(
    path: str, all: bool = False, start: int | None = None, finish: int | None = None
) -> str:
    """Read file contents. Returns full file if all=True, else lines [start:finish] (1-indexed, inclusive-exclusive).

    Args:
        path: Absolute file path (str).
        all: Return entire file if True; otherwise use start/finish (bool).
        start: First line number to read, 1-indexed (int, default None).
        finish: Line after last line to read, 1-indexed (int, default None).
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if all:
        return "".join(lines)

    start = 0 if start is None else start
    finish = len(lines) if finish is None else finish
    return "".join(lines[start:finish])


@tool
def write_file(path: str, content: str) -> str:
    """Write content to file, overwriting existing. Returns "ok" on success.

    Args:
        path: Absolute file path (str).
        content: Text to write to file (str).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return "ok"


@tool
def modify_file(
    path: str, target: str, replacement: str, all_instances: bool = False
) -> str:
    """Replace text in file. Returns "ok" on success.

    Args:
        path: Absolute file path (str).
        target: Text to find (str).
        replacement: Text to insert (str).
        all_instances: Replace all matches if True, else first match only (bool).
    """
    if target == replacement:
        return "Target and replacement are the same, no changes made."

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if all_instances:
        content = content.replace(target, replacement)
    else:
        content = content.replace(target, replacement, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return "ok"


@tool
def get_file_length(path: str) -> int:
    """Return line count in file.

    Args:
        path: Absolute file path (str).
    """
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _build_tree(root: str, prefix: str = "") -> list[str]:
    items = sorted(os.listdir(root))
    lines = []

    for i, name in enumerate(items):
        path = os.path.join(root, name)
        connector = "└── " if i == len(items) - 1 else "├── "
        lines.append(prefix + connector + name)

        if os.path.isdir(path):
            extension = "    " if i == len(items) - 1 else "│   "
            lines.extend(_build_tree(path, prefix + extension))

    return lines


@tool
def list_dir(path: str) -> str:
    """Return directory tree as indented text.

    Args:
        path: Absolute directory path (str).
    """
    if not os.path.exists(path):
        return "path not found"

    return "\n".join([os.path.basename(path)] + _build_tree(path))


all_base_tools = [
    read_file,
    write_file,
    modify_file,
    get_file_length,
    list_dir,
    *HYPOTHESIS_BANK_TOOLS,
]
