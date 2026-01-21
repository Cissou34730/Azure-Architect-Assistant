"""
PromptBuilder: construct system prompt + template for ReAct flows.
"""

from langchain.prompts import PromptTemplate


def build_prompt_template(system_prompt: str, tools: list[dict] | None = None) -> PromptTemplate:
    tools = tools or []
    tools_text = "\n".join([f"{t['name']}: {t.get('description','')}" for t in tools])
    template = f"{system_prompt}\n\n{{input}}\n\nTOOLS:\n{tools_text}\n\n{{agent_scratchpad}}"
    return PromptTemplate(template=template, input_variables=["input", "agent_scratchpad"])

