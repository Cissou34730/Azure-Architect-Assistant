import requests
import json

try:
    response = requests.post(
        "http://localhost:8000/api/projects",
        headers={"Content-Type": "application/json"},
        json={"name": "Test Project"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.ok:
        print(f"Success! Project created: {response.json()}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")

