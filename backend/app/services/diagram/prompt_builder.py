"""Prompt builder for diagram generation with shared patterns."""


from app.models.diagram import DiagramType


class PromptBuilder:
    """
    Shared LLM prompt patterns for diagram generation.

    Abstracts common prompt structures for Mermaid and PlantUML diagrams,
    avoiding duplication across different diagram types.
    """

    @staticmethod
    def build_generation_prompt(
        description: str,
        diagram_type: DiagramType,
        previous_error: str | None = None,
    ) -> str:
        """
        Build prompt for diagram generation.

        Args:
            description: Input architecture description
            diagram_type: Type of diagram to generate
            previous_error: Error from previous attempt (for retry)

        Returns:
            Formatted prompt for LLM
        """
        base_prompt = f"""Generate a {diagram_type.value} diagram from this description:

{description}

"""

        if diagram_type == DiagramType.MERMAID_FUNCTIONAL:
            base_prompt += """Create a Mermaid flowchart showing functional flow.

Use this syntax:
```mermaid
graph TD
    A[Component] --> B[Another Component]
    B --> C{Decision}
    C -->|Yes| D[Action]
    C -->|No| E[Alternative]
```

Requirements:
- Use graph TD (top-down) or graph LR (left-right)
- Clear node labels
- Show data flow and decisions
- Max 20 nodes for readability
"""

        elif diagram_type == DiagramType.C4_CONTEXT:
            base_prompt += """Create a C4 Context diagram showing system boundaries and external actors.

Use Mermaid C4Context syntax:
```mermaid
C4Context
    title System Context diagram for [System Name]

    Person(user, "User", "External user")
    System(system, "Main System", "Core functionality")
    System_Ext(external, "External System", "Third party")

    Rel(user, system, "Uses")
    Rel(system, external, "Calls API")
```

Requirements:
- Show Person (users/actors) and System elements only
- At least one Person element
- Use System_Ext for external systems
- Clear relationships with Rel()
"""

        elif diagram_type == DiagramType.C4_CONTAINER:
            base_prompt += """Create a C4 Container diagram showing application components.

Use Mermaid C4Container syntax:
```mermaid
C4Container
    title Container diagram for [System Name]

    Person(user, "User")

    Container_Boundary(c1, "System Name") {
        Container(web, "Web Application", "React", "UI")
        Container(api, "API", "FastAPI", "Backend")
        ContainerDb(db, "Database", "PostgreSQL", "Data storage")
    }

    Rel(user, web, "Uses", "HTTPS")
    Rel(web, api, "Calls", "REST")
    Rel(api, db, "Reads/Writes", "SQL")
```

Requirements:
- Show Container elements within system boundary
- Use Container_Boundary to group
- Include technology choices
- No Component elements (wrong abstraction level)
"""

        elif diagram_type == DiagramType.PLANTUML_AZURE:
            base_prompt += """Create a PlantUML diagram with Azure service icons.

Use C4-PlantUML syntax with Azure-PlantUML sprites:
```plantuml
@startuml
!include <C4/C4_Container>
!include <azure/AzureCommon>
!include <azure/Compute/AzureFunctions>
!include <azure/Databases/AzureCosmosDb>
!include <azure/Storage/AzureBlobStorage>

Person(user, "User")
Container(web, "Web App", "React")
AzureFunctions(functions, "Functions", "Serverless compute")
AzureCosmosDb(cosmos, "Cosmos DB", "NoSQL database")

Rel(user, web, "Uses")
Rel(web, functions, "Calls")
Rel(functions, cosmos, "Stores data")
@enduml
```

Requirements:
- Use !include for C4 and Azure libraries
- Map Azure services to correct sprites (e.g., "azure function" → AzureFunctions)
- Use Azure service names in descriptions
- Show relationships between services
"""

        if previous_error:
            base_prompt += f"""

IMPORTANT: Previous attempt failed with this error:
{previous_error}

Fix the error and regenerate the diagram.
"""

        base_prompt += (
            "\nReturn ONLY the diagram code, no explanations or markdown formatting."
        )

        return base_prompt

    @staticmethod
    def build_ambiguity_prompt(description: str) -> str:
        """
        Build prompt for ambiguity detection.

        Args:
            description: Input description to analyze

        Returns:
            Formatted prompt for ambiguity detection
        """
        return f"""Analyze this architecture description for unclear elements:

{description}

Identify:
1. Vague component names ("the system", "the service")
2. Unclear relationships ("communicates with", "uses")
3. Missing specifications (no technology, no protocol)
4. Ambiguous requirements ("fast", "scalable", "secure")

Return JSON:
{{
  "ambiguities": [
    {{
      "text": "exact ambiguous text",
      "issue": "why it's unclear",
      "clarification": "specific question to ask"
    }}
  ]
}}
"""

    @staticmethod
    def build_retry_prompt(
        original_prompt: str,
        error_feedback: str,
        attempt: int,
    ) -> str:
        """
        Build prompt for retry attempt with error feedback.

        Args:
            original_prompt: Original generation prompt
            error_feedback: Error message from validation
            attempt: Retry attempt number (1-3)

        Returns:
            Enhanced prompt with error context
        """
        return f"""{original_prompt}

RETRY ATTEMPT {attempt}/3

Previous generation failed validation:
{error_feedback}

Fix the issues and regenerate. Return ONLY the corrected diagram code.
"""

