import httpx
import time

EC_URL = "http://127.0.0.1:8050"

print("Testing EC sync endpoint...")
print(f"Current time: {time.strftime('%H:%M:%S')}")

try:
    with httpx.Client(timeout=30.0) as client:
        print("Sending sync request...")
        start_time = time.time()
        response = client.post(f"{EC_URL}/ec/state/sync")
        end_time = time.time()
        print(f"Request took {end_time - start_time:.2f} seconds")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print(f"End time: {time.strftime('%H:%M:%S')}")
