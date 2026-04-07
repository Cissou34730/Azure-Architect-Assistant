import asyncio
import sys

import httpx

sys.path.insert(0, 'backend')

async def main():
    from backend.app.core.app_settings import get_app_settings
    s = get_app_settings()
    print('Provider:', s.effective_ai_llm_provider)
    print('Azure endpoint:', s.effective_azure_openai_endpoint)
    print('Azure deployment:', s.effective_azure_llm_deployment)
    print('Azure deployments:', s.effective_azure_llm_deployments)
    print('Azure API version:', s.ai_azure_openai_api_version)
    print('Azure API key set:', bool(s.effective_azure_openai_api_key))

    endpoint = s.effective_azure_openai_endpoint.rstrip('/')
    api_key = s.effective_azure_openai_api_key
    if endpoint and api_key:
        url = f'{endpoint}/openai/models'
        headers = {'api-key': api_key}
        params = {'api-version': '2024-10-21'}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params, headers=headers)
                print('Models endpoint status:', resp.status_code)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get('data', []):
                        caps = m.get('capabilities', {})
                        print(f'  Model: {m["id"]} - chat: {caps.get("chat_completion")}, inference: {caps.get("inference")}')
                else:
                    print('Response:', resp.text[:500])
        except Exception as e:
            print(f'Error calling models endpoint: {e}')

    deployment = s.effective_azure_llm_deployment
    if endpoint and api_key and deployment:
        url2 = f'{endpoint}/openai/deployments/{deployment}/chat/completions'
        params2 = {'api-version': s.ai_azure_openai_api_version}
        headers2 = {'api-key': api_key, 'Content-Type': 'application/json'}
        body = {'messages': [{'role': 'user', 'content': 'Reply with: ok'}], 'max_tokens': 10}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp2 = await client.post(url2, params=params2, headers=headers2, json=body)
                print(f'Chat completions ({deployment}) status:', resp2.status_code)
                if resp2.status_code == 200:
                    print('Chat response:', resp2.json()['choices'][0]['message']['content'][:100])
                else:
                    print('Chat error:', resp2.text[:500])
        except Exception as e:
            print(f'Error calling chat: {e}')

asyncio.run(main())
