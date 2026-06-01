import asyncio
import httpx

API_KEY = "AIzaSyDtnYa2VoPqMro9mUAN868cVRqh8vKBHpg"

async def try_model(model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": "Say: Key works."}]}]}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, timeout=10.0)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"✅ {model} -> {text}")
        else:
            code = r.json().get("error", {}).get("message", r.text)[:80]
            print(f"❌ {model} -> {code}")

async def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=10.0)
        if r.status_code == 200:
            models = r.json().get("models", [])
            print("\n=== Available Models ===")
            for m in models:
                print(" -", m.get("name"), "|", m.get("displayName"))
        else:
            print("Could not list models:", r.text[:200])

async def main():
    await list_models()
    print("\n=== Testing Models ===")
    for model in ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
        await try_model(model)

asyncio.run(main())
