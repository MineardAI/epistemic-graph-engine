from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Iterable

from .hash_utils import canonical_json, normalize_text, sha256_hex, stable_id, truncate_text


@dataclass(frozen=True)
class IngestResult:
    evidence_path: Path
    observations_path: Path
    manifest_path: Path


def load_conversations(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _conversation_key(conversation: dict[str, Any]) -> tuple[str, str]:
    conversation_id = str(conversation.get("conversation_id") or conversation.get("id") or "")
    title = str(conversation.get("title") or "")
    return (conversation_id, title)


def _root_node_ids(mapping: dict[str, dict[str, Any]]) -> list[str]:
    roots = [node_id for node_id, node in mapping.items() if node.get("parent") in (None, "")]
    return sorted(roots)


def _tree_order(mapping: dict[str, dict[str, Any]]) -> list[str]:
    roots = _root_node_ids(mapping)
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in seen or node_id not in mapping:
            return
        seen.add(node_id)
        ordered.append(node_id)
        for child_id in mapping[node_id].get("children") or []:
            visit(child_id)

    for root in roots:
        visit(root)

    for node_id in sorted(mapping):
        if node_id not in seen:
            visit(node_id)

    return ordered


def _conversation_timestamp(conversation: dict[str, Any]) -> float | int | None:
    timestamps: list[float] = []
    for node in conversation.get("mapping", {}).values():
        message = node.get("message") or {}
        if message.get("create_time") is not None:
            timestamps.append(float(message["create_time"]))
        if message.get("update_time") is not None:
            timestamps.append(float(message["update_time"]))
    if conversation.get("create_time") is not None:
        timestamps.append(float(conversation["create_time"]))
    if conversation.get("update_time") is not None:
        timestamps.append(float(conversation["update_time"]))
    if not timestamps:
        return None
    return max(timestamps)


def _timestamp_to_iso(timestamp: float | int | None) -> str:
    if timestamp is None:
        return "1970-01-01T00:00:00Z"
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _raw_scope(conversation: dict[str, Any], node_id: str, node: dict[str, Any]) -> dict[str, Any]:
    return {
        "conversation": {
            "conversation_id": conversation.get("conversation_id") or conversation.get("id"),
            "title": conversation.get("title"),
            "create_time": conversation.get("create_time"),
            "update_time": conversation.get("update_time"),
        },
        "mapping_node": node,
        "node_id": node_id,
    }


def _extract_text(message: dict[str, Any] | None) -> str:
    if not message:
        return ""
    content = message.get("content") or {}
    parts = content.get("parts") or []
    if isinstance(parts, list):
        return "\n".join(str(part) for part in parts if part is not None)
    if isinstance(parts, str):
        return parts
    return ""


def _extract_content_type(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    content = message.get("content") or {}
    value = content.get("content_type")
    return str(value) if value is not None else None


def _extract_attachments(message: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not message:
        return []
    metadata = message.get("metadata") or {}
    attachments = metadata.get("attachments") or []
    if isinstance(attachments, list):
        return attachments
    return []


def _actor(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    author = message.get("author") or {}
    role = author.get("role")
    return str(role) if role is not None else None


def _preview_for_message(message: dict[str, Any] | None) -> str:
    text = normalize_text(_extract_text(message))
    if text:
        return truncate_text(text, 180)
    if not message:
        return ""
    content_type = _extract_content_type(message)
    if content_type:
        return f"[{content_type}]"
    return ""


def _evidence_for_node(conversation: dict[str, Any], node_id: str, node: dict[str, Any]) -> dict[str, Any]:
    message = node.get("message")
    raw_payload = _raw_scope(conversation, node_id, node)
    source_hash = sha256_hex(raw_payload)
    evidence_id = stable_id(
        "evidence",
        {
            "conversation_id": conversation.get("conversation_id") or conversation.get("id"),
            "node_id": node_id,
            "source_hash": source_hash,
        },
    )
    metadata = message.get("metadata") if message else {}
    attachments = _extract_attachments(message)
    is_hidden = bool(metadata.get("is_visually_hidden_from_conversation")) if message else True
    return {
        "evidence_id": evidence_id,
        "source_hash": source_hash,
        "raw_pointer": f"raw/conversations.json#conversation.{conversation.get('conversation_id') or conversation.get('id')}.mapping.{node_id}",
        "redacted_preview": _preview_for_message(message),
        "metadata": {
            "conversation_id": conversation.get("conversation_id") or conversation.get("id"),
            "node_id": node_id,
            "parent_id": node.get("parent"),
            "children_ids": list(node.get("children") or []),
            "timestamp": message.get("create_time") if message else conversation.get("create_time"),
            "actor": _actor(message),
            "content_type": _extract_content_type(message),
            "is_visible_to_user": not is_hidden,
            "attachments": attachments,
            "tool_name": metadata.get("tool_name") if message else None,
            "message_status": message.get("status") if message else None,
            "model_slug": metadata.get("model_slug") or metadata.get("default_model_slug") if message else None,
        },
    }


def _gather_text_literals(text: str) -> list[str]:
    if not text:
        return []
    literals = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
    extracted = [first or second for first, second in literals if (first or second)]
    return list(dict.fromkeys(normalize_text(value) for value in extracted if normalize_text(value)))


def _has_quoted_capitalized_terms(text: str) -> bool:
    if not text:
        return False
    for literal in _gather_text_literals(text):
        if re.search(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", literal):
            return True
    return False


def _gather_terms(text: str) -> list[str]:
    if not text:
        return []
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", text)
    cleaned: list[str] = []
    for candidate in candidates:
        normalized = normalize_text(candidate)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _gather_references(text: str) -> list[str]:
    urls = re.findall(r"https?://\S+", text)
    return list(dict.fromkeys(urls))


def _event_type(actor: str | None, message: dict[str, Any] | None) -> str:
    content_type = _extract_content_type(message)
    text = normalize_text(_extract_text(message))
    if not message:
        return "unknown"
    if _has_quoted_capitalized_terms(text):
        return "naming"
    if actor == "system":
        return "system_event"
    if actor == "tool":
        return "tool_event"
    if actor == "user":
        return "question" if text.endswith("?") else "statement"
    if actor == "assistant":
        if content_type == "code":
            return "implementation"
        if text.endswith("?"):
            return "question"
        return "proposal"
    return "unknown"


def _observation_for_evidence(evidence: dict[str, Any], message: dict[str, Any] | None) -> dict[str, Any]:
    text = _extract_text(message)
    normalized_text = normalize_text(text)
    quote_hash = sha256_hex(normalized_text if normalized_text else evidence["source_hash"])
    event_type = _event_type(evidence["metadata"]["actor"], message)
    observation = {
        "observation_id": stable_id(
            "observation",
            {
                "source_evidence_id": evidence["evidence_id"],
                "event_type": event_type,
                "quote_hash": quote_hash,
            },
        ),
        "source_evidence_id": evidence["evidence_id"],
        "timestamp": evidence["metadata"]["timestamp"],
        "actor": evidence["metadata"]["actor"],
        "event_type": event_type,
        "introduced_terms": _gather_terms(normalized_text),
        "literal_phrases": _gather_text_literals(text),
        "actions": [],
        "references": _gather_references(normalized_text),
        "quote_pointer": evidence["raw_pointer"],
        "quote_hash": quote_hash,
        "redacted_quote": truncate_text(normalized_text, 240),
        "hashes": {
            "source_hash": evidence["source_hash"],
            "observation_hash": "",
        },
    }
    observation["hashes"]["observation_hash"] = sha256_hex(
        {
            key: value
            for key, value in observation.items()
            if key != "hashes"
        }
    )
    return observation


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [canonical_json(record) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def build_artifacts(conversations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    evidence_nodes: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    root_ids: list[str] = []
    branch_count = 0
    max_children = 0
    message_counts: Counter[str] = Counter()
    total_hidden = 0
    total_system = 0
    total_tool = 0

    for conversation in sorted(conversations, key=_conversation_key):
        mapping = conversation.get("mapping") or {}
        ordered_nodes = _tree_order(mapping)
        conv_root_ids = []
        for node_id in ordered_nodes:
            node = mapping[node_id]
            evidence = _evidence_for_node(conversation, node_id, node)
            evidence_nodes.append(evidence)
            if node.get("parent") in (None, ""):
                conv_root_ids.append(evidence["evidence_id"])
            children_ids = evidence["metadata"]["children_ids"]
            if len(children_ids) > 1:
                branch_count += 1
            max_children = max(max_children, len(children_ids))
            actor = evidence["metadata"]["actor"]
            if actor == "system":
                total_system += 1
            if actor == "tool":
                total_tool += 1
            if not evidence["metadata"]["is_visible_to_user"]:
                total_hidden += 1
            if node.get("message"):
                message_counts[actor or "unknown"] += 1
                observations.append(_observation_for_evidence(evidence, node.get("message")))
        root_ids.extend(conv_root_ids)

    manifest = {
        "schema_version": "1.0",
        "generated_at": _timestamp_to_iso(max((_conversation_timestamp(conv) or 0 for conv in conversations), default=None)),
        "total_conversations": len(conversations),
        "total_evidence_nodes": len(evidence_nodes),
        "total_observations": len(observations),
        "total_enriched_observations": 0,
        "topology_summary": {
            "root_evidence_nodes": root_ids,
            "branch_count": branch_count,
            "max_children_per_node": max_children,
        },
        "root_evidence_nodes": root_ids,
        "branch_counts": {
            "nodes_with_multiple_children": branch_count,
            "max_children_per_node": max_children,
        },
        "message_counts": {
            "hidden": total_hidden,
            "system": total_system,
            "tool": total_tool,
            "assistant": message_counts.get("assistant", 0),
            "user": message_counts.get("user", 0),
            "unknown": message_counts.get("unknown", 0),
        },
    }
    return evidence_nodes, observations, manifest


def ingest_archive(input_path: str | Path, output_dir: str | Path) -> IngestResult:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conversations = load_conversations(input_path)
    evidence_nodes, observations, manifest = build_artifacts(conversations)

    input_hash = sha256_hex(input_path.read_bytes())
    evidence_path = output_dir / "evidence.jsonl"
    observations_path = output_dir / "observations.jsonl"
    manifest_path = output_dir / "manifest.json"

    _write_jsonl(evidence_path, evidence_nodes)
    _write_jsonl(observations_path, observations)
    manifest["input_archive_hash"] = input_hash
    manifest["evidence_jsonl_hash"] = sha256_hex(evidence_path.read_bytes())
    manifest["observations_jsonl_hash"] = sha256_hex(observations_path.read_bytes())
    _write_json(manifest_path, manifest)

    return IngestResult(
        evidence_path=evidence_path,
        observations_path=observations_path,
        manifest_path=manifest_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Contract 001 ingestion")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    ingest_archive(args.input_path, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
