import httpx
import sys

EC_URL = "http://127.0.0.1:8050"

def test_ec_sync():
    sys.stdout.write("Testing EC sync...\n")
    sys.stdout.flush()
    
    try:
        r = httpx.post(f"{EC_URL}/ec/state/sync", timeout=10.0)
        sys.stdout.write(f"Status: {r.status_code}\n")
        sys.stdout.write(f"Response: {r.text}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"Error: {e}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    test_ec_sync()
