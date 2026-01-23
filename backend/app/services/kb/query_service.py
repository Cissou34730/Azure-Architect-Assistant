"""KB Query Services

Query execution logic for single KB and multi-KB orchestration.
"""

import logging
from enum import Enum

from llama_index.core import Settings

from app.kb import KBManager
from app.kb.models import KBConfig
from app.kb.service import KnowledgeBaseService
from config.settings import get_query_settings

logger = logging.getLogger(__name__)


class QueryProfile(str, Enum):
    CHAT = "chat"
    PROPOSAL = "proposal"


class KBQueryService:
    """Per-KB query execution using the index managed by KnowledgeBaseService."""

    def __init__(
        self,
        kb_config: KBConfig,
        similarity_threshold: float | None = None,
        min_results: int | None = None,
    ):
        self.kb_config = kb_config
        self.kb_id = kb_config.id
        self.kb_name = kb_config.name
        
        # Load query settings from config
        query_settings = get_query_settings()
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else query_settings.similarity_threshold
        self.min_results = min_results if min_results is not None else query_settings.min_results
        self.initial_retrieve_multiplier = query_settings.initial_retrieve_multiplier
        self.min_initial_retrieve = query_settings.min_initial_retrieve

    def query(
        self, question: str, top_k: int = 5, metadata_filters: dict | None = None
    ) -> dict:
        logger.info("[%s] Processing query: %s...", self.kb_id, question[:100])

        index = KnowledgeBaseService(self.kb_config).get_index()
        # Retrieve more candidates initially to ensure we have enough after filtering
        initial_retrieve_count = max(
            top_k * self.initial_retrieve_multiplier,
            self.min_initial_retrieve
        )
        retriever = index.as_retriever(similarity_top_k=initial_retrieve_count)

        if metadata_filters:
            from llama_index.core.vector_stores import (  # noqa: PLC0415
                MetadataFilter,
                MetadataFilters,
            )

            filters = MetadataFilters(
                filters=[
                    MetadataFilter(key=k, value=v) for k, v in metadata_filters.items()
                ]
            )
            retriever = index.as_retriever(similarity_top_k=initial_retrieve_count, filters=filters)

        retrieved_nodes = retriever.retrieve(question)
        logger.info("[%s] Retrieved %d nodes", self.kb_id, len(retrieved_nodes))

        # Log top scores for debugging
        if retrieved_nodes:
            top_scores = ", ".join([f"{n.score:.3f}" for n in retrieved_nodes[:5]])
            logger.info("[%s] Top 5 scores: [%s] (threshold: %.3f)", self.kb_id, top_scores, self.similarity_threshold)

        # Filter by threshold
        filtered = [n for n in retrieved_nodes if n.score >= self.similarity_threshold]
        
        # Apply minimum results policy: if we got some results but filtered all out,
        # return top min_results anyway (sorted by score)
        if not filtered and retrieved_nodes:
            logger.warning(
                "[%s] All %d nodes filtered out by threshold %.3f. Applying min_results policy (%d).",
                self.kb_id, len(retrieved_nodes), self.similarity_threshold, self.min_results
            )
            filtered = retrieved_nodes[:self.min_results]
        
        # Limit to requested top_k
        filtered = filtered[:top_k]
        logger.info("[%s] After filtering: %d nodes (returned)", self.kb_id, len(filtered))

        if not filtered:
            return {
                "answer": f"No relevant information found in {self.kb_name}.",
                "sources": [],
                "scores": [],
                "has_results": False,
                "kb_id": self.kb_id,
                "kb_name": self.kb_name,
            }

        context_parts: list[str] = []
        sources: list[dict] = []
        scores: list[float] = []
        for i, node in enumerate(filtered, 1):
            context_parts.append(f"[Source {i} - {self.kb_name}]\n{node.text}\n")
            sources.append(
                {
                    "url": node.metadata.get("url", ""),
                    "title": node.metadata.get("title", ""),
                    "section": node.metadata.get("section", ""),
                    "score": float(node.score),
                    "kb_id": self.kb_id,
                    "kb_name": self.kb_name,
                }
            )
            scores.append(float(node.score))

        prompt = self._build_prompt(question, "\n".join(context_parts))
        try:
            llm = Settings.llm
            response = llm.complete(prompt)
            answer = response.text.strip()
            logger.info("[%s] Answer generated: %d chars", self.kb_id, len(answer))
        except Exception as exc:
            logger.error("[%s] Generation failed: %s", self.kb_id, exc)
            raise

        return {
            "answer": answer,
            "sources": sources,
            "scores": scores,
            "has_results": True,
            "kb_id": self.kb_id,
            "kb_name": self.kb_name,
        }

    def _build_prompt(self, question: str, context: str) -> str:
        return (
            f"You are an expert assistant for {self.kb_name}.\n\n"
            "Use the following context to answer the question. Be specific and cite sources using [Source N].\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )


class MultiKBQueryService:
    """Aggregate queries across multiple knowledge bases."""

    def __init__(self, kb_manager: KBManager):
        self.kb_manager = kb_manager
        self._kb_services: dict[str, KBQueryService] = {}
        logger.info("MultiKBQueryService initialized")

    def _get_kb_service(self, kb_config: KBConfig) -> KBQueryService:
        if kb_config.id not in self._kb_services:
            self._kb_services[kb_config.id] = KBQueryService(kb_config)
        return self._kb_services[kb_config.id]

    def query_profile(
        self,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: int = 3,
        metadata_filters: dict | None = None,
    ) -> dict:
        logger.info("Query with profile: %s", profile.value)

        kb_configs = self.kb_manager.get_kbs_for_profile(profile.value)
        if not kb_configs:
            logger.warning("No KBs found for profile: %s", profile.value)
            return {
                "answer": f"No knowledge bases available for {profile.value} profile.",
                "sources": [],
                "has_results": False,
                "kbs_queried": [],
            }

        results: list[dict] = []
        for kb_config in kb_configs:
            try:
                service = self._get_kb_service(kb_config)
                outcome = service.query(
                    question=question,
                    top_k=top_k_per_kb,
                    metadata_filters=metadata_filters,
                )
                if outcome["has_results"]:
                    results.append(outcome)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to query KB %s: %s", kb_config.id, exc)

        if not results:
            return {
                "answer": "No relevant information found across knowledge bases.",
                "sources": [],
                "has_results": False,
                "kbs_queried": [kb.id for kb in kb_configs],
            }

        return self._merge_results(results, question, profile)

    def _merge_results(
        self, all_results: list[dict], question: str, profile: QueryProfile
    ) -> dict:
        sources: list[dict] = []
        for result in all_results:
            sources.extend(result["sources"])

        sources.sort(key=lambda source: source["score"], reverse=True)

        merged_sources = sources[:6] if profile == QueryProfile.CHAT else sources[:15]
        kb_names = sorted({result["kb_name"] for result in all_results})

        if profile == QueryProfile.CHAT:
            answer_parts = [f"Based on {', '.join(kb_names)}:\n"]
            for result in all_results:
                answer = result.get("answer")
                if answer:
                    answer_parts.append(f"\n**{result['kb_name']}**: {answer}")
            consolidated_answer = "\n".join(answer_parts)
        else:
            contexts = []
            for result in all_results:
                contexts.append(
                    f"### Context from {result['kb_name']}:\n{result['answer']}"
                )
            consolidated_answer = "\n\n".join(contexts)

        return {
            "answer": consolidated_answer,
            "sources": merged_sources,
            "has_results": True,
            "kbs_queried": [result["kb_id"] for result in all_results],
            "kb_count": len(all_results),
        }

    def query_specific_kbs(
        self,
        question: str,
        kb_ids: list[str],
        top_k: int = 5,
        metadata_filters: dict | None = None,
    ) -> dict:
        logger.info("Query specific KBs: %s", kb_ids)

        results: list[dict] = []
        for kb_id in kb_ids:
            kb_config = self.kb_manager.get_kb(kb_id)
            if not kb_config or not kb_config.is_active:
                logger.warning("KB not found or inactive: %s", kb_id)
                continue

            try:
                service = self._get_kb_service(kb_config)
                outcome = service.query(
                    question=question,
                    top_k=top_k,
                    metadata_filters=metadata_filters,
                )
                if outcome["has_results"]:
                    results.append(outcome)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to query KB %s: %s", kb_id, exc)

        if not results:
            return {
                "answer": "No relevant information found.",
                "sources": [],
                "has_results": False,
                "kbs_queried": kb_ids,
            }

        return self._merge_results(results, question, QueryProfile.CHAT)

    def query_kbs(
        self,
        question: str,
        kb_ids: list[str],
        top_k_per_kb: int = 5,
        metadata_filters: dict | None = None,
    ) -> dict:
        return self.query_specific_kbs(
            question=question,
            kb_ids=kb_ids,
            top_k=top_k_per_kb,
            metadata_filters=metadata_filters,
        )

