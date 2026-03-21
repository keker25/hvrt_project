#!/usr/bin/env python3
"""
快速测试容器化服务是否正常
"""
import httpx

def test_service(url, name):
    try:
        response = httpx.get(f"{url}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ {name} is healthy at {url}!")
            return True
        else:
            print(f"❌ {name} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        return False

def test_register_device(cta_url):
    try:
        response = httpx.post(
            f"{cta_url}/register",
            json={"device_id": "test_001", "region": "regionA"},
            timeout=10.0
        )
        if response.status_code == 200:
            print(f"✅ CTA register endpoint works!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ CTA register failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ CTA register exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing containerized HVRT services...")
    print("=" * 60)
    
    services = [
        ("http://localhost:8000", "CTA"),
        ("http://localhost:8050", "EC"),
        ("http://localhost:8100", "AG1"),
        ("http://localhost:8200", "AG2"),
    ]
    
    all_ok = True
    for url, name in services:
        if not test_service(url, name):
            all_ok = False
    
    if all_ok:
        print("=" * 60)
        print("All services are healthy! Now testing CTA register...")
        test_register_device("http://localhost:8000")
