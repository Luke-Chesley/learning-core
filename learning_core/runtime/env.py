from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from dotenv import dotenv_values

_LOADED_DEFAULT_ENV = False


def _default_search_roots() -> list[Path]:
    package_root = Path(__file__).resolve().parents[2]
    cwd_root = Path.cwd()
    roots: list[Path] = []
    for root in (package_root, cwd_root):
        if root not in roots:
            roots.append(root)
    return roots


def load_runtime_env(
    *,
    search_roots: Iterable[Path] | None = None,
    force: bool = False,
) -> None:
    global _LOADED_DEFAULT_ENV

    if search_roots is None and _LOADED_DEFAULT_ENV and not force:
        return

    merged: dict[str, str] = {}
    roots = list(search_roots) if search_roots is not None else _default_search_roots()

    for root in roots:
        for filename in (".env", ".env.local"):
            path = root / filename
            if not path.is_file():
                continue
            for key, value in dotenv_values(path).items():
                if value is not None:
                    merged[key] = value

    for key, value in merged.items():
        os.environ.setdefault(key, value)

    if search_roots is None:
        _LOADED_DEFAULT_ENV = True
