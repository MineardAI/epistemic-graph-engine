# Implementation Note

- Contract 001 uses a deterministic `generated_at` derived from the archive timestamps instead of wall-clock time so repeated runs stay byte-identical.
- The selected sample fixture is a full conversation slice from `Docs/conversations.json`; a synthetic overlay was not needed because the archive already contains branching, hidden/system, tool, and attachment metadata.
- Mapping entries without messages are retained as evidence nodes, but they do not produce observations.

