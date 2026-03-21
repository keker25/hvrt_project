#!/usr/bin/env python3
"""
最简单的调试脚本 - 单独测试 /issue_rrt 接口
"""
import httpx

AG1_URL = "http://localhost:8100"

print("=" * 80)
print("  最简单的调试")
print("=" * 80)

print("\n1. 检查 AG1 健康状态...")
resp = httpx.get(f"{AG1_URL}/health")
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text}")

print("\n2. 尝试注册一个设备...")
CTA_URL = "http://localhost:8000"
device_id = "debug_test_001"
resp = httpx.post(
    f"{CTA_URL}/register",
    json={"device_id": device_id, "region": "region_a"}
)
print(f"   Register Status: {resp.status_code}")
if resp.status_code == 200:
    print("   ✅ 注册成功！")
else:
    print(f"   ❌ 注册失败！Response: {resp.text}")

print("\n3. 尝试调用 /issue_rrt...")
resp_rrt = httpx.post(
    f"{AG1_URL}/issue_rrt",
    json={"device_id": device_id, "region": "region_a"}
)
print(f"   Status: {resp_rrt.status_code}")
print(f"   Headers: {dict(resp_rrt.headers)}")
print(f"   Content: {repr(resp_rrt.content)}")
print(f"   Text: {repr(resp_rrt.text)}")

try:
    json_data = resp_rrt.json()
    print(f"   ✅ JSON 解析成功！")
    print(f"   JSON: {json_data}")
except Exception as e:
    print(f"   ❌ JSON 解析失败！")
    print(f"   Error: {type(e).__name__}: {e}")
