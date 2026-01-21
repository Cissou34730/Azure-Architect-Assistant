"""Visual quality checker service (Layer 3 validation).

Checks diagram quality metrics like node count, edge count, complexity.
Non-blocking - logs warnings for quality issues but doesn't fail generation.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Quality assessment report for diagram."""

    is_acceptable: bool
    issues: list[str]
    warnings: list[str]
    severity: str  # "INFO", "WARNING", "ERROR"
    metrics: dict

    def __bool__(self) -> bool:
        # Always true - non-blocking validation
        return True


class VisualQualityChecker:
    """Checks visual quality metrics for diagrams."""

    # Quality thresholds (configurable)
    MAX_NODES = 20  # Readability threshold
    MAX_EDGES = 30  # Avoid spaghetti
    MAX_DEPTH = 5  # Avoid deep nesting

    def _validate_thresholds(
        self, nodes: list[str], edges: list[str], orphans: set[str], depth: int
    ) -> tuple[list[str], list[str]]:
        """Validate calculated metrics against visual quality thresholds."""
        issues = []
        warnings = []

        if len(nodes) > self.MAX_NODES:
            warnings.append(
                f"High node count ({len(nodes)}>{self.MAX_NODES}): "
                "Consider splitting into multiple diagrams"
            )

        if len(edges) > self.MAX_EDGES:
            warnings.append(
                f"High edge count ({len(edges)}>{self.MAX_EDGES}): "
                "Diagram may be too complex"
            )

        if orphans:
            issues.append(
                f"Orphan nodes detected ({len(orphans)}): {', '.join(list(orphans)[:5])}"
            )

        if depth > self.MAX_DEPTH:
            warnings.append(
                f"Deep nesting ({depth} levels): Consider flattening structure"
            )

        return issues, warnings

    async def check_mermaid_visual_quality(self, source_code: str) -> QualityReport:
        """Check Mermaid diagram visual quality metrics."""
        logger.info(
            "Checking Mermaid visual quality (length: %d chars)", len(source_code)
        )

        nodes = self._extract_mermaid_nodes(source_code)
        edges = self._extract_mermaid_edges(source_code)
        orphans = self._find_orphan_nodes(nodes, edges)
        depth = self._calculate_depth(source_code)

        metrics = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "orphan_count": len(orphans),
            "depth": depth,
        }

        issues, warnings = self._validate_thresholds(nodes, edges, orphans, depth)

        # Determine severity
        severity = "ERROR" if issues else ("WARNING" if warnings else "INFO")

        logger.info(
            "Quality check complete: nodes=%d, edges=%d, orphans=%d, depth=%d, severity=%s",
            len(nodes),
            len(edges),
            len(orphans),
            depth,
            severity,
        )

        if warnings:
            for warning in warnings:
                logger.warning("Quality warning: %s", warning)

        if issues:
            for issue in issues:
                logger.error("Quality issue: %s", issue)

        return QualityReport(
            is_acceptable=len(issues) == 0,  # Only fail on errors, not warnings
            issues=issues,
            warnings=warnings,
            severity=severity,
            metrics=metrics,
        )

    def _extract_mermaid_nodes(self, source_code: str) -> set[str]:
        """Extract node IDs from Mermaid diagram.

        Matches patterns like:
        - A[Label]
        - A(Label)
        - A{Label}
        - A((Label))
        - Person(id, "Label")

        Args:
            source_code: Mermaid source

        Returns:
            Set of node IDs
        """
        nodes: set[str] = set()

        # Pattern for flowchart nodes: ID[text] or ID(text) or ID{text}
        flowchart_pattern = r"\b([A-Za-z0-9_]+)[\[\(\{]"
        nodes.update(re.findall(flowchart_pattern, source_code))

        # Pattern for C4 elements: Person(id, ...) or System(id, ...)
        c4_pattern = r"(?:Person|System|Container|Component|ContainerDb|ContainerQueue)\(([A-Za-z0-9_]+)"
        nodes.update(re.findall(c4_pattern, source_code))

        # Filter out Mermaid keywords
        keywords: set[str] = {
            "graph",
            "flowchart",
            "TB",
            "TD",
            "LR",
            "RL",
            "BT",
            "subgraph",
            "end",
            "style",
            "class",
        }
        nodes = {n for n in nodes if n not in keywords}

        return nodes

    def _extract_mermaid_edges(self, source_code: str) -> list[tuple[str, str]]:
        """Extract edges/relationships from Mermaid diagram.

        Matches arrow patterns like:
        - A --> B
        - A -.-> B
        - A ==> B
        - Rel(A, B, ...)

        Args:
            source_code: Mermaid source

        Returns:
            List of (from_node, to_node) tuples
        """
        edges: list[tuple[str, str]] = []

        # Pattern for flowchart arrows: A --> B
        arrow_pattern = (
            r"\b([A-Za-z0-9_]+)\s*(?:-->|---|-\.-|==>|===)\s*([A-Za-z0-9_]+)"
        )
        edges.extend(re.findall(arrow_pattern, source_code))

        # Pattern for C4 relationships: Rel(A, B, ...)
        rel_pattern = r"(?:Rel|BiRel)\(([A-Za-z0-9_]+),\s*([A-Za-z0-9_]+)"
        edges.extend(re.findall(rel_pattern, source_code))

        return edges

    def _find_orphan_nodes(
        self, nodes: set[str], edges: list[tuple[str, str]]
    ) -> set[str]:
        """Find nodes not connected to any edges.

        Args:
            nodes: All node IDs
            edges: All edges (from, to)

        Returns:
            Set of orphan node IDs
        """
        connected_nodes: set[str] = set()
        for from_node, to_node in edges:
            connected_nodes.add(from_node)
            connected_nodes.add(to_node)

        return nodes - connected_nodes

    def _calculate_depth(self, source_code: str) -> int:
        """Calculate nesting depth in diagram.

        For flowcharts: subgraph nesting levels
        For C4: Boundary nesting levels

        Args:
            source_code: Mermaid source

        Returns:
            Maximum nesting depth
        """
        max_depth: int = 0
        current_depth: int = 0

        lines: list[str] = source_code.split("\n")
        for raw_line in lines:
            line = raw_line.strip()

            # Check for subgraph or Boundary opening
            if line.startswith("subgraph") or ("Boundary" in line and "(" in line):
                current_depth += 1
                max_depth = max(max_depth, current_depth)

            # Check for end
            if line in {"end", "}"}:
                current_depth = max(0, current_depth - 1)

        return max_depth

