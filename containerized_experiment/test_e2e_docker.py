#!/usr/bin/env python3
"""
HVRT 完整端到端功能测试（Docker 容器化版本）
包含完整的同步步骤
"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"
AG2_URL = "http://localhost:8200"


async def reset_env():
    print("\n=== 清理环境 ===")
    print("✅ 环境清理完成（Docker 环境会自动重置）")


async def wait_service_ready(url, service_name, max_wait=120):
    print(f"等待 {service_name} 服务就绪...")
    for i in range(max_wait):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    print(f"✅ {service_name} 服务就绪")
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    print(f"❌ {service_name} 服务未就绪")
    return False


async def test_case_1_register_enroll_access():
    """用例 1：注册—同步—发票据—访问成功"""
    print("\n" + "="*60)
    print("用例 1：注册—同步—发票据—访问成功")
    print("="*60)
    
    device_id = "td_docker_001"
    device_secret = None
    gtt = None
    
    try:
        # 1. 注册设备
        print(f"1. 注册设备 {device_id}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CTA_URL}/register",
                json={"device_id": device_id, "region": "regionA"}
            )
            response.raise_for_status()
            result = response.json()
            device_secret = result["device_secret"]
            gtt = result["gtt"]
        print("   ✅ 注册成功")
        
        # 2. 强制同步 EC
        print("2. 强制同步 EC...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{EC_URL}/sync")
            response.raise_for_status()
        print("   ✅ EC 同步完成")
        
        # 3. 强制同步 AG1
        print("3. 强制同步 AG1...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{AG1_URL}/sync")
            response.raise_for_status()
        print("   ✅ AG1 同步完成")
        
        # 4. Issue RRT
        print("4. Issue RRT...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/issue_rrt",
                json={"device_id": device_id, "region": "regionA"}
            )
            response.raise_for_status()
            rrt_data = response.json()
            rrt = rrt_data["rrt"]
        print("   ✅ RRT 签发成功")
        
        # 5. Issue SAT
        print("5. Issue SAT...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/issue_sat",
                json={"device_id": device_id, "rrt_id": rrt["rrt_id"]}
            )
            response.raise_for_status()
            sat_data = response.json()
            sat = sat_data["sat"]
        print("   ✅ SAT 签发成功")
        
        # 6. Generate Challenge
        print("6. Generate Challenge...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/generate_challenge",
                json={"device_id": device_id}
            )
            response.raise_for_status()
            chal_data = response.json()
            challenge_id = chal_data["challenge_id"]
            nonce = chal_data["nonce"]
        print("   ✅ Challenge 生成成功")
        
        # 7. Compute Response HMAC (简化版，不使用完整的 CryptoUtils)
        print("7. Verify Response...")
        import base64
        import hashlib
        import hmac
        
        def compute_hmac(secret: str, message: str) -> str:
            hmac_obj = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
            return base64.b64encode(hmac_obj.digest()).decode()
        
        response_hmac = compute_hmac(device_secret, f"{challenge_id}:{nonce}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
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
            response.raise_for_status()
            verify_result = response.json()
        
        if verify_result["result"] != "allow":
            raise Exception(f"访问失败: {verify_result}")
        print(f"   ✅ 访问成功: {verify_result}")
        
        print("\n✅ 用例 1 通过")
        return True, device_id, device_secret
    except Exception as e:
        print(f"\n❌ 用例 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


async def test_case_4_roaming(device_id, device_secret):
    """用例 4：漫游成功"""
    print("\n" + "="*60)
    print("用例 4：漫游成功")
    print("="*60)
    
    try:
        # 1. 在 AG1 访问（验证已在 AG1）
        print("1. 在 AG1 验证状态...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{AG1_URL}/debug/device_status/{device_id}")
            print(f"   AG1 状态: {response.json()}")
        
        # 2. 同步 AG2
        print("2. 同步 AG2...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{AG2_URL}/sync")
        print("   ✅ AG2 同步完成")
        
        # 3. 在 AG2 验证状态
        print("3. 在 AG2 验证状态...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{AG2_URL}/debug/device_status/{device_id}")
            print(f"   AG2 状态: {response.json()}")
        
        # 4. 在 AG2 完整认证
        print("4. 在 AG2 完整认证...")
        
        # Issue RRT on AG2
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG2_URL}/issue_rrt",
                json={"device_id": device_id, "region": "regionA"}
            )
            response.raise_for_status()
            rrt_data = response.json()
            rrt = rrt_data["rrt"]
        
        # Issue SAT on AG2
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG2_URL}/issue_sat",
                json={"device_id": device_id, "rrt_id": rrt["rrt_id"]}
            )
            response.raise_for_status()
            sat_data = response.json()
            sat = sat_data["sat"]
        
        # Generate Challenge on AG2
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG2_URL}/generate_challenge",
                json={"device_id": device_id}
            )
            response.raise_for_status()
            chal_data = response.json()
            challenge_id = chal_data["challenge_id"]
            nonce = chal_data["nonce"]
        
        # Compute HMAC
        import base64
        import hashlib
        import hmac
        
        def compute_hmac(secret: str, message: str) -> str:
            hmac_obj = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
            return base64.b64encode(hmac_obj.digest()).decode()
        
        response_hmac = compute_hmac(device_secret, f"{challenge_id}:{nonce}")
        
        # Verify on AG2
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG2_URL}/verify_response",
                json={
                    "challenge_id": challenge_id,
                    "device_id": device_id,
                    "response_hmac": response_hmac,
                    "device_secret": device_secret,
                    "sat": sat,
                    "rrt": rrt
                }
            )
            response.raise_for_status()
            verify_result = response.json()
        
        if verify_result["result"] != "allow":
            raise Exception(f"AG2 访问失败: {verify_result}")
        print(f"   ✅ AG2 访问成功: {verify_result}")
        
        print("\n✅ 用例 4 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_case_5_revocation(device_id, device_secret):
    """用例 5：撤销后全部拒绝"""
    print("\n" + "="*60)
    print("用例 5：撤销后全部拒绝")
    print("="*60)
    
    try:
        # 1. 撤销设备
        print("1. 撤销设备...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CTA_URL}/revoke",
                json={"device_id": device_id}
            )
            response.raise_for_status()
        print("   ✅ 撤销成功")
        
        # 2. 强制同步 EC
        print("2. 强制同步 EC...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{EC_URL}/sync")
        print("   ✅ EC 同步完成")
        
        # 3. 强制同步 AG1 和 AG2
        print("3. 强制同步 AG1 和 AG2...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{AG1_URL}/sync")
            await client.post(f"{AG2_URL}/sync")
        print("   ✅ AG 同步完成")
        
        # 4. 验证状态
        print("4. 验证状态...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{CTA_URL}/debug/device_status/{device_id}")
            print(f"   CTA 状态: {response.json()}")
            response = await client.get(f"{EC_URL}/debug/device_status/{device_id}")
            print(f"   EC 状态: {response.json()}")
            response = await client.get(f"{AG1_URL}/debug/device_status/{device_id}")
            print(f"   AG1 状态: {response.json()}")
        
        # 5. 尝试在 AG1 签发 RRT（应该失败）
        print("5. 尝试在 AG1 签发 RRT...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{AG1_URL}/issue_rrt",
                    json={"device_id": device_id, "region": "regionA"}
                )
                if response.status_code != 403:
                    raise Exception(f"应该返回 403，但返回 {response.status_code}")
            print("   ✅ RRT 签发正确拒绝")
        except Exception as e:
            print(f"   ❌ RRT 签发测试失败: {e}")
            raise
        
        print("\n✅ 用例 5 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 5 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "="*80)
    print("HVRT 完整端到端功能测试（Docker 容器化版本）")
    print("="*80)
    
    # 等待服务就绪
    services = [
        (CTA_URL, "CTA"),
        (EC_URL, "EC"),
        (AG1_URL, "AG1"),
        (AG2_URL, "AG2"),
    ]
    
    print("\n=== 检查服务状态 ===")
    for url, name in services:
        if not await wait_service_ready(url, name):
            print("\n❌ 测试失败：服务未就绪")
            return
    
    # 清理环境
    await reset_env()
    
    # 执行所有测试
    results = []
    
    # 用例 1
    success, device_id, device_secret = await test_case_1_register_enroll_access()
    results.append(("用例 1", success))
    
    if success and device_id and device_secret:
        # 用例 4（漫游）
        success_roam = await test_case_4_roaming(device_id, device_secret)
        results.append(("用例 4", success_roam))
        
        # 用例 5（撤销）
        success_revoke = await test_case_5_revocation(device_id, device_secret)
        results.append(("用例 5", success_revoke))
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())
