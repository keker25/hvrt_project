#!/usr/bin/env python3
"""
测试 CTA 的 /sync 接口
"""
import httpx

CTA_URL = "http://localhost:8000"

print("=" * 80)
print("  测试 CTA /sync")
print("=" * 80)

print("\n1. 检查 CTA 健康状态...")
resp = httpx.get(f"{CTA_URL}/health")
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text}")

print("\n2. 调用 CTA /sync...")
resp_sync = httpx.get(f"{CTA_URL}/sync")
print(f"   Status: {resp_sync.status_code}")
print(f"   Content: {resp_sync.content}")
print(f"   Text: {resp_sync.text}")
try:
    json_data = resp_sync.json()
    print(f"   ✅ JSON: {json_data}")
except Exception as e:
    print(f"   ❌ JSON Error: {e}")
