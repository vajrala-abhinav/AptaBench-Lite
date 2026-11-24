from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Normalized:
    raw: object
    canonical: str | None
    status: str
    transformations: tuple[str, ...] = ()
    offsets: tuple[int, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Source:
    workbook: str
    sheet: str
    row: int
    cell: str
    item_index: int | None
    raw_json: str


@dataclass(frozen=True)
class Record:
    id: str
    paper_id: str | None
    paper_key: str
    sequence: Normalized
    name: str
    name_source: str
    source: Source
    significant: bool = True
    scope_status: str = "SIGNIFICANT"
    notes: str = ""


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    source: str = ""
    record_id: str = ""
    severity: str = "warning"
    fix: str = "Inspect source annotations or mapping."


@dataclass(frozen=True)
class Trace:
    aligned_gold: str
    aligned_extractor: str
    operations: tuple[str, ...]
    distance: int
    gold_start: int
    gold_end: int
    extractor_start: int
    extractor_end: int
    left_flank: str
    right_flank: str
    optimal_interval_count: int
    mode: str
    algorithm_version: str = "unit-edit-fitting-v1"

    @property
    def counts(self):
        return {op: self.operations.count(op) for op in
                ("MATCH", "SUBSTITUTION", "INSERTION", "DELETION", "FREE_EXTRACTOR_FLANK")}

    def completion(self):
        return 100 * max(0, 1 - self.distance / self.gold_end)


@dataclass(frozen=True)
class Candidate:
    id: str
    paper_id: str
    gold_id: str
    extractor_id: str
    core: Trace
    whole: Trace
    budget: int
    name_support: bool
    name_conflict: bool
    viable: bool
    reasons: tuple[str, ...]
    stage: str = "S3"
    strict_whole_pass: bool = field(init=False)
    strict_core_pass: bool = field(init=False)
    adaptive_whole_pass: bool = field(init=False)
    adaptive_core_pass: bool = field(init=False)

    def __post_init__(self):
        for key, value in (("strict_whole_pass",self.whole.distance==0),
                           ("strict_core_pass",self.core.distance==0),
                           ("adaptive_whole_pass",self.whole.distance<=self.budget),
                           ("adaptive_core_pass",self.core.distance<=self.budget)):
            object.__setattr__(self,key,value)

    def passes(self, tolerance="adaptive", sequence_scope="core"):
        trace = self.core if sequence_scope == "core" else self.whole
        return trace.distance <= (self.budget if tolerance == "adaptive" else 0)


@dataclass(frozen=True)
class DuplicateGroup:
    id: str
    paper_id: str
    canonical: str
    members: tuple[str, ...]
    representatives: tuple[str, ...]
    name_conflict: bool
    multiplicity: bool


@dataclass(frozen=True)
class Association:
    gold_id: str
    extractor_id: str
    candidate_id: str
    origin: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    gold_id: str
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Paper:
    id: str
    aliases: tuple[str, ...]
    attempted: bool
    gold_ids: tuple[str, ...]
    extractor_ids: tuple[str, ...]
    logical_extractor_ids: tuple[str, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationRun:
    run_id: str
    schema_version: str
    policy_version: str
    gold_sha256: str
    extractor_sha256: str
    config_json: str
    metadata_json: str
    gold: tuple[Record, ...]
    extractors: tuple[Record, ...]
    papers: tuple[Paper, ...]
    duplicates: tuple[DuplicateGroup, ...]
    candidates: tuple[Candidate, ...]
    automatic: tuple[Association, ...]
    decisions: tuple[Decision, ...]
    diagnostics: tuple[Diagnostic, ...]
    timings_json: str


@dataclass(frozen=True)
class ReviewEvent:
    revision: int
    action: str
    reviewer: str
    timestamp: str
    gold_id: str = ""
    extractor_id: str = ""
    note: str = ""
    target_revision: int | None = None
    confirmed: bool = False


@dataclass(frozen=True)
class ReviewedRun:
    run: EvaluationRun
    events: tuple[ReviewEvent, ...]
    associations: tuple[Association, ...]
    missing: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]


def base_run(value):
    return value.run if isinstance(value, ReviewedRun) else value


def associations(value):
    return value.associations if isinstance(value, ReviewedRun) else value.automatic
