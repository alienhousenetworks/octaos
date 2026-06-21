import requests

url = "http://localhost:8000/api/v1/llm/plan-task"
payload = {
    "complexity": "high",
    "provider": None,
    "model": None
}
headers = {
    "Content-Type": "application/json",
    # Assuming we need auth, but let's see if we can bypass or we need a token
}

# we don't have a token. Let's write a python script to run the local function directly
