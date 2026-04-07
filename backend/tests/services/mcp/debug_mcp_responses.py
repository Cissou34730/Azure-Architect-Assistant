"""
Debug script to capture and inspect raw MCP responses from Microsoft Learn server.
This helps understand the actual response contract before refactoring.
"""

import asyncio
import json
import pprint

from app.shared.mcp import MicrosoftLearnMCPClient


async def _test_search_docs(client):
    """Test search docs tool."""
    print("\n\n1️⃣  TESTING: microsoft_docs_search")
    print("-" * 80)
    try:
        response = await client.call_tool(
            "microsoft_docs_search", {"query": "Azure Container Apps"}
        )
        print(f"\n📦 Raw response type: {type(response)}")
        print(
            f"📦 Raw response keys: {response.keys() if isinstance(response, dict) else 'N/A'}"
        )
        print("\n📄 Full response structure:")
        pprint.pprint(response, depth=3, width=120)

        # Inspect content specifically
        content = response.get("content")
        print(f"\n🔍 Content type: {type(content)}")
        if isinstance(content, list) and len(content) > 0:
            print(f"🔍 Content length: {len(content)}")
            print(f"🔍 First item type: {type(content[0])}")
            print(f"🔍 First item: {content[0]}")

            # Try to parse as JSON if it's a string
            if isinstance(content[0], str):
                try:
                    parsed = json.loads(content[0])
                    print("\n✅ Content[0] is valid JSON!")
                    print("📊 Parsed structure:")
                    pprint.pprint(parsed, depth=2, width=120)
                except json.JSONDecodeError:
                    print("\n❌ Content[0] is NOT JSON, it's plain text")

    except (RuntimeError, ValueError) as e:
        print(f"❌ Error: {e}")


async def _test_fetch_docs(client):
    """Test fetch docs tool."""
    print("\n\n2️⃣  TESTING: microsoft_docs_fetch")
    print("-" * 80)
    try:
        response = await client.call_tool(
            "microsoft_docs_fetch",
            {"url": "https://learn.microsoft.com/azure/container-apps/overview"},
        )
        print(f"\n📦 Raw response type: {type(response)}")
        print(
            f"📦 Raw response keys: {response.keys() if isinstance(response, dict) else 'N/A'}"
        )

        content = response.get("content")
        print(f"\n🔍 Content type: {type(content)}")
        if isinstance(content, list) and len(content) > 0:
            print(f"🔍 Content length: {len(content)}")
            print(f"🔍 First item type: {type(content[0])}")

            # Show preview of content (first 500 chars)
            content_preview = str(content[0])[:500]
            print("\n📄 Content preview (first 500 chars):")
            print(content_preview)
            print("...")

            # Check if it's JSON or markdown
            if isinstance(content[0], str):
                try:
                    parsed = json.loads(content[0])
                    print("\n✅ Content is JSON structure")
                    print(
                        f"📊 JSON keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}"
                    )
                except json.JSONDecodeError:
                    print("\n✅ Content is plain text/markdown (not JSON)")

    except (RuntimeError, ValueError) as e:
        print(f"❌ Error: {e}")


async def _test_code_search(client):
    """Test code search tool."""
    print("\n\n3️⃣  TESTING: microsoft_code_sample_search")
    print("-" * 80)
    try:
        response = await client.call_tool(
            "microsoft_code_sample_search",
            {"query": "Azure Blob Storage upload", "language": "python"},
        )
        print(f"\n📦 Raw response type: {type(response)}")
        print(
            f"📦 Raw response keys: {response.keys() if isinstance(response, dict) else 'N/A'}"
        )
        print("\n📄 Full response structure:")
        pprint.pprint(response, depth=3, width=120)

        content = response.get("content")
        print(f"\n🔍 Content type: {type(content)}")
        if isinstance(content, list) and len(content) > 0:
            print(f"🔍 Content length: {len(content)}")
            print(f"🔍 First item type: {type(content[0])}")
            print(f"🔍 First item preview: {str(content[0])[:300]}...")

            # Try to parse as JSON
            if isinstance(content[0], str):
                try:
                    parsed = json.loads(content[0])
                    print("\n✅ Content[0] is valid JSON!")
                    print("📊 Parsed structure:")
                    pprint.pprint(parsed, depth=2, width=120)
                except json.JSONDecodeError:
                    print("\n❌ Content[0] is NOT JSON")

    except (RuntimeError, ValueError) as e:
        print(f"❌ Error: {e}")


async def inspect_responses():
    """Call each Microsoft Learn MCP tool and print raw responses."""

    config = {
        "endpoint": "https://learn.microsoft.com/api/mcp",
        "timeout": 30,
    }

    async with MicrosoftLearnMCPClient(config) as client:
        print("=" * 80)
        print("MICROSOFT LEARN MCP SERVER - RAW RESPONSE INSPECTION")
        print("=" * 80)

        await _test_search_docs(client)
        await _test_fetch_docs(client)
        await _test_code_search(client)

        print("\n\n" + "=" * 80)
        print("INSPECTION COMPLETE")
        print("=" * 80)

        print("\n\n" + "=" * 80)
        print("INSPECTION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(inspect_responses())


