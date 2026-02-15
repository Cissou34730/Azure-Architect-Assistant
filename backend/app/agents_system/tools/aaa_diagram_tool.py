"""AAA Diagram Persistence Tool

Allows agent to create and persist diagrams via the diagram-set API,
then store references in ProjectState for retrieval.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

logger = logging.getLogger(__name__)


class AAACreateDiagramSetInput(BaseModel):
    """Input schema for creating diagram set."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    input_description: str = Field(
        min_length=10,
        description="Functional requirements or architecture description for diagram generation"
    )
    adr_id: str | None = Field(
        default=None,
        description="Optional ADR identifier to link diagrams to a specific decision"
    )


class AAACreateDiagramSetToolInput(BaseModel):
    """Raw tool payload wrapper."""

    payload: str | dict[str, Any] = Field(
        description=(
            "A JSON object (or JSON string) matching AAACreateDiagramSetInput. Example: "
            "{\"inputDescription\":\"E-commerce platform...\",\"adrId\":\"adr-001\"}"
        )
    )


class AAACreateDiagramSetTool(BaseTool):
    name: str = "aaa_create_diagram_set"
    description: str = (
        "Create and persist architecture diagrams (Mermaid functional, C4 context, C4 container). "
        "This tool generates diagrams from a functional description and stores them "
        "in the diagram database, then adds references to ProjectState.diagrams[]. "
        "Use this when the user requests diagrams or when diagrams would help visualize the architecture."
    )

    args_schema: type[BaseModel] = AAACreateDiagramSetToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(payload=payload, **kwargs))

    async def _arun(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = self._validate_args(raw_data)
            result = await self._generate_and_persist(args)
            return result

        except Exception as exc:
            logger.error(f"Failed to create diagram set: {exc}", exc_info=True)
            return f"ERROR: {exc!s}"

    def _parse_payload(
        self, payload: str | dict[str, Any] | None, **kwargs: Any
    ) -> dict[str, Any]:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                raise ValueError("Missing payload for aaa_create_diagram_set")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Invalid JSON payload. Provide a JSON object in Action Input."
                ) from exc
        if isinstance(payload, dict):
            return payload
        raise ValueError("Invalid payload type for aaa_create_diagram_set")

    def _validate_args(self, data: dict[str, Any]) -> AAACreateDiagramSetInput:
        try:
            return AAACreateDiagramSetInput.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Validation failed: {exc!s}") from exc

    async def _generate_and_persist(self, args: AAACreateDiagramSetInput) -> str:
        logger.info(
            f"Creating diagram set (adr_id={args.adr_id}, description_len={len(args.input_description)})"
        )

        # Import services here to avoid circular dependencies
        from app.models.diagram import (  # noqa: PLC0415
            AmbiguityReport,
            Diagram,
            DiagramSet,
            DiagramType,
        )
        from app.services.diagram.ambiguity_detector import (  # noqa: PLC0415
            AmbiguityDetector,
        )
        from app.services.diagram.database import get_diagram_session  # noqa: PLC0415
        from app.services.diagram.diagram_generator import (  # noqa: PLC0415
            DiagramGenerator,
        )
        from app.services.diagram.llm_client import DiagramLLMClient  # noqa: PLC0415

        try:
            llm_client = DiagramLLMClient()
            ambiguity_detector = AmbiguityDetector(llm_client)
            diagram_generator = DiagramGenerator(llm_client)

            # Get diagram database session
            async for diagram_session in get_diagram_session():
                # Create DiagramSet record
                diagram_set = DiagramSet(
                    adr_id=args.adr_id,
                    input_description=args.input_description,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                diagram_session.add(diagram_set)
                await diagram_session.flush()  # Get ID
                logger.info(f"✓ Created DiagramSet: id={diagram_set.id}")

                # Detect ambiguities
                ambiguities_data = await ambiguity_detector.analyze_description(args.input_description)
                for amb_data in ambiguities_data:
                    ambiguity = AmbiguityReport(
                        diagram_set_id=diagram_set.id,
                        ambiguous_text=amb_data["ambiguous_text"],
                        suggested_clarification=amb_data.get("suggested_clarification"),
                        resolved=False,
                        created_at=datetime.now(timezone.utc),
                    )
                    diagram_session.add(ambiguity)

                # Generate 3 diagrams in parallel
                logger.info("Generating 3 diagrams in parallel...")
                (
                    functional_result,
                    c4_context_result,
                    c4_container_result,
                ) = await asyncio.gather(
                    diagram_generator.generate_mermaid_functional(description=args.input_description),
                    diagram_generator.generate_c4_context(description=args.input_description),
                    diagram_generator.generate_c4_container(description=args.input_description),
                )

                # Store diagrams and build state update
                diagram_refs = []
                for gen_result, diagram_type in [
                    (functional_result, DiagramType.MERMAID_FUNCTIONAL),
                    (c4_context_result, DiagramType.C4_CONTEXT),
                    (c4_container_result, DiagramType.C4_CONTAINER),
                ]:
                    diagram = Diagram(
                        diagram_set_id=diagram_set.id,
                        diagram_type=diagram_type.value,
                        source_code=gen_result.source_code,
                        rendered_svg=None,  # Mermaid rendered client-side
                        rendered_png=None,
                        version="1.0.0",
                        previous_version_id=None,
                        created_at=datetime.now(timezone.utc),
                    )
                    diagram_session.add(diagram)
                    await diagram_session.flush()  # Get ID

                    # Frontend expects: {id, diagramType, sourceCode, version, createdAt}
                    diagram_refs.append({
                        "id": diagram.id,
                        "diagramType": diagram_type.value,
                        "sourceCode": gen_result.source_code,
                        "version": "1.0.0",
                        "createdAt": diagram.created_at.isoformat(),
                    })
                    logger.info(f"✓ Diagram persisted: type={diagram_type.value}, id={diagram.id}")

                await diagram_session.commit()
                logger.info(f"✓ DiagramSet committed: id={diagram_set.id}, diagrams={len(diagram_refs)}")

                # Build state update payload (with full sourceCode for ProjectState)
                updates = {
                    "diagrams": diagram_refs
                }
                payload_str = json.dumps(updates, ensure_ascii=False, indent=2)

                # Build concise user-facing message (no full diagram code in chat)
                diagram_names = []
                for ref in diagram_refs:
                    dtype = ref["diagramType"]
                    if dtype == "mermaid_functional":
                        diagram_names.append("Functional Flow")
                    elif dtype == "c4_context":
                        diagram_names.append("C4 Context")
                    elif dtype == "c4_container":
                        diagram_names.append("C4 Container")
                    else:
                        diagram_names.append(dtype)

                return (
                    f"✓ Diagrams ready: {', '.join(diagram_names)}\n"
                    "\n"
                    "AAA_STATE_UPDATE\n"
                    "```json\n"
                    f"{payload_str}\n"
                    "```"
                )

        except Exception as exc:
            logger.error(f"Failed to generate diagrams: {exc}", exc_info=True)
            raise


def create_diagram_tools() -> list[BaseTool]:
    """Factory returning diagram tools."""
    return [AAACreateDiagramSetTool()]

