"""
ToolRegistry: provide a single place to build and expose tools for agents.
"""
from typing import List, Any

from ..tools.mcp_tool import create_mcp_tools
from ..tools.kb_tool import create_kb_tools
from ..tools.aaa_candidate_tool import create_aaa_tools


async def build_tools(mcp_client=None) -> List[Any]:
    # Keep signature flexible: some callers may pass a client, others not.
    tools = []
    if mcp_client is not None:
        mcp_tools = await create_mcp_tools(mcp_client)
        tools.extend(mcp_tools)
    tools.extend(create_kb_tools())
    tools.extend(create_aaa_tools())
    return tools
