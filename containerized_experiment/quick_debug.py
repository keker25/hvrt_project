#!/usr/bin/env python3
"""
快速调试检查
"""
import httpx

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"

print("检查健康状态...")
for name, url in [("CTA", CTA_URL), ("EC", EC_URL), ("AG1", AG1_URL)]:
    try:
        resp = httpx.get(f"{url}/health", timeout=5)
        print(f"{name}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")

print("\n注册一个设备...")
try:
    resp = httpx.post(
        f"{CTA_URL}/register",
        json={"device_id": "quick_test_001", "region": "region_a"},
        timeout=10
    )
    print(f"Register Response: {resp.status_code}")
    if resp.status_code == 200:
        print(resp.json())
    else:
        print(resp.text)
except Exception as e:
    print(f"Register ERROR: {e}")
