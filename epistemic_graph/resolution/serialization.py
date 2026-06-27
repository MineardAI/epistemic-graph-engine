from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from ..hash_utils import canonical_json


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(canonical_json(value) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, records: Iterable[Any]) -> None:
    lines = [canonical_json(record) for record in records]
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

