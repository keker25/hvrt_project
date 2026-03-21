#!/usr/bin/env python3
"""
HVRT 同步一致性测试
测试用例列表：
A. 注册事件传播
B. 撤销事件传播
C. 重复 sync 不应重复写脏数据
"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://127.0.0.1:8000"
EC_URL = "http://127.0.0.1:8050"
AG1_URL = "http://127.0.0.1:8100"


async def get_cta_state(device_id: str):
    """获取 CTA 状态"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 先获取所有设备
        response = await client.get(f"{CTA_URL}/cta/devices")
        response.raise_for_status()
        devices = response.json()["devices"]
        device = next((d for d in devices if d["device_id"] == device_id), None)
        
        # 获取撤销版本
        response = await client.get(f"{CTA_URL}/cta/revocation/current")
        response.raise_for_status()
        version = response.json()["version"]
        
        return {
            "device": device,
            "version": version
        }


async def get_ec_state(device_id: str):
    """获取 EC 状态"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{EC_URL}/ec/state/current")
        response.raise_for_status()
        state = response.json()
        return {
            "device_state": state["device_states"].get(device_id),
            "device_secret": state.get("device_secrets", {}).get(device_id),
            "ec_pubkey": state.get("ec_pubkey"),
            "version": state["revocation_version"]
        }


async def get_ag_state(device_id: str, ag_url: str):
    """获取 AG 状态"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{ag_url}/ag/state/current")
        response.raise_for_status()
        state = response.json()
        return {
            "device_state": state["device_states"].get(device_id),
            "device_secret": state.get("device_secrets", {}).get(device_id),
            "ec_pubkey": state.get("ec_pubkey"),
            "version": state["revocation_version"]
        }


async def test_case_a_registration_propagation():
    """用例 A：注册事件传播"""
    print("\n" + "="*60)
    print("用例 A：注册事件传播")
    print("="*60)
    
    device_id = "td_sync_test_001"
    
    try:
        # 1. 注册设备
        print(f"1. 注册设备 {device_id}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CTA_URL}/cta/register_device",
                json={"device_id": device_id, "region_id": "regionA"}
            )
            response.raise_for_status()
            register_result = response.json()
        print(f"   ✅ 注册成功，secret: {register_result['device_secret'][:10]}...")
        
        # 2. 获取 CTA 状态
        print("2. 获取 CTA 状态...")
        cta_state = await get_cta_state(device_id)
        if not cta_state["device"]:
            raise Exception("CTA 中找不到设备")
        print(f"   ✅ CTA: status={cta_state['device']['status']}, version={cta_state['version']}")
        
        # 3. EC 同步
        print("3. EC 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{EC_URL}/ec/state/sync")
        print("   ✅ EC 同步完成")
        
        # 4. 检查 EC 状态
        print("4. 检查 EC 状态...")
        ec_state = await get_ec_state(device_id)
        if ec_state["device_state"] != "active":
            raise Exception(f"EC 设备状态错误: {ec_state['device_state']}")
        if not ec_state["device_secret"]:
            raise Exception("EC 没有设备密钥")
        print(f"   ✅ EC: status={ec_state['device_state']}, secret存在, version={ec_state['version']}")
        
        # 5. AG 同步
        print("5. AG 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{AG1_URL}/ag/state/sync")
        print("   ✅ AG 同步完成")
        
        # 6. 检查 AG 状态
        print("6. 检查 AG 状态...")
        ag_state = await get_ag_state(device_id, AG1_URL)
        if ag_state["device_state"] != "active":
            raise Exception(f"AG 设备状态错误: {ag_state['device_state']}")
        if not ag_state["device_secret"]:
            raise Exception("AG 没有设备密钥")
        if not ag_state["ec_pubkey"]:
            raise Exception("AG 没有 EC 公钥")
        print(f"   ✅ AG: status={ag_state['device_state']}, secret存在, ec_pubkey存在, version={ag_state['version']}")
        
        print("\n✅ 用例 A 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 A 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_case_b_revocation_propagation():
    """用例 B：撤销事件传播"""
    print("\n" + "="*60)
    print("用例 B：撤销事件传播")
    print("="*60)
    
    device_id = "td_sync_test_001"
    
    try:
        # 1. 撤销设备
        print(f"1. 撤销设备 {device_id}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CTA_URL}/cta/revoke_device",
                json={"device_id": device_id}
            )
            response.raise_for_status()
        print("   ✅ 撤销成功")
        
        # 2. 获取 CTA 状态
        print("2. 获取 CTA 状态...")
        cta_state = await get_cta_state(device_id)
        if not cta_state["device"]:
            raise Exception("CTA 中找不到设备")
        if cta_state["device"]["status"] != "revoked":
            raise Exception(f"CTA 状态错误: {cta_state['device']['status']}")
        print(f"   ✅ CTA: status={cta_state['device']['status']}, version={cta_state['version']}")
        
        # 3. EC 同步
        print("3. EC 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{EC_URL}/ec/state/sync")
        print("   ✅ EC 同步完成")
        
        # 4. 检查 EC 状态
        print("4. 检查 EC 状态...")
        ec_state = await get_ec_state(device_id)
        if ec_state["device_state"] != "revoked":
            raise Exception(f"EC 设备状态错误: {ec_state['device_state']}")
        print(f"   ✅ EC: status={ec_state['device_state']}, version={ec_state['version']}")
        
        # 5. AG 同步
        print("5. AG 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{AG1_URL}/ag/state/sync")
        print("   ✅ AG 同步完成")
        
        # 6. 检查 AG 状态
        print("6. 检查 AG 状态...")
        ag_state = await get_ag_state(device_id, AG1_URL)
        if ag_state["device_state"] != "revoked":
            raise Exception(f"AG 设备状态错误: {ag_state['device_state']}")
        print(f"   ✅ AG: status={ag_state['device_state']}, version={ag_state['version']}")
        
        print("\n✅ 用例 B 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 B 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_case_c_duplicate_sync():
    """用例 C：重复 sync 不应重复写脏数据"""
    print("\n" + "="*60)
    print("用例 C：重复 sync 不应重复写脏数据")
    print("="*60)
    
    device_id = "td_sync_test_001"
    
    try:
        # 1. 获取第一次同步后的状态
        print("1. 获取初始状态...")
        ec_state1 = await get_ec_state(device_id)
        ag_state1 = await get_ag_state(device_id, AG1_URL)
        print(f"   ✅ 初始状态: EC version={ec_state1['version']}, AG version={ag_state1['version']}")
        
        # 2. 连续两次 EC 同步
        print("2. 连续两次 EC 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{EC_URL}/ec/state/sync")
            await client.post(f"{EC_URL}/ec/state/sync")
        print("   ✅ EC 两次同步完成")
        
        # 3. 检查 EC 状态不变
        print("3. 检查 EC 状态不变...")
        ec_state2 = await get_ec_state(device_id)
        if ec_state2["version"] != ec_state1["version"]:
            raise Exception(f"EC 版本不应变化: {ec_state1['version']} -> {ec_state2['version']}")
        if ec_state2["device_state"] != ec_state1["device_state"]:
            raise Exception("EC 设备状态不应变化")
        print("   ✅ EC 状态不变")
        
        # 4. 连续两次 AG 同步
        print("4. 连续两次 AG 同步...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{AG1_URL}/ag/state/sync")
            await client.post(f"{AG1_URL}/ag/state/sync")
        print("   ✅ AG 两次同步完成")
        
        # 5. 检查 AG 状态不变
        print("5. 检查 AG 状态不变...")
        ag_state2 = await get_ag_state(device_id, AG1_URL)
        if ag_state2["version"] != ag_state1["version"]:
            raise Exception(f"AG 版本不应变化: {ag_state1['version']} -> {ag_state2['version']}")
        if ag_state2["device_state"] != ag_state1["device_state"]:
            raise Exception("AG 设备状态不应变化")
        print("   ✅ AG 状态不变")
        
        print("\n✅ 用例 C 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 C 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def wait_service_ready(url, service_name, max_wait=30):
    print(f"等待 {service_name} 服务就绪...")
    for i in range(max_wait):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{url}/")
                if response.status_code == 200:
                    print(f"✅ {service_name} 服务就绪")
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    print(f"❌ {service_name} 服务未就绪")
    return False


async def main():
    print("\n" + "="*80)
    print("HVRT 同步一致性测试")
    print("="*80)
    
    # 等待服务就绪
    services = [
        (CTA_URL, "CTA"),
        (EC_URL, "EC"),
        (AG1_URL, "AG1"),
    ]
    
    print("\n=== 检查服务状态 ===")
    for url, name in services:
        if not await wait_service_ready(url, name):
            print("\n❌ 测试失败：服务未就绪")
            return
    
    # 执行所有测试
    test_cases = [
        ("用例 A", test_case_a_registration_propagation),
        ("用例 B", test_case_b_revocation_propagation),
        ("用例 C", test_case_c_duplicate_sync),
    ]
    
    results = []
    for name, test_func in test_cases:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 异常: {e}")
            results.append((name, False))
    
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
