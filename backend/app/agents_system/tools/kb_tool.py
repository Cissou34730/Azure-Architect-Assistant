"""
KB tools wrapping existing RAG services for use by the ReAct agent.
"""

import asyncio
import contextlib
import json
from pathlib import Path
from typing import Any

from langchain.tools import BaseTool, Tool
from pydantic import PrivateAttr

from ..agents.rag_agent import RAGAgent, build_cited_reply


class KBSearchTool(BaseTool):
    name: str = "kb_search"
    description: str = (
        "Search curated Azure architecture knowledge bases and return cited answers. "
        "Knowledge bases: Azure Well-Architected Framework (WAF), Azure Cloud Adoption Framework (CAF), and NIST SP 800-207 (Zero Trust Architecture). "
        "NIST SP 800-207 coverage includes: core zero trust principles, policy and trust evaluation points, enforcement points, identity-centric access, continuous verification, micro-segmentation, and reference architecture components relevant to cloud workloads. "
        'Input: {"query": str, "profile": \'chat\', "kb_ids": [str]|null, "topK": int}. '
        "Profile 'chat' produces concise, actionable guidance suitable for interactive use. "
        "Optional \"kb_ids\" limits the search to specific KBs (e.g., ['caf','waf']); omit to search all active KBs. "
        "Output: assistant message including Sources with KB titles/sections for traceability."
    )
    _agent: RAGAgent = PrivateAttr()

    def __init__(self):
        super().__init__()
        self._agent = RAGAgent()

    def _run(self, payload: str | dict | Any) -> str:
        # Normalize payload to (query, profile, kb_ids, top_k)
        if isinstance(payload, str):
            query = payload
            profile = "chat"
            kb_ids = None
            top_k = 5
        elif isinstance(payload, dict):
            query = payload.get("query")
            profile = payload.get("profile", "chat")
            kb_ids = payload.get("kb_ids")
            top_k = payload.get("top_k") or payload.get("topK") or 5
        else:
            # object-like
            query = getattr(payload, "query", str(payload))
            profile = getattr(payload, "profile", "chat")
            kb_ids = getattr(payload, "kb_ids", None)
            top_k = getattr(payload, "top_k", getattr(payload, "topK", 5))

        result = self._agent.execute(query, profile=profile, kb_ids=kb_ids, top_k=top_k)
        payload_out = build_cited_reply(result)
        return payload_out["assistantMessage"]

    async def _arun(self, payload: str | dict | Any) -> str:
        # Wrap the sync call to keep tool signature consistent
        return await asyncio.to_thread(self._run, payload)


def _discover_specific_kb_tools() -> list[BaseTool]:
    """Helper to discover and build per-KB search tools."""
    specific_tools: list[BaseTool] = []
    with contextlib.suppress(Exception):
        cfg_path = Path(__file__).parents[2] / "data" / "knowledge_bases" / "config.json"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            for kb_entry in cfg.get("knowledge_bases", []):
                if kb_entry.get("status") != "active":
                    continue
                kb_id = kb_entry.get("id")
                kb_name = kb_entry.get("name") or kb_id

                def _build_kb_tool(kid: str, kname: str) -> BaseTool:
                    class PerKBTool(BaseTool):
                        name: str = f"kb_{kid}_search"
                        description: str = f"Search KB: {kname} (id={kid})"

                        def _run(self, payload: Any) -> str:
                            tool = KBSearchTool()
                            if isinstance(payload, str):
                                payload_obj = {"query": payload, "kb_ids": [kid]}
                            elif isinstance(payload, dict):
                                payload_obj = dict(payload)
                                payload_obj.setdefault("kb_ids", [kid])
                            else:
                                payload_obj = {"query": str(payload), "kb_ids": [kid]}
                            return tool._run(payload_obj)

                        async def _arun(self, payload: Any) -> str:
                            return await asyncio.to_thread(self._run, payload)
                    return PerKBTool()

                specific_tools.append(_build_kb_tool(str(kb_id), str(kb_name)))
    return specific_tools


def create_kb_tools() -> list[BaseTool]:
    """Factory returning KB-related tools for the agent."""
    tools: list[BaseTool] = []

    # Add a legacy 'kb_search' wrapper that delegates to KBSearchTool.
    # Provide a lightweight legacy wrapper named 'kb_search' for tests and
    # scripting.
    with contextlib.suppress(Exception):
        class KBSearchWrapper:
            name = "kb_search"
            description = "Search across configured KBs (legacy wrapper)"
            is_single_input = True

            def __init__(self):
                self.func = self.run

            def get(self, key, default=None):
                return getattr(self, key, default)

            def run(self, payload):
                return KBSearchTool()._run(payload)

            async def arun(self, payload):
                return await KBSearchTool()._arun(payload)

        tools.append(KBSearchWrapper())  # type: ignore

    # Also expose a real langchain Tool for agent initialization.
    with contextlib.suppress(Exception):
        def _kb_search_for_agent(single_input):
            if isinstance(single_input, str):
                payload = None
                with contextlib.suppress(Exception):
                    payload = json.loads(single_input)
                if not payload:
                    payload = single_input
            else:
                payload = single_input
            return KBSearchTool()._run(payload)

        tools.append(Tool(name="kb_search_agent", func=_kb_search_for_agent, description="Agent-facing KB search (internal)"))

    # Try to discover configured KBs and create per-KB single-input tools
    tools.extend(_discover_specific_kb_tools())

    return tools

