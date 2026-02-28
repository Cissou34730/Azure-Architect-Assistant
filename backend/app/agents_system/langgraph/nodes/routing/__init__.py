"""Routing sub-package: per-agent routing and handoff logic.

Re-exports all public symbols so existing imports from
``stage_routing`` keep working after the split.
"""

from .architecture_planner import (
    prepare_architecture_planner_handoff,
    should_route_to_architecture_planner,
)
from .cost_estimator import (
    prepare_cost_estimator_handoff,
    should_route_to_cost_estimator,
)
from .iac_generator import (
    prepare_iac_generator_handoff,
    should_route_to_iac_generator,
)
from .saas_advisor import (
    prepare_saas_advisor_handoff,
    should_route_to_saas_advisor,
)

__all__ = [
    "prepare_architecture_planner_handoff",
    "prepare_cost_estimator_handoff",
    "prepare_iac_generator_handoff",
    "prepare_saas_advisor_handoff",
    "should_route_to_architecture_planner",
    "should_route_to_cost_estimator",
    "should_route_to_iac_generator",
    "should_route_to_saas_advisor",
]
