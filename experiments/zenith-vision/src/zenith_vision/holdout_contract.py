from __future__ import annotations

import re
from pathlib import Path


_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,119}$")


def resolve_holdout_directories(root: Path, value: str) -> tuple[Path, ...]:
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError("holdout contract requires four distinct segments")
    if any(_NAME.fullmatch(name) is None for name in names):
        raise ValueError("invalid holdout segment name")
    resolved_root = root.resolve()
    paths = tuple((resolved_root / name).resolve() for name in names)
    if any(path.parent != resolved_root or not path.is_dir() or path.is_symlink() for path in paths):
        raise ValueError("holdout segment is unavailable or unsafe")
    return paths
