import pytest

from app.agents_system.tools.kb_tool import KBSearchTool


class DummyResult:
    def __init__(self):
        self.result = {
            "answer": "This is a grounded answer.",
            "sources": [
                {
                    "title": "Azure Architecture Guide",
                    "url": "https://learn.microsoft.com/azure/architecture/guide",
                    "kb_name": "CAF",
                    "score": 0.9,
                }
            ],
            "has_results": True,
        }


@pytest.fixture
def tool(monkeypatch):
    t = KBSearchTool()

    # Monkeypatch the agent to avoid hitting real indices/services
    class DummyAgent:
        def execute(
            self, query, profile="chat", kb_ids=None, top_k=5, metadata_filters=None
        ):
            return DummyResult().result

    monkeypatch.setattr(t, "_agent", DummyAgent())
    return t


def test_kb_search_tool_returns_cited_answer(tool):
    output = tool._run(
        query="How to secure Azure SQL?", profile="chat", kb_ids=None, topK=3
    )
    assert "This is a grounded answer." in output
    assert "Sources:" in output
    assert "Azure Architecture Guide" in output
