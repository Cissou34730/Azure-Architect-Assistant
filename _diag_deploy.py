import asyncio
import sys

import httpx

sys.path.insert(0, "backend")
from app.core.app_settings import get_app_settings


async def main():
    s = get_app_settings()
    endpoint = s.effective_azure_openai_endpoint.rstrip("/")
    api_key = s.effective_azure_openai_api_key
    url = f"{endpoint}/openai/deployments"
    headers = {"api-key": api_key}
    params = {"api-version": "2024-10-21"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=headers)
        print("Deployments endpoint status:", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            for d in data.get("data", []):
                dep_id = d.get("id", "?")
                model = d.get("model", "?")
                status = d.get("status", "?")
                print(f"  Deployment: {dep_id}, model: {model}, status: {status}")
        else:
            print("Response:", resp.text[:500])


asyncio.run(main())
