from app.agents_system.services.response_sanitizer import sanitize_agent_output


def test_sanitize_agent_output_removes_state_update_block() -> None:
    text = (
        "Updated checklist.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        '{"wafChecklist":{"items":[{"id":"x"}]}}\n'
        "```\n"
    )

    assert sanitize_agent_output(text) == "Updated checklist."


def test_sanitize_agent_output_removes_mcp_log_block() -> None:
    text = (
        "I searched docs.\n"
        "AAA_MCP_LOG\n"
        "```json\n"
        '{"tool":"microsoft_docs_search","urls":["https://learn.microsoft.com/"]}\n'
        "```\n"
        "Here is the summary."
    )

    sanitized = sanitize_agent_output(text)
    assert "AAA_MCP_LOG" not in sanitized
    assert sanitized.startswith("I searched docs.")
    assert sanitized.endswith("Here is the summary.")


def test_sanitize_agent_output_keeps_regular_mermaid_and_text() -> None:
    text = (
        "System overview:\n"
        "```mermaid\n"
        "flowchart TD\n"
        "A-->B\n"
        "```\n"
        "No machine payloads."
    )

    assert sanitize_agent_output(text) == text
