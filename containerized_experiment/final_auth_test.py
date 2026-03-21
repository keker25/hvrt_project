#!/usr/bin/env python3
"""
最终测试：认证撤销的设备
"""
import httpx
import hashlib
import hmac
import base64

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"

device_id = "final_test_002"

print("="*80)
print("  最终认证测试")
print("="*80)

print("\n1. 注册设备...")
resp = httpx.post(f"{CTA_URL}/register", json={"device_id": device_id, "region": "region_a"})
data = resp.json()
device_secret = data["device_secret"]
print(f"   OK!")

print("\n2. 撤销前认证（应该 allow）...")
print("   - 签发 RRT...")
resp_rrt = httpx.post(f"{AG1_URL}/issue_rrt", json={"device_id": device_id, "region": "region_a"})
if resp_rrt.status_code != 200:
    print(f"❌ RRT Issue: {resp_rrt.status_code} - {resp_rrt.text}")
    exit(1)
rrt = resp_rrt.json()["rrt"]
print("   OK")

print("   - 签发 SAT...")
resp_sat = httpx.post(f"{AG1_URL}/issue_sat", json={"device_id": device_id, "rrt_id": rrt["rrt_id"]})
if resp_sat.status_code != 200:
    print(f"❌ SAT Issue: {resp_sat.status_code} - {resp_sat.text}")
    exit(1)
sat = resp_sat.json()["sat"]
print("   OK")

print("   - 生成挑战...")
resp_chal = httpx.post(f"{AG1_URL}/generate_challenge", json={"device_id": device_id})
chal_data = resp_chal.json()
challenge_id = chal_data["challenge_id"]
nonce = chal_data["nonce"]
print("   OK")

print("   - 验证响应...")
hmac_obj = hmac.new(device_secret.encode('utf-8'), f"{challenge_id}:{nonce}".encode('utf-8'), hashlib.sha256)
response_hmac = base64.b64encode(hmac_obj.digest()).decode()
resp_verify = httpx.post(
    f"{AG1_URL}/verify_response",
    json={
        "challenge_id": challenge_id,
        "device_id": device_id,
        "response_hmac": response_hmac,
        "device_secret": device_secret,
        "sat": sat,
        "rrt": rrt
    }
)
result_before = resp_verify.json()
print(f"   ✅ 撤销前认证结果: {result_before['result']} (reason: {result_before['reason']})")

print("\n3. 撤销设备...")
resp = httpx.post(f"{CTA_URL}/revoke", json={"device_id": device_id})
print(f"   OK!")

print("\n4. 同步 EC...")
httpx.post(f"{EC_URL}/sync")
print(f"   OK!")

print("\n5. 同步 AG1...")
httpx.post(f"{AG1_URL}/sync")
print(f"   OK!")

print("\n6. 撤销后认证（应该 deny）...")
print("   - 尝试签发 RRT...")
resp_rrt = httpx.post(f"{AG1_URL}/issue_rrt", json={"device_id": device_id, "region": "region_a"})
print(f"   RRT Issue 状态: {resp_rrt.status_code}")
if resp_rrt.status_code == 403:
    print("   ✅ 签发 RRT 被正确拒绝（403）！")
else:
    print(f"   ❌ 签发 RRT 失败或没有拒绝！响应: {resp_rrt.text}")

print("\n" + "="*80)
print("  最终测试完成！")
print("="*80)
