"""
KB tools wrapping existing RAG services for use by the ReAct agent.
"""

from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
from pydantic import PrivateAttr
import asyncio

from ..agents.rag_agent import RAGAgent, build_cited_reply


class KBSearchTool(BaseTool):
    name: str = "kb_search"
    description: str = (
        "Search curated Azure architecture knowledge bases and return cited answers. "
        "Knowledge bases: Azure Well-Architected Framework (WAF), Azure Cloud Adoption Framework (CAF), and NIST SP 800-207 (Zero Trust Architecture). "
        "NIST SP 800-207 coverage includes: core zero trust principles, policy and trust evaluation points, enforcement points, identity-centric access, continuous verification, micro-segmentation, and reference architecture components relevant to cloud workloads. "
        "Input: {\"query\": str, \"profile\": 'chat', \"kb_ids\": [str]|null, \"topK\": int}. "
        "Profile 'chat' produces concise, actionable guidance suitable for interactive use. "
        "Optional \"kb_ids\" limits the search to specific KBs (e.g., ['caf','waf']); omit to search all active KBs. "
        "Output: assistant message including Sources with KB titles/sections for traceability."
    )
    _agent: RAGAgent = PrivateAttr()

    def __init__(self):
        super().__init__()
        self._agent = RAGAgent()

    def _run(self, query: str, profile: str = "chat", kb_ids: Optional[List[str]] = None, topK: int = 5) -> str:
        result = self._agent.execute(query, profile=profile, kb_ids=kb_ids, top_k=topK)
        payload = build_cited_reply(result)
        return payload["assistantMessage"]

    async def _arun(self, query: str, profile: str = "chat", kb_ids: Optional[List[str]] = None, topK: int = 5) -> str:
        # Wrap the sync call to keep tool signature consistent
        return await asyncio.to_thread(self._run, query, profile, kb_ids, topK)


def create_kb_tools() -> List[BaseTool]:
    """Factory returning KB-related tools for the agent."""
    return [KBSearchTool()]
