"""Multi-source KB query compatibility utilities."""

import logging
from enum import Enum
from typing import Any

from llama_index.core import Settings

from app.shared.config.app_settings import get_app_settings

from .knowledge_base_manager import KBManager
from .models import KBConfig
from .service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class KBQueryService:
    """Infrastructure-local per-KB query execution used by the compatibility service."""

    def __init__(
        self,
        kb_config: KBConfig,
        similarity_threshold: float | None = None,
        min_results: int | None = None,
    ):
        self.kb_config = kb_config
        self.kb_id = kb_config.id
        self.kb_name = kb_config.name

        app_settings = get_app_settings()
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else app_settings.search_similarity_threshold
        )
        self.min_results = (
            min_results if min_results is not None else app_settings.search_min_results
        )
        self.initial_retrieve_multiplier = app_settings.search_initial_retrieve_multiplier
        self.min_initial_retrieve = app_settings.search_min_initial_retrieve

    def query(
        self,
        question: str,
        top_k: int = 5,
        metadata_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.info("[%s] Processing query: %s...", self.kb_id, question[:100])

        index = KnowledgeBaseService(self.kb_config).get_index()
        initial_retrieve_count = max(
            top_k * self.initial_retrieve_multiplier,
            self.min_initial_retrieve,
        )
        retriever = index.as_retriever(similarity_top_k=initial_retrieve_count)

        if metadata_filters:
            from llama_index.core.vector_stores import (  # noqa: PLC0415
                MetadataFilter,
                MetadataFilters,
            )

            filters = MetadataFilters(
                filters=[
                    MetadataFilter(key=key, value=value)
                    for key, value in metadata_filters.items()
                ]
            )
            retriever = index.as_retriever(
                similarity_top_k=initial_retrieve_count,
                filters=filters,
            )

        retrieved_nodes = retriever.retrieve(question)
        logger.info("[%s] Retrieved %d nodes", self.kb_id, len(retrieved_nodes))

        filtered_nodes = [
            node for node in retrieved_nodes if node.score >= self.similarity_threshold
        ]
        if not filtered_nodes and retrieved_nodes:
            filtered_nodes = retrieved_nodes[: self.min_results]

        filtered_nodes = filtered_nodes[:top_k]
        if not filtered_nodes:
            return {
                "answer": f"No relevant information found in {self.kb_name}.",
                "sources": [],
                "scores": [],
                "has_results": False,
                "kb_id": self.kb_id,
                "kb_name": self.kb_name,
            }

        context_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        scores: list[float] = []
        for index_position, node in enumerate(filtered_nodes, 1):
            context_parts.append(
                f"[Source {index_position} - {self.kb_name}]\n{node.text}\n"
            )
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
        response = Settings.llm.complete(prompt)

        return {
            "answer": response.text.strip(),
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


class QueryProfile(str, Enum):
    CHAT = "chat"
    PROPOSAL = "proposal"


class MultiSourceQueryService:
    """Service for querying multiple knowledge bases."""

    def __init__(self, kb_manager: KBManager):
        self.kb_manager = kb_manager
        self._kb_query_services: dict[str, Any] = {}
        logger.info("MultiSourceQueryService initialized")

    def _get_kb_query_service(self, kb_config: KBConfig) -> Any:
        if kb_config.id not in self._kb_query_services:
            self._kb_query_services[kb_config.id] = KBQueryService(kb_config)
        return self._kb_query_services[kb_config.id]

    def query_profile(
        self,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: int = 3,
        metadata_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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

        all_results = []
        failed_kbs = []
        for kb_config in kb_configs:
            try:
                kb_service = self._get_kb_query_service(kb_config)
                result = kb_service.query(
                    question=question,
                    top_k=top_k_per_kb,
                    metadata_filters=metadata_filters,
                )
                if result["has_results"]:
                    all_results.append(result)
            except FileNotFoundError as exc:
                logger.warning("KB %s not indexed yet: %s", kb_config.id, exc)
                failed_kbs.append(f"{kb_config.id} (not indexed)")
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to query KB %s: %s", kb_config.id, exc)
                failed_kbs.append(f"{kb_config.id} (error)")

        if not all_results:
            failure_msg = f" ({', '.join(failed_kbs)} not available)" if failed_kbs else ""
            return {
                "answer": f"Knowledge bases are not yet indexed{failure_msg}. Please use microsoft_docs_search for official documentation instead.",
                "sources": [],
                "has_results": False,
                "kbs_queried": [kb.id for kb in kb_configs],
                "kbs_failed": failed_kbs,
            }

        return self._merge_results(all_results, profile)

    def _merge_results(
        self,
        all_results: list[dict[str, Any]],
        profile: QueryProfile,
    ) -> dict[str, Any]:
        all_sources: list[dict[str, Any]] = []
        for result in all_results:
            all_sources.extend(result["sources"])

        all_sources.sort(key=lambda source: source["score"], reverse=True)
        merged_sources = all_sources[:6] if profile == QueryProfile.CHAT else all_sources[:15]

        kb_names = list({result["kb_name"] for result in all_results})
        if profile == QueryProfile.CHAT:
            answer_parts = [f"Based on {', '.join(kb_names)}:\n"]
            for result in all_results:
                if result.get("answer"):
                    answer_parts.append(f"\n**{result['kb_name']}**: {result['answer']}")
            consolidated_answer = "\n".join(answer_parts)
        else:
            contexts = [
                f"### Context from {result['kb_name']}:\n{result.get('answer', '')}"
                for result in all_results
            ]
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
        metadata_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.info("Query specific KBs: %s", kb_ids)

        all_results = []
        for kb_id in kb_ids:
            kb_config = self.kb_manager.get_kb(kb_id)
            if not kb_config or not kb_config.is_active:
                logger.warning("KB not found or inactive: %s", kb_id)
                continue

            try:
                kb_service = self._get_kb_query_service(kb_config)
                result = kb_service.query(
                    question=question,
                    top_k=top_k,
                    metadata_filters=metadata_filters,
                )
                if result["has_results"]:
                    all_results.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to query KB %s: %s", kb_id, exc)

        if not all_results:
            return {
                "answer": "No relevant information found.",
                "sources": [],
                "has_results": False,
                "kbs_queried": kb_ids,
            }

        return self._merge_results(all_results, QueryProfile.CHAT)

    def query_kbs(
        self,
        question: str,
        kb_ids: list[str],
        top_k_per_kb: int = 5,
        metadata_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.query_specific_kbs(
            question=question,
            kb_ids=kb_ids,
            top_k=top_k_per_kb,
            metadata_filters=metadata_filters,
        )

    def get_kb_health(self) -> dict[str, Any]:
        kbs = self.kb_manager.get_active_kbs()
        health: dict[str, Any] = {}
        for kb in kbs:
            try:
                service = KnowledgeBaseService(kb)
                health[kb.id] = {
                    "name": kb.name,
                    "status": "ready" if service.is_index_ready() else "not_indexed",
                    "profiles": kb.profiles,
                    "index_path": kb.index_path,
                }
            except Exception as exc:  # noqa: BLE001
                health[kb.id] = {
                    "name": kb.name,
                    "status": "error",
                    "profiles": kb.profiles,
                    "index_path": kb.index_path,
                    "error": str(exc),
                }
        return health
