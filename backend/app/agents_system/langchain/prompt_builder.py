"""
PromptBuilder: construct system prompt + template for ReAct flows.
"""

from langchain.prompts import PromptTemplate


def build_prompt_template(system_prompt: str, tools: list[dict] | None = None) -> PromptTemplate:
    """
    Build a LangChain ReAct-compatible prompt.

    Requirements from `create_react_agent`:
    - `input`
    - `agent_scratchpad`
    - `tools` (can be partial)
    - `tool_names` (can be partial)
    """
    tools = tools or []
    tools_text = "\n".join([f"{t['name']}: {t.get('description', '')}" for t in tools])
    tool_names_text = ", ".join([t["name"] for t in tools if "name" in t])

    template = system_prompt
    if "{input}" not in template:
        template = f"{template}\n\nQuestion: {{input}}"
    if "{agent_scratchpad}" not in template:
        template = f"{template}\n\nThought: {{agent_scratchpad}}"
    if "{tools}" not in template:
        template = f"{template}\n\nAvailable tools:\n{{tools}}"
    if "{tool_names}" not in template:
        template = f"{template}\n\nAllowed tool names: {{tool_names}}"

    return PromptTemplate.from_template(
        template,
        partial_variables={
            "tools": tools_text,
            "tool_names": tool_names_text,
        },
    )

