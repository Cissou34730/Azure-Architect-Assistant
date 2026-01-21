from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def _ensure_backend_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))


_ensure_backend_on_path()

from app.core.app_settings import get_settings
from app.agents_system.runner import initialize_agent_runner, shutdown_agent_runner, get_agent_runner
from app.services.mcp.learn_mcp_client import MicrosoftLearnMCPClient


async def main(message: str) -> None:
    settings = get_settings()

    try:
        mcp_config = settings.get_mcp_server_config("microsoft_learn")
    except Exception as e:
        print(f"Failed to load MCP config: {e}")
        return

    mcp_client = MicrosoftLearnMCPClient(mcp_config)
    try:
        await mcp_client.initialize()
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")
        return

    # Initialize global agent runner
    try:
        await initialize_agent_runner(mcp_client)
    except Exception as e:
        print(f"Failed to initialize agent runner: {e}")
        await mcp_client.close()
        return

    try:
        runner = await get_agent_runner()
        result = await runner.execute_query(message)
        print("Success:", result.get("success"))
        print("Answer:\n", result.get("output") or result.get("answer") or "")
    except Exception as e:
        print(f"Agent execution failed: {e}")
    finally:
        # Clean up
        try:
            await shutdown_agent_runner()
        finally:
            await mcp_client.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Call internal agent runner without HTTP")
    p.add_argument("message", help="Message to send to the agent")
    args = p.parse_args()

    asyncio.run(main(args.message))

