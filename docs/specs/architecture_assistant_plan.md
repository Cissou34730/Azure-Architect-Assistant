# Architecture Assistant – Full Implementation Plan (Python + LlamaIndex + MCP + ReAct + Router + Conversation Memory)

This document contains the complete ordered task list for implementing:
- Specialized ReAct agents (RAG Agent + MCP Agent)
- An LLM-based Router
- Conversation memory + LLM summarization
- Full separation of responsibilities
- Clean project layout

## 0. Project Structure

Create or refactor into the following layout:

```
app/
  __init__.py

  config/
    __init__.py
    settings.py

  rag/
    __init__.py
    index.py
    tool.py

  mcp/
    __init__.py
    client.py
    tool.py

  agents/
    __init__.py
    base.py
    rag_agent.py
    mcp_agent.py

  router/
    __init__.py
    llm_router.py

  conversation/
    __init__.py
    models.py
    memory.py
    summarizer.py

  runner.py
```

## 1. Core Dependencies

Install and use:
- llama-index
- openai or llama-index-llms-openai
- pydantic
- httpx (if MCP HTTP)
- or Python MCP client

## 2. Global Configuration (`config/settings.py`)

Define a Settings class with:
- OPENAI_API_KEY
- ROUTER_MODEL_NAME
- AGENT_MODEL_NAME
- MEMORY_MODEL_NAME
- MCP_ENDPOINT_URL or MCP_CONFIG_PATH

## 3. RAG Index (`rag/index.py`)

Implement `get_rag_query_engine()` returning a LlamaIndex QueryEngine.

## 4. RAG Tool (`rag/tool.py`)

Wrap RAG as a tool:
- `rag_query_tool(query, scope) -> str`

## 5. MCP Client Wrapper (`mcp/client.py`)

Provide a unified client interface whether using MCP Python client or HTTP.

## 6. MCP Tool (`mcp/tool.py`)

Implement:
- `mcp_call_tool(service, action, params) -> dict`

## 7. Agent Base Class (`agents/base.py`)

Defines:
```
async def run(self, user_message, state) -> str
```

## 8. RAG Agent

ReAct loop:
- Use conversation summary
- Decide answer vs rag_query_tool
- Finalize with LLM

## 9. MCP Agent

ReAct loop:
- Use conversation summary
- Decide answer vs mcp_call_tool
- Finalize with LLM

## 10. Conversation Models (`conversation/models.py`)

Implement:
- Turn
- ConversationState (summary + turns)

## 11. Conversation Memory (`conversation/memory.py`)

Store & manage per-session memory and summary.

## 12. Summarizer (`conversation/summarizer.py`)

LLM updates summary using:
- previous summary
- last N turns

## 13. Router (`router/llm_router.py`)

LLM chooses between:
- "RAG"
- "MCP"

Delegates to appropriate agent.

## 14. Execution Runner (`runner.py`)

A simple REPL:
- Append user turn
- Route to agent
- Append assistant turn
- Summarize
- Print answer

## 15. Flow Summary

User → Router → Agent → Tool → Agent → Memory → Summary → next turn.

## 16. Principles

- Router = classification only
- Agents = ReAct loops
- Tools = pure functions
- Summary injected in agent prompts
- Modular & scalable design

## 17. Result

A clean multi-agent architecture with:
- Deterministic tool boundaries
- Scalable routing logic
- Conversation state management
- Prompt-injected memory
