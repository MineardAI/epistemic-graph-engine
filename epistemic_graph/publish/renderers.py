from __future__ import annotations

import csv
import html
from io import StringIO
from typing import Any, Iterable, Mapping, Sequence

from ..hash_utils import canonical_json


def _path_value(row: Mapping[str, Any], field: str) -> Any:
    current: Any = row
    for part in field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _stringify(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    return canonical_json(value)


def _markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _row_sort_key(row: Mapping[str, Any], sort_keys: Sequence[str]) -> tuple[tuple[int, Any], ...]:
    components: list[tuple[int, Any]] = []
    for field in sort_keys:
        value = _path_value(row, field)
        if value is None or value == "":
            components.append((0, ""))
        elif isinstance(value, bool):
            components.append((1, 1 if value else 0))
        elif isinstance(value, (int, float)):
            components.append((2, value))
        elif isinstance(value, str):
            components.append((3, value))
        else:
            components.append((4, canonical_json(value)))
    return tuple(components)


def _sorted_rows(rows: Iterable[Mapping[str, Any]], sort_keys: Sequence[str]) -> list[Mapping[str, Any]]:
    return sorted((dict(row) for row in rows), key=lambda row: _row_sort_key(row, sort_keys))


def render_markdown_table(
    *,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    sort_keys: Sequence[str] = (),
) -> str:
    ordered_rows = _sorted_rows(rows, sort_keys)
    rendered_rows = ordered_rows or [{column: None for column in columns}]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rendered_rows:
        lines.append(
            "| "
            + " | ".join(
                _markdown_escape(_stringify(_path_value(row, column))) for column in columns
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_csv_table(
    *,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    sort_keys: Sequence[str] = (),
) -> str:
    ordered_rows = _sorted_rows(rows, sort_keys)
    rendered_rows = ordered_rows or [{column: None for column in columns}]
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(columns))
    for row in rendered_rows:
        writer.writerow([_stringify(_path_value(row, column)) for column in columns])
    return buffer.getvalue()


def render_html_table(
    *,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    sort_keys: Sequence[str] = (),
) -> str:
    ordered_rows = _sorted_rows(rows, sort_keys)
    rendered_rows = ordered_rows or [{column: None for column in columns}]
    lines = ["<table>", "  <thead>", "    <tr>"]
    for column in columns:
        lines.append(f"      <th>{html.escape(column)}</th>")
    lines.extend(["    </tr>", "  </thead>", "  <tbody>"])
    for row in rendered_rows:
        lines.append("    <tr>")
        for column in columns:
            lines.append(f"      <td>{html.escape(_stringify(_path_value(row, column)))}</td>")
        lines.append("    </tr>")
    lines.extend(["  </tbody>", "</table>", ""])
    return "\n".join(lines)
