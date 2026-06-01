import requests

API_URL = "http://127.0.0.1:8000/api/v1"

# Signup
signup_data = {"email": "testuser99@test.com", "password": "testpassword", "company_name": "Test Co"}
res = requests.post(f"{API_URL}/auth/signup", json=signup_data)
if res.status_code != 200:
    # Try login
    res = requests.post(f"{API_URL}/auth/login", data={"username": "testuser99@test.com", "password": "testpassword"})

if res.status_code != 200:
    print("Could not get token:", res.text)
    exit(1)

token = res.json().get("access_token")
headers = {"Authorization": f"Bearer {token}", "Origin": "http://localhost:3000"}

endpoints = [
    "/commands/queue",
    "/commands/timeline",
    "/commands/knowledge",
    "/dashboard/metrics",
    "/dashboard/teams",
    "/dashboard/marketplace/installed",
    "/commands/keys"
]

for ep in endpoints:
    url = f"{API_URL}{ep}"
    r = requests.get(url, headers=headers)
    print(f"Endpoint: {ep} -> Status: {r.status_code}")
    if r.status_code == 500:
        print("  Error:", r.text)

