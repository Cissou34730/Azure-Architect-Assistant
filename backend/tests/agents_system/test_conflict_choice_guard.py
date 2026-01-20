from app.agents_system.agents.router import _extract_architect_choice_required_section


def test_extract_architect_choice_required_section_none_when_absent() -> None:
    assert _extract_architect_choice_required_section("No conflicts here") is None


def test_extract_architect_choice_required_section_extracts_until_state_update_marker() -> None:
    text = (
        "Some intro\n\n"
        "Architect choice required:\n"
        "Option 1: Do A\n"
        "Option 2: Do B\n\n"
        "AAA_STATE_UPDATE\n```json\n{\"nfrs\": {}}\n```\n"
    )
    section = _extract_architect_choice_required_section(text)
    assert section is not None
    assert section.startswith("Architect choice required:")
    assert "AAA_STATE_UPDATE" not in section
