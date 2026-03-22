import httpx
import json
import sys

CTA_URL = "http://127.0.0.1:8000"

def test_cta_register():
    sys.stdout.write("Testing CTA register with test_sync_test_001...\n")
    sys.stdout.flush()
    
    try:
        r = httpx.post(
            f"{CTA_URL}/cta/register_device",
            json={"device_id": "td_sync_test_001", "region_id": "regionA"},
            timeout=10.0
        )
        sys.stdout.write(f"Status: {r.status_code}\n")
        sys.stdout.write(f"Response: {r.text}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"Error: {e}\n")
        sys.stdout.flush()

def test_cta_revoke():
    sys.stdout.write("\nTesting CTA revoke with test_sync_test_001...\n")
    sys.stdout.flush()
    
    try:
        r = httpx.post(
            f"{CTA_URL}/cta/revoke_device",
            json={"device_id": "td_sync_test_001"},
            timeout=10.0
        )
        sys.stdout.write(f"Status: {r.status_code}\n")
        sys.stdout.write(f"Response: {r.text}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"Error: {e}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    test_cta_register()
    test_cta_revoke()
