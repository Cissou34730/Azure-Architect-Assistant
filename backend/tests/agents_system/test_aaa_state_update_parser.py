import json

from app.agents_system.services.state_update_parser import extract_state_updates


def test_extract_state_updates_parses_aaa_state_update_json_block() -> None:
    response = (
        "Here is the candidate.\n\n"
        "AAA_STATE_UPDATE\n"
        "```json\n"
        + json.dumps(
            {
                "candidateArchitectures": [
                    {
                        "id": "c1",
                        "title": "Candidate 1",
                        "summary": "Summary",
                        "assumptionIds": [],
                        "diagramIds": [],
                        "sourceCitations": [],
                    }
                ]
            }
        )
        + "\n```\n"
    )

    updates = extract_state_updates(response, user_message="", current_state={})
    assert updates is not None
    assert updates.get("candidateArchitectures")[0]["id"] == "c1"


def test_extract_state_updates_falls_back_to_heuristics_when_no_block() -> None:
    response = "We need 99.9% availability for this workload."
    updates = extract_state_updates(response, user_message=response, current_state={})
    assert updates is not None
    assert updates.get("nfrs", {}).get("availability")
