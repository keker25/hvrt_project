#!/usr/bin/env python3
"""
超级简单的撤销测试 - 手动逐步执行
"""
import httpx
import time

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"

device_id = "super_test_001"

print("="*80)
print("  超级简单撤销测试")
print("="*80)

print("\n1. 注册设备...")
resp = httpx.post(f"{CTA_URL}/register", json={"device_id": device_id, "region": "region_a"})
print(f"   Status: {resp.status_code}")
data = resp.json()
device_secret = data["device_secret"]
print(f"   OK! device_secret: {device_secret[:20]}...")

print("\n2. 检查 CTA 状态...")
resp = httpx.get(f"{CTA_URL}/debug/device_status/{device_id}")
print(f"   Status: {resp.status_code}")
print(f"   CTA: {resp.json()}")

print("\n3. 撤销设备...")
resp = httpx.post(f"{CTA_URL}/revoke", json={"device_id": device_id})
print(f"   Status: {resp.status_code}")
print(f"   Revoke Response: {resp.json()}")

print("\n4. 再次检查 CTA 状态...")
resp = httpx.get(f"{CTA_URL}/debug/device_status/{device_id}")
print(f"   CTA: {resp.json()}")

print("\n5. 触发 EC 同步...")
resp = httpx.post(f"{EC_URL}/sync")
print(f"   Status: {resp.status_code}")
print(f"   EC Sync: {resp.json()}")

print("\n6. 检查 EC 状态...")
resp = httpx.get(f"{EC_URL}/debug/device_status/{device_id}")
print(f"   EC: {resp.json()}")

print("\n7. 触发 AG1 同步...")
resp = httpx.post(f"{AG1_URL}/sync")
print(f"   Status: {resp.status_code}")
print(f"   AG1 Sync: {resp.json()}")

print("\n8. 检查 AG1 状态...")
resp = httpx.get(f"{AG1_URL}/debug/device_status/{device_id}")
print(f"   AG1: {resp.json()}")

print("\n" + "="*80)
print("  调试测试完成！")
print("="*80)
