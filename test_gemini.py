import asyncio
from app.services.ai_gateway.adapters import GeminiAdapter

async def main():
    api_key = "AIzaSyDtnYa2VoPqMro9mUAN868cVRqh8vKBHpg"
    adapter = GeminiAdapter(api_key=api_key)
    try:
        res = await adapter.execute_request(
            prompt="Reply with exactly 'Key works.'", 
            model="gemini-1.5-flash"
        )
        print("Success:", res['content'].strip())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
