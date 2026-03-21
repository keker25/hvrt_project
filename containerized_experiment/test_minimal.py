#!/usr/bin/env python3
"""
最小化的测试脚本，验证完整流程
"""
import asyncio
import httpx
import time
from terminal_client import TerminalDevice

CTA_URL = "http://localhost:8000"
AG1_URL = "http://localhost:8100"
AG2_URL = "http://localhost:8200"

print("=" * 80)
print("  最小化完整流程测试")
print("=" * 80)

print("\n1. 同步 EC 和 AG...")
print("   同步 EC...")
resp_ec = httpx.post("http://localhost:8050/sync", timeout=30)
print(f"   EC sync: {resp_ec.status_code}")

print("   同步 AG1...")
resp_ag1 = httpx.post(f"{AG1_URL}/sync", timeout=30)
print(f"   AG1 sync: {resp_ag1.status_code}")

print("   同步 AG2...")
resp_ag2 = httpx.post(f"{AG2_URL}/sync", timeout=30)
print(f"   AG2 sync: {resp_ag2.status_code}")

time.sleep(2)

print("\n2. 注册 1 个终端...")
timestamp = int(time.time())
device_id = f"test_min_{timestamp}"

td = TerminalDevice(
    device_id=device_id,
    cta_url=CTA_URL,
    ag1_url=AG1_URL,
    ag2_url=AG2_URL
)

print(f"   设备 ID: {device_id}")
print("   注册中...")
try:
    asyncio.run(td.register())
    print("   ✅ 注册成功！")
except Exception as e:
    print(f"   ❌ 注册失败: {e}")
    exit(1)

print("\n3. 认证 1 次...")
try:
    result = asyncio.run(td.authenticate(AG1_URL))
    print(f"   ✅ 认证结果: {result}")
except Exception as e:
    print(f"   ❌ 认证失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ 最小化完整流程测试通过！")
