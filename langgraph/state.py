"""
Shared state definitions for LangGraph workflows.

All workflows share a common base state with typed fields for
task tracking, artifacts, and inter-agent communication.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


# --- Enums ---


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    FAILED = "failed"


class ImpactClassification(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    NEEDS_REWORK = "needs_rework"


class ChangeType(str, Enum):
    ADDITIVE = "additive"
    MUTATIVE = "mutative"
    REMOVAL = "removal"


class SOMALayer(str, Enum):
    STAGING = "staging"
    ACTIVITIES = "activities"
    ENTITIES = "entities"
    NETS = "nets"


class MetricType(str, Enum):
    ATOMIC = "atomic"
    COMPOUND = "compound"


# --- Data Classes ---


@dataclass
class VerificationGate:
    name: str
    passed: bool = False
    details: str = ""


@dataclass
class ReviewFinding:
    category: str  # blocking, suggestion, question, praise
    description: str
    file_path: str = ""
    line_number: int = 0
    auto_fix: str = ""


@dataclass
class DesignSpec:
    model_name: str = ""
    soma_layer: str = ""
    grain: str = ""
    primary_key: list[str] = field(default_factory=list)
    columns: dict[str, str] = field(default_factory=dict)
    materialization: str = "view"
    incremental_strategy: str = ""
    clustering_keys: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tests: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""


@dataclass
class MetricSpec:
    name: str = ""
    label: str = ""
    metric_type: str = ""  # atomic or compound
    calculation_type: str = ""  # count, sum, average, ratio, etc.
    description: str = ""
    business_definition: str = ""
    formula: str = ""
    filters: list[dict[str, str]] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    owner: str = ""
    time_grains: list[str] = field(default_factory=list)


@dataclass
class PerformanceBaseline:
    query_or_model: str = ""
    runtime_seconds: float = 0.0
    bytes_scanned: int = 0
    credits_used: float = 0.0
    spillage_bytes: int = 0
    partitions_scanned: int = 0
    partitions_total: int = 0


@dataclass
class ImpactReport:
    classification: str = ""  # safe, caution, dangerous
    change_type: str = ""  # additive, mutative, removal
    affected_models: list[str] = field(default_factory=list)
    value_dependent_filters: list[str] = field(default_factory=list)
    dimension_collisions: list[str] = field(default_factory=list)
    recommendation: str = ""
    details: str = ""


# --- Workflow States ---


class FeatureDevelopmentState(TypedDict, total=False):
    """State for the feature development workflow."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Task
    task_description: str
    current_phase: str
    status: str
    error: str

    # Design phase
    design_spec: dict[str, Any]
    design_score: int
    design_approved: bool

    # Impact analysis phase
    impact_report: dict[str, Any]
    impact_classification: str

    # Implementation phase
    implemented_models: list[str]
    verification_gates: list[dict[str, Any]]
    all_gates_passed: bool

    # Review phase
    review_findings: list[dict[str, Any]]
    review_score: int
    review_decision: str
    review_cycle: int

    # Optimization (conditional)
    needs_optimization: bool
    performance_before: dict[str, Any]
    performance_after: dict[str, Any]

    # Learning
    retrospective_summary: str

    # Artifacts accumulated across phases
    artifacts: Annotated[list[str], operator.add]


class MetricsWorkflowState(TypedDict, total=False):
    """State for the metrics definition workflow."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Task
    task_description: str
    current_phase: str
    status: str
    error: str

    # Metric definition phase
    metric_spec: dict[str, Any]
    definition_gates_passed: list[str]

    # Schema design (conditional)
    needs_new_model: bool
    design_spec: dict[str, Any]

    # Impact analysis
    impact_report: dict[str, Any]
    impact_classification: str

    # Implementation
    implemented_models: list[str]
    verification_gates: list[dict[str, Any]]
    all_gates_passed: bool

    # Validation
    validation_result: dict[str, Any]
    variance_pct: float
    validation_passed: bool

    # Learning
    retrospective_summary: str

    artifacts: Annotated[list[str], operator.add]


class PerformanceWorkflowState(TypedDict, total=False):
    """State for the performance optimization workflow."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Task
    task_description: str
    current_phase: str
    status: str
    error: str

    # Diagnosis
    bottleneck: str
    root_cause: str
    optimization_strategy: str

    # Implementation
    implemented_changes: list[str]
    verification_gates: list[dict[str, Any]]

    # Validation - A/B comparison
    performance_before: dict[str, Any]
    performance_after: dict[str, Any]
    improvement_pct: float

    # Review
    review_decision: str
    review_score: int

    # Learning
    retrospective_summary: str

    artifacts: Annotated[list[str], operator.add]


class LearningWorkflowState(TypedDict, total=False):
    """State for the learning/retrospective workflow."""
    messages: Annotated[list[BaseMessage], add_messages]

    # Task
    task_description: str
    current_phase: str
    status: str
    error: str

    # Analysis
    successes: list[str]
    failures: list[str]
    discoveries: list[str]
    root_causes: list[str]

    # Patterns
    patterns_extracted: list[dict[str, Any]]
    reflections_stored: list[str]

    # Proposals
    improvement_proposals: list[dict[str, Any]]

    artifacts: Annotated[list[str], operator.add]
