from app.agents_system.langgraph.nodes.architecture_planner import (
    _format_previous_decisions,
)


def test_format_previous_decisions_returns_bulleted_summary() -> None:
    formatted = _format_previous_decisions(
        [
            {
                "title": "Use Front Door",
                "rationale": "Global edge routing improves failover behavior.",
            },
            {
                "title": "Prefer managed identity",
                "rationale": "Avoid secret sprawl.",
            },
        ]
    )

    assert formatted == (
        "1. **Use Front Door**\n"
        "   Rationale: Global edge routing improves failover behavior.\n"
        "2. **Prefer managed identity**\n"
        "   Rationale: Avoid secret sprawl."
    )
