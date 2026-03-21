#!/usr/bin/env python3
"""
最小化撤销测试脚本 - 验证撤销同步链路是否闭环
"""
import os
import sys
import time
import httpx
import json

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"
AG2_URL = "http://localhost:8200"

def print_separator(title: str):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_health():
    print_separator("步骤 0: 检查所有服务健康状态")
    
    for name, url in [("CTA", CTA_URL), ("EC", EC_URL), ("AG1", AG1_URL), ("AG2", AG2_URL)]:
        try:
            resp = httpx.get(f"{url}/health", timeout=10)
            if resp.status_code == 200:
                print(f"✅ {name} is healthy!")
            else:
                print(f"❌ {name} is NOT healthy! Status: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ {name} is NOT reachable! Error: {e}")
            return False
    return True

def register_device(device_id: str, region: str = "region_a"):
    print_separator(f"步骤 1: 注册设备 {device_id}")
    try:
        resp = httpx.post(
            f"{CTA_URL}/register",
            json={"device_id": device_id, "region": region},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Device {device_id} registered successfully!")
            print(f"   - GTT ID: {data['gtt']['gtt_id']}")
            return data["device_secret"], data["gtt"]
        else:
            print(f"❌ Registration failed! Status: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return None, None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None, None

def check_cta_status(device_id: str):
    print_separator(f"  检查 CTA 设备状态: {device_id}")
    try:
        resp = httpx.get(f"{CTA_URL}/debug/device_status/{device_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   CTA Status: {data['status']} (revoked={data['revoked']})")
            print(f"   CTA Revocation Version: {data['cta_revocation_version']}")
            return data
        else:
            print(f"❌ Failed to check CTA status! Status: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ CTA status check error: {e}")
        return None

def authenticate_device(device_id: str, device_secret: str, ag_url: str = AG1_URL):
    print_separator(f"  在 AG 认证设备: {device_id}")
    try:
        resp_rrt = httpx.post(
            f"{ag_url}/issue_rrt",
            json={"device_id": device_id, "region": "region_a"},
            timeout=30
        )
        if resp_rrt.status_code != 200:
            print(f"❌ RRT Issue failed! Status: {resp_rrt.status_code}")
            print(f"   Response: {resp_rrt.text}")
            return "deny"
        
        rrt = resp_rrt.json()["rrt"]
        
        resp_sat = httpx.post(
            f"{ag_url}/issue_sat",
            json={"device_id": device_id, "rrt_id": rrt["rrt_id"]},
            timeout=30
        )
        if resp_sat.status_code != 200:
            print(f"❌ SAT Issue failed! Status: {resp_sat.status_code}")
            print(f"   Response: {resp_sat.text}")
            return "deny"
        
        sat = resp_sat.json()["sat"]
        
        resp_chal = httpx.post(
            f"{ag_url}/generate_challenge",
            json={"device_id": device_id},
            timeout=30
        )
        if resp_chal.status_code != 200:
            print(f"❌ Challenge failed! Status: {resp_chal.status_code}")
            print(f"   Response: {resp_chal.text}")
            return "deny"
        
        chal_data = resp_chal.json()
        challenge_id = chal_data["challenge_id"]
        nonce = chal_data["nonce"]
        
        import hashlib
        import hmac
        import base64
        hmac_obj = hmac.new(device_secret.encode('utf-8'), f"{challenge_id}:{nonce}".encode('utf-8'), hashlib.sha256)
        response_hmac = base64.b64encode(hmac_obj.digest()).decode()
        
        resp_verify = httpx.post(
            f"{ag_url}/verify_response",
            json={
                "challenge_id": challenge_id,
                "device_id": device_id,
                "response_hmac": response_hmac,
                "device_secret": device_secret,
                "sat": sat,
                "rrt": rrt
            },
            timeout=30
        )
        if resp_verify.status_code == 200:
            result = resp_verify.json()
            print(f"   Authentication Result: {result['result']} (reason: {result['reason']})")
            return result["result"]
        else:
            print(f"❌ Verify failed! Status: {resp_verify.status_code}")
            print(f"   Response: {resp_verify.text}")
            return "deny"
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return "deny"

def revoke_device(device_id: str):
    print_separator(f"步骤 3: 撤销设备 {device_id}")
    try:
        resp = httpx.post(
            f"{CTA_URL}/revoke",
            json={"device_id": device_id},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Device {device_id} revoked successfully!")
            print(f"   New revocation version: {data['revocation_version']}")
            return True
        else:
            print(f"❌ Revocation failed! Status: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Revocation error: {e}")
        return False

def sync_ec():
    print_separator(f"步骤 5: 触发 EC 同步")
    try:
        resp = httpx.post(f"{EC_URL}/sync", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ EC synced! Revocation version: {data['revocation_version']}")
            return True
        else:
            print(f"❌ EC sync failed! Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ EC sync error: {e}")
        return False

def check_ec_status(device_id: str):
    print_separator(f"  检查 EC 设备状态: {device_id}")
    try:
        resp = httpx.get(f"{EC_URL}/debug/device_status/{device_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   EC Revoked: {data['revoked']}")
            print(f"   EC Revocation Version: {data['ec_revocation_version']}")
            return data
        else:
            print(f"❌ Failed to check EC status! Status: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ EC status check error: {e}")
        return None

def sync_ag(ag_url: str, ag_name: str):
    print_separator(f"步骤 6: 触发 {ag_name} 同步")
    try:
        resp = httpx.post(f"{ag_url}/sync", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ {ag_name} synced! Revocation version: {data['revocation_version']}")
            return True
        else:
            print(f"❌ {ag_name} sync failed! Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ {ag_name} sync error: {e}")
        return False

def check_ag_status(device_id: str, ag_url: str, ag_name: str):
    print_separator(f"  检查 {ag_name} 设备状态: {device_id}")
    try:
        resp = httpx.get(f"{ag_url}/debug/device_status/{device_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   {ag_name} Revoked: {data['revoked']}")
            print(f"   {ag_name} Revocation Version: {data['ag_revocation_version']}")
            return data
        else:
            print(f"❌ Failed to check {ag_name} status! Status: {resp.status_code}")
            return None
    except Exception as e:
        print(f"❌ {ag_name} status check error: {e}")
        return None

def main():
    device_id = "td_test_001"
    
    print("="*80)
    print("  最小化撤销链路测试")
    print("="*80)
    
    if not test_health():
        print("\n❌ 测试失败：部分服务不可用！")
        return
    
    print("\n\n")
    
    device_secret, gtt = register_device(device_id)
    if not device_secret:
        print("\n❌ 测试失败：设备注册失败！")
        return
    
    print("\n\n")
    print_separator("步骤 2: 撤销前正常认证")
    result_before = authenticate_device(device_id, device_secret)
    print(f"   认证结果: {result_before}")
    if result_before != "allow":
        print("\n❌ 测试失败：撤销前认证应该为 allow！")
        return
    
    print("\n\n")
    check_cta_status(device_id)
    
    print("\n\n")
    if not revoke_device(device_id):
        print("\n❌ 测试失败：设备撤销失败！")
        return
    
    print("\n\n")
    print_separator("步骤 4: 撤销后立即检查 CTA 状态")
    cta_status_after = check_cta_status(device_id)
    if not cta_status_after or not cta_status_after["revoked"]:
        print("\n❌ 测试失败：CTA 状态应该为 revoked！")
        return
    
    print("\n\n")
    if not sync_ec():
        print("\n❌ 测试失败：EC 同步失败！")
        return
    
    print("\n\n")
    ec_status = check_ec_status(device_id)
    if not ec_status or not ec_status["revoked"]:
        print("\n❌ 测试失败：EC 状态应该为 revoked！")
        return
    
    print("\n\n")
    if not sync_ag(AG1_URL, "AG1"):
        print("\n❌ 测试失败：AG1 同步失败！")
        return
    
    print("\n\n")
    ag1_status = check_ag_status(device_id, AG1_URL, "AG1")
    if not ag1_status or not ag1_status["revoked"]:
        print("\n❌ 测试失败：AG1 状态应该为 revoked！")
        return
    
    print("\n\n")
    print_separator("步骤 7: 同步后再次认证")
    result_after = authenticate_device(device_id, device_secret)
    print(f"   认证结果: {result_after}")
    
    print("\n\n")
    print_separator("测试总结")
    if result_after == "deny":
        print("✅ 测试成功！撤销链路完整闭环！")
        print(f"   - 撤销前: allow")
        print(f"   - 撤销后: deny")
    else:
        print("❌ 测试失败！撤销后仍然是 allow！")

if __name__ == "__main__":
    main()
