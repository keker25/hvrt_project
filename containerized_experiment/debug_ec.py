#!/usr/bin/env python3
"""
测试 EC 的 /sync_data 接口
"""
import httpx

EC_URL = "http://localhost:8050"

print("=" * 80)
print("  测试 EC /sync_data")
print("=" * 80)

print("\n1. 检查 EC 健康状态...")
resp = httpx.get(f"{EC_URL}/health")
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text}")

print("\n2. 调用 EC /sync_data...")
resp_sync = httpx.get(f"{EC_URL}/sync_data")
print(f"   Status: {resp_sync.status_code}")
print(f"   Content: {resp_sync.content}")
print(f"   Text: {resp_sync.text}")
try:
    json_data = resp_sync.json()
    print(f"   ✅ JSON: {json_data}")
except Exception as e:
    print(f"   ❌ JSON Error: {e}")
