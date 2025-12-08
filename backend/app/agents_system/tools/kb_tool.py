"""
KB tools wrapping existing RAG services for use by the ReAct agent.
"""

from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
import asyncio

from ..agents.rag_agent import RAGAgent, build_cited_reply


class KBSearchTool(BaseTool):
    name = "kb_search"
    description = (
        "Search knowledge bases using profile routing or explicit kb_ids. "
        "Input: {\"query\": str, \"profile\": 'chat'|'proposal', \"kb_ids\": [str]|null, \"topK\": int}."
    )

    def __init__(self):
        super().__init__()
        self.agent = RAGAgent()

    def _run(self, query: str, profile: str = "chat", kb_ids: Optional[List[str]] = None, topK: int = 5) -> str:
        result = self.agent.execute(query, profile=profile, kb_ids=kb_ids, top_k=topK)
        payload = build_cited_reply(result)
        return payload["assistantMessage"]

    async def _arun(self, query: str, profile: str = "chat", kb_ids: Optional[List[str]] = None, topK: int = 5) -> str:
        # Wrap the sync call to keep tool signature consistent
        return await asyncio.to_thread(self._run, query, profile, kb_ids, topK)


def create_kb_tools() -> List[BaseTool]:
    """Factory returning KB-related tools for the agent."""
    return [KBSearchTool()]
