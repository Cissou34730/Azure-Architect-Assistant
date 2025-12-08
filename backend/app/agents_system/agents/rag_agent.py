"""
RAG-specialized agent.
Wraps the existing MultiSourceQueryService to perform retrieval and
produce context-grounded answers with citations, without adding new endpoints.
"""

import logging
from typing import Optional, List, Dict, Any

from app.service_registry import get_multi_query_service
from app.kb.multi_query import QueryProfile

logger = logging.getLogger(__name__)


class RAGAgent:
	"""Thin wrapper agent around the existing RAG query services."""

	def __init__(self):
		self.query_service = get_multi_query_service()
		logger.info("RAGAgent initialized")

	def execute(
		self,
		user_query: str,
		profile: str = "chat",
		kb_ids: Optional[List[str]] = None,
		top_k: int = 5,
		metadata_filters: Optional[Dict[str, Any]] = None,
	) -> Dict[str, Any]:
		"""
		Execute a retrieval-augmented response.

		Args:
			user_query: User question
			profile: "chat" or "proposal" (default: chat)
			kb_ids: Optional explicit KB selection; if omitted, uses profile mapping
			top_k: Max results per KB
			metadata_filters: Optional filters

		Returns:
			Dict with keys: answer, sources, has_results, kbs_queried, kb_count
		"""
		logger.info(f"RAGAgent executing query (profile={profile})")

		if kb_ids and len(kb_ids) > 0:
			result = self.query_service.query_specific_kbs(
				question=user_query,
				kb_ids=kb_ids,
				top_k=top_k,
				metadata_filters=metadata_filters,
			)
			return result

		# Use profile-based routing across KBs
		qp = QueryProfile.CHAT if profile == "chat" else QueryProfile.PROPOSAL
		result = self.query_service.query_profile(
			question=user_query,
			profile=qp,
			top_k_per_kb=top_k,
			metadata_filters=metadata_filters,
		)
		return result


def build_cited_reply(agent_result: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Build a response payload including citations ready for the chat pipeline.

	Returns a dict with keys:
	  - assistantMessage: str
	  - sources: list[dict]
	  - has_results: bool
	"""
	answer = agent_result.get("answer", "")
	sources = agent_result.get("sources", [])
	has_results = agent_result.get("has_results", False)

	# Append simple citation list to the end of the answer
	if sources:
		citation_lines = []
		for i, src in enumerate(sources, 1):
			title = src.get("title") or src.get("section") or "Untitled"
			url = src.get("url", "")
			kb_name = src.get("kb_name", "")
			citation_lines.append(f"[{i}] {title} ({kb_name}) {url}")
		answer = f"{answer}\n\nSources:\n" + "\n".join(citation_lines)

	return {
		"assistantMessage": answer,
		"sources": sources,
		"has_results": has_results,
	}
