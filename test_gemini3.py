import asyncio
from app.services.ai_gateway.adapters import GeminiAdapter

async def main():
    adapter = GeminiAdapter(api_key="AIzaSyDtnYa2VoPqMro9mUAN868cVRqh8vKBHpg")
    for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
        try:
            res = await adapter.execute_request(prompt="Reply: Key works.", model=model)
            print(f"✅ {model}: {res['content'].strip()[:40]}")
        except Exception as e:
            print(f"❌ {model}: {str(e)[:80]}")

asyncio.run(main())
