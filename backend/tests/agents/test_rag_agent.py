import pytest

from app.agents_system.agents.rag_agent import RAGAgent


@pytest.fixture
def agent(monkeypatch):
    a = RAGAgent()

    class DummyService:
        def query_profile(
            self, question, profile, top_k_per_kb=3, metadata_filters=None
        ):
            return {
                "answer": f"Answer for: {question}",
                "sources": [
                    {
                        "title": "CAF Docs",
                        "url": "https://learn.microsoft.com/azure/well-architected/",
                        "kb_name": "CAF",
                        "score": 0.88,
                    }
                ],
                "has_results": True,
                "kbs_queried": ["caf"],
                "kb_count": 1,
            }

        def query_specific_kbs(self, question, kb_ids, top_k=5, metadata_filters=None):
            return {
                "answer": f"Specific KBs: {kb_ids}",
                "sources": [],
                "has_results": True,
                "kbs_queried": kb_ids,
                "kb_count": len(kb_ids),
            }

    # Replace real service with dummy
    monkeypatch.setattr(a, "query_service", DummyService())
    return a


def test_rag_agent_profile_routing(agent):
    res = agent.execute("What is CAF?", profile="chat", kb_ids=None, top_k=3)
    assert res["has_results"] is True
    assert "Answer for:" in res["answer"]
    assert res["kb_count"] == 1
    assert len(res["sources"]) == 1


def test_rag_agent_specific_kbs(agent):
    res = agent.execute(
        "Explain policies", profile="chat", kb_ids=["caf", "security"], top_k=2
    )
    assert res["has_results"] is True
    assert "Specific KBs:" in res["answer"]
    assert res["kbs_queried"] == ["caf", "security"]
    assert res["kb_count"] == 2
