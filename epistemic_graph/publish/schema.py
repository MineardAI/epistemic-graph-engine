from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PACKAGE_SCHEMA_VERSION = "005.v0"
PACKAGE_VERSION = "0.1.0"

PublishProfileName = Literal["executive", "audit", "research", "timeline", "claim"]
PublishViewName = Literal["executive_summary", "evidence_report", "claim_dossier", "timeline_export"]
PublishedArtifactName = Literal[
    "answer.json",
    "bounties.jsonl",
    "claim_graph.json",
    "claims.jsonl",
    "concept_maturity.json",
    "concept_timeline.json",
    "evidence.jsonl",
    "gap_windows.jsonl",
    "observations.jsonl",
    "resolution_trace.json",
    "timeline_events.jsonl",
    "timeline_report.md",
    "enriched_observations.jsonl",
]


class TableRowType(str, Enum):
    package_identity = "package_identity"
    build_metadata = "build_metadata"
    input = "input"
    output = "output"
    verification = "verification"
    evidence = "evidence"
    observation = "observation"
    claim = "claim"
    support_edge = "support_edge"
    contradiction_edge = "contradiction_edge"
    graph_summary = "graph_summary"
    bounty = "bounty"
    event = "event"
    concept_timeline = "concept_timeline"
    maturity = "maturity"
    gap_window = "gap_window"


class PublishViewColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: str
    field: str


class PublishView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PublishViewName
    title: str
    record_types: list[TableRowType] = Field(
        description=(
            "Descriptive metadata only. It lists the intended upstream record "
            "families for a profile view. It is not enforced by the v0 runtime "
            "packager. The v0 packager selects outputs from explicit profile "
            "include/exclude rules and declared views, not from record_types."
        )
    )
    columns: list[PublishViewColumn]
    sort_keys: list[str] = Field(default_factory=list)

    @field_validator("columns")
    @classmethod
    def _validate_columns(cls, value: list[PublishViewColumn]) -> list[PublishViewColumn]:
        if not value:
            raise ValueError("publish views require at least one column")
        return value


class PublishProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_name: PublishProfileName
    package_version: str = PACKAGE_VERSION
    package_schema_version: str = PACKAGE_SCHEMA_VERSION
    source_artifacts: list[PublishedArtifactName]
    views: list[PublishView]

    @field_validator("source_artifacts")
    @classmethod
    def _validate_source_artifacts(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("profiles require at least one source artifact")
        return value

    @field_validator("views")
    @classmethod
    def _validate_views(cls, value: list[PublishView]) -> list[PublishView]:
        if not value:
            raise ValueError("profiles require at least one view")
        return value

    @model_validator(mode="after")
    def _validate_versions(self) -> "PublishProfile":
        if self.package_version != PACKAGE_VERSION:
            raise ValueError(f"unexpected package_version {self.package_version!r}")
        if self.package_schema_version != PACKAGE_SCHEMA_VERSION:
            raise ValueError(f"unexpected package_schema_version {self.package_schema_version!r}")
        return self


class PackageIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    package_version: str
    package_schema_version: str
    profile_name: PublishProfileName

    @model_validator(mode="after")
    def _validate_versions(self) -> "PackageIdentity":
        if self.package_version != PACKAGE_VERSION:
            raise ValueError(f"unexpected package_version {self.package_version!r}")
        if self.package_schema_version != PACKAGE_SCHEMA_VERSION:
            raise ValueError(f"unexpected package_schema_version {self.package_schema_version!r}")
        return self


class BuildMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    epistemic_version: str
    contract_versions: dict[str, str]


class ManifestInputArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    size_bytes: int
    sha256: str

    @field_validator("size_bytes")
    @classmethod
    def _validate_size_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("size_bytes may not be negative")
        return value


class ManifestOutputArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    size_bytes: int
    sha256: str

    @field_validator("size_bytes")
    @classmethod
    def _validate_size_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("size_bytes may not be negative")
        return value


class PackageVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_valid: bool
    profile_valid: bool
    required_files_present: bool
    file_sizes_valid: bool
    hashes_valid: bool
    errors: list[str] = Field(default_factory=list)


class PackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_identity: PackageIdentity
    build_metadata: BuildMetadata
    inputs: list[ManifestInputArtifact]
    outputs: list[ManifestOutputArtifact]
    verification: PackageVerification

    @field_validator("inputs", "outputs")
    @classmethod
    def _validate_artifact_lists(cls, value: list[ManifestInputArtifact | ManifestOutputArtifact]) -> list[ManifestInputArtifact | ManifestOutputArtifact]:
        if not value:
            raise ValueError("package manifests require at least one artifact entry")
        return value
