from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = ROOT / "Docs" / "conversations.json"
SAMPLE_PATH = ROOT / "tests" / "fixtures" / "sample_conversations.json"


def _load_archive() -> list[dict]:
    return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))


def _has_required_edges(conversation: dict) -> bool:
    nodes = conversation.get("mapping", {})
    has_branch = any(len(node.get("children") or []) > 1 for node in nodes.values())
    has_attachment = any((node.get("message") or {}).get("metadata", {}).get("attachments") for node in nodes.values())
    has_hidden = any((node.get("message") or {}).get("metadata", {}).get("is_visually_hidden_from_conversation") for node in nodes.values())
    has_tool = any((node.get("message") or {}).get("author", {}).get("role") == "tool" for node in nodes.values())
    return has_branch and has_attachment and has_hidden and has_tool


def main() -> int:
    archive = _load_archive()
    selected = sorted(
        (conversation for conversation in archive if _has_required_edges(conversation)),
        key=lambda conversation: (
            len(conversation.get("mapping", {})),
            str(conversation.get("conversation_id") or conversation.get("id") or ""),
            str(conversation.get("title") or ""),
        ),
    )
    if not selected:
        raise RuntimeError("No archive conversation contains all required edge cases.")

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_PATH.write_text(
        json.dumps([selected[0]], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
