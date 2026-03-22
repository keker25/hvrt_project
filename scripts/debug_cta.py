import httpx
import json
import sys

CTA_URL = "http://127.0.0.1:8000"

def test_cta():
    sys.stdout.write("Testing CTA...\n")
    sys.stdout.flush()
    
    try:
        r = httpx.get(f"{CTA_URL}/", timeout=5.0)
        sys.stdout.write(f"CTA Status: {r.status_code}\n")
        sys.stdout.write(f"CTA Response: {r.text}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"CTA not reachable: {e}\n")
        sys.stdout.flush()
        return
    
    try:
        r = httpx.post(
            f"{CTA_URL}/cta/register_device",
            json={"device_id": "test_debug_001", "region_id": "regionA"},
            timeout=10.0
        )
        sys.stdout.write(f"\nRegister Status: {r.status_code}\n")
        sys.stdout.write(f"Register Response: {r.text}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"Register error: {e}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    test_cta()
