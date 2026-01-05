"""C4 compliance validation service (Layer 4 validation).

Validates C4 diagram abstraction levels to ensure Context diagrams only contain
Person and System elements, and Container diagrams only contain Container elements.
"""

import logging
import re
from typing import List, Set
from dataclasses import dataclass

from app.models.diagram import DiagramType

logger = logging.getLogger(__name__)


@dataclass
class C4ValidationResult:
    """Result of C4 compliance validation."""
    is_valid: bool
    violations: List[str]
    
    def __bool__(self) -> bool:
        return self.is_valid


class C4ComplianceValidator:
    """Validates C4 diagram abstraction level compliance."""
    
    # Allowed elements per C4 diagram type
    C4_CONTEXT_ELEMENTS: Set[str] = {"Person", "System", "System_Ext", "Boundary", "SystemDb", "SystemQueue"}
    C4_CONTAINER_ELEMENTS: Set[str] = {
        "Container", "ContainerDb", "ContainerQueue", "Container_Ext",
        "Boundary", "Person", "System_Ext"  # Person and external systems allowed in Container diagrams
    }
    
    def __init__(self) -> None:
        """Initialize C4 compliance validator."""
        pass

    async def validate_c4_compliance(
        self,
        diagram_source: str,
        diagram_type: DiagramType
    ) -> C4ValidationResult:
        """Validate C4 diagram abstraction level compliance.
        
        Args:
            diagram_source: C4 diagram source code
            diagram_type: Type of diagram (c4_context or c4_container)
            
        Returns:
            C4ValidationResult with violations list
        """
        logger.info("Validating C4 compliance for type: %s", diagram_type)
        
        # Only validate C4 diagram types
        if diagram_type not in [DiagramType.C4_CONTEXT, DiagramType.C4_CONTAINER]:
            logger.debug("Skipping C4 validation for non-C4 diagram type: %s", diagram_type)
            return C4ValidationResult(is_valid=True, violations=[])
        
        violations: List[str] = []
        
        # Extract all C4 element types from diagram source
        elements_used: Set[str] = self._extract_c4_elements(diagram_source)
        
        if diagram_type == DiagramType.C4_CONTEXT:
            violations = self._validate_context_elements(elements_used)
        elif diagram_type == DiagramType.C4_CONTAINER:
            violations = self._validate_container_elements(elements_used)
        
        is_valid: bool = len(violations) == 0
        
        if not is_valid:
            logger.warning("C4 compliance violations found: %s", violations)
        else:
            logger.info("C4 compliance validation passed")
        
        return C4ValidationResult(is_valid=is_valid, violations=violations)
    
    def _extract_c4_elements(self, source_code: str) -> Set[str]:
        """Extract all C4 element types from diagram source.
        
        Matches patterns like:
        - Person(user, "User")
        - System(api, "API")
        - Container(web, "Web App")
        - ContainerDb(db, "Database")
        
        Args:
            source_code: C4 diagram source
            
        Returns:
            Set of element type names used in diagram
        """
        # Pattern to match C4 element declarations
        # Matches: Person(...), System(...), Container(...), etc.
        pattern = r'\b([A-Z][a-zA-Z_]*)\s*\('
        
        matches = re.finditer(pattern, source_code)
        elements: Set[str] = {match.group(1) for match in matches}
        
        logger.debug("Extracted C4 elements: %s", elements)
        return elements
    
    def _validate_context_elements(self, elements_used: Set[str]) -> List[str]:
        """Validate C4 Context diagram elements.
        
        Context diagrams (Level 1) should only contain:
        - Person: Users/actors
        - System: Internal systems
        - System_Ext: External systems
        - SystemDb: System-level databases
        - SystemQueue: System-level message queues
        - Boundary: System boundaries
        
        Args:
            elements_used: Set of element types found in diagram
            
        Returns:
            List of violation messages
        """
        violations: List[str] = []
        
        disallowed_elements: Set[str] = elements_used - self.C4_CONTEXT_ELEMENTS
        
        for element in disallowed_elements:
            if element.startswith("Container"):
                violations.append(
                    f"C4 Context diagram contains Container-level element '{element}'. "
                    f"Context diagrams (Level 1) should only show Person, System, and Boundary elements."
                )
            elif element not in ["Rel", "Rel_D", "Rel_U", "Rel_L", "Rel_R", "Rel_Back"]:
                # Ignore relationship elements
                violations.append(
                    f"C4 Context diagram contains unknown element type '{element}'. "
                    f"Allowed elements: {', '.join(sorted(self.C4_CONTEXT_ELEMENTS))}"
                )
        
        return violations
    
    def _validate_container_elements(self, elements_used: Set[str]) -> List[str]:
        """Validate C4 Container diagram elements.
        
        Container diagrams (Level 2) should contain:
        - Container: Application containers
        - ContainerDb: Container-level databases
        - ContainerQueue: Container-level message queues
        - Container_Ext: External containers
        - Person: Users (allowed for context)
        - System_Ext: External systems (allowed for context)
        - Boundary: Container boundaries
        
        Should NOT contain System or SystemDb (those are Context-level)
        
        Args:
            elements_used: Set of element types found in diagram
            
        Returns:
            List of violation messages
        """
        violations: List[str] = []
        
        disallowed_elements: Set[str] = elements_used - self.C4_CONTAINER_ELEMENTS
        
        for element in disallowed_elements:
            if element in ["System", "SystemDb", "SystemQueue"]:
                violations.append(
                    f"C4 Container diagram contains System-level element '{element}'. "
                    f"Container diagrams (Level 2) should show Container elements, not System-level abstractions. "
                    f"Use Container, ContainerDb, or ContainerQueue instead."
                )
            elif element not in ["Rel", "Rel_D", "Rel_U", "Rel_L", "Rel_R", "Rel_Back"]:
                # Ignore relationship elements
                violations.append(
                    f"C4 Container diagram contains unknown element type '{element}'. "
                    f"Allowed elements: {', '.join(sorted(self.C4_CONTAINER_ELEMENTS))}"
                )
        
        return violations
