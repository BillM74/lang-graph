"""
LangGraph workflow definitions — teams converted to StateGraphs.

Each workflow implements a multi-agent orchestration pattern:
- feature_development: Design -> Safety -> Implementation -> Review -> Learning
- metrics_team: Definition -> Design -> Safety -> Implementation -> Validation -> Learning
- performance_team: Diagnosis -> Implementation -> Validation -> Documentation -> Learning
- learning_team: Analysis -> Pattern Extraction -> Proposals
"""

from .feature_development import build_feature_development_workflow
from .learning_team import build_learning_workflow
from .metrics_team import build_metrics_workflow
from .performance_team import build_performance_workflow

__all__ = [
    "build_feature_development_workflow",
    "build_learning_workflow",
    "build_metrics_workflow",
    "build_performance_workflow",
]
