#!/usr/bin/env python3
"""
手动触发 EC 和 AG 的同步！
"""
import httpx
import time

print("=" * 80)
print("  手动触发 EC 和 AG 同步")
print("=" * 80)

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"
AG2_URL = "http://localhost:8200"

print("\n1. 触发 EC 从 CTA 同步...")
resp_ec_sync = httpx.post(f"{EC_URL}/sync")
print(f"   Status: {resp_ec_sync.status_code}")
print(f"   Response: {resp_ec_sync.text}")

time.sleep(2)

print("\n2. 检查 EC /sync_data...")
resp_ec_data = httpx.get(f"{EC_URL}/sync_data")
print(f"   Status: {resp_ec_data.status_code}")
print(f"   Response: {resp_ec_data.text}")

time.sleep(1)

print("\n3. 触发 AG1 从 EC 同步...")
resp_ag1_sync = httpx.post(f"{AG1_URL}/sync")
print(f"   Status: {resp_ag1_sync.status_code}")
print(f"   Response: {resp_ag1_sync.text}")

time.sleep(1)

print("\n4. 触发 AG2 从 EC 同步...")
resp_ag2_sync = httpx.post(f"{AG2_URL}/sync")
print(f"   Status: {resp_ag2_sync.status_code}")
print(f"   Response: {resp_ag2_sync.text}")

time.sleep(1)

print("\n5. 再次检查 EC /sync_data...")
resp_ec_data2 = httpx.get(f"{EC_URL}/sync_data")
print(f"   Response: {resp_ec_data2.text}")

print("\n✅ 同步完成！")
