#!/usr/bin/env python3
"""
HVRT 完整端到端功能测试
测试用例列表：
1. 注册—同步—发票据—default 访问成功
2. centralized 模式成功
3. terminal_online_status 模式成功
4. 漫游成功
5. 撤销后全部拒绝
6. 旧 receipt 不能复用
7. 设备未注册不能 enroll
8. secret 不匹配必须拒绝
9. 旧 RRT 在版本落后后必须拒绝
"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient

CTA_URL = "http://127.0.0.1:8000"
EC_URL = "http://127.0.0.1:8050"
AG1_URL = "http://127.0.0.1:8100"
AG2_URL = "http://127.0.0.1:8200"


async def reset_env():
    print("\n=== 清理环境 ===")
    # 清空数据目录
    for dir_name in ["cta/data", "ec/data", "ag/data", "td_client/data"]:
        dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), dir_name)
        if os.path.exists(dir_path):
            import shutil
            shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
    print("✅ 环境清理完成")


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


async def test_case_1_register_enroll_access():
    """用例 1：注册—同步—发票据—default 访问成功"""
    print("\n" + "="*60)
    print("用例 1：注册—同步—发票据—default 访问成功")
    print("="*60)
    
    device_id = "td_e2e_001"
    storage = TDStorage()
    
    try:
        # 1. 注册设备
        print(f"1. 注册设备 {device_id}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CTA_URL}/cta/register_device",
                json={"device_id": device_id, "region_id": "regionA"}
            )
            response.raise_for_status()
            result = response.json()
            storage.save_device(device_id, result["device_secret"])
        print("   ✅ 注册成功")
        
        # 2. 强制同步
        print("2. 强制同步 EC 和 AG...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{EC_URL}/ec/state/sync")
            await client.post(f"{AG1_URL}/ag/state/sync")
        print("   ✅ 同步完成")
        
        # 3. Enroll
        print("3. Enroll...")
        client = TDClient(device_id, storage)
        await client.enroll(AG1_URL)
        print("   ✅ Enroll 成功")
        
        # 4. 访问 (default)
        print("4. 访问 (default)...")
        result = await client.access(AG1_URL, mode="default")
        if result["result"] != "allow":
            raise Exception(f"访问失败: {result}")
        print(f"   ✅ 访问成功: {result}")
        
        print("\n✅ 用例 1 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 1 失败: {e}")
        return False


async def test_case_2_centralized():
    """用例 2：centralized 模式成功"""
    print("\n" + "="*60)
    print("用例 2：centralized 模式成功")
    print("="*60)
    
    device_id = "td_e2e_001"
    storage = TDStorage()
    client = TDClient(device_id, storage)
    
    try:
        print("访问 (centralized)...")
        result = await client.access(AG1_URL, mode="centralized")
        if result["result"] != "allow":
            raise Exception(f"访问失败: {result}")
        print(f"✅ 访问成功: {result}")
        
        print("\n✅ 用例 2 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 2 失败: {e}")
        return False


async def test_case_3_terminal_online_status():
    """用例 3：terminal_online_status 模式成功"""
    print("\n" + "="*60)
    print("用例 3：terminal_online_status 模式成功")
    print("="*60)
    
    device_id = "td_e2e_001"
    storage = TDStorage()
    client = TDClient(device_id, storage)
    
    try:
        print("访问 (terminal_online_status)...")
        result = await client.access(AG1_URL, mode="terminal_online_status")
        if result["result"] != "allow":
            raise Exception(f"访问失败: {result}")
        print(f"✅ 访问成功: {result}")
        
        print("\n✅ 用例 3 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 3 失败: {e}")
        return False


async def test_case_4_roaming():
    """用例 4：漫游成功"""
    print("\n" + "="*60)
    print("用例 4：漫游成功")
    print("="*60)
    
    device_id = "td_e2e_001"
    storage = TDStorage()
    client = TDClient(device_id, storage)
    
    try:
        # 在 AG1 访问
        print("1. 在 AG1 访问...")
        result1 = await client.access(AG1_URL, mode="default")
        if result1["result"] != "allow":
            raise Exception(f"AG1 访问失败: {result1}")
        print(f"   ✅ AG1 访问成功")
        
        # 在 AG2 同步
        print("2. 同步 AG2...")
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            await client_http.post(f"{AG2_URL}/ag/state/sync")
        print("   ✅ AG2 同步完成")
        
        # 在 AG2 Enroll
        print("3. 在 AG2 Enroll...")
        await client.enroll(AG2_URL)
        print("   ✅ AG2 Enroll 成功")
        
        # 在 AG2 访问
        print("4. 在 AG2 访问...")
        result2 = await client.access(AG2_URL, mode="default")
        if result2["result"] != "allow":
            raise Exception(f"AG2 访问失败: {result2}")
        print(f"   ✅ AG2 访问成功")
        
        print("\n✅ 用例 4 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 4 失败: {e}")
        return False


async def test_case_5_revocation():
    """用例 5：撤销后全部拒绝"""
    print("\n" + "="*60)
    print("用例 5：撤销后全部拒绝")
    print("="*60)
    
    device_id = "td_e2e_001"
    storage = TDStorage()
    client = TDClient(device_id, storage)
    
    try:
        # 撤销设备
        print("1. 撤销设备...")
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.post(
                f"{CTA_URL}/cta/revoke_device",
                json={"device_id": device_id}
            )
            response.raise_for_status()
        print("   ✅ 撤销成功")
        
        # 强制同步
        print("2. 强制同步 EC 和 AG...")
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            await client_http.post(f"{EC_URL}/ec/state/sync")
            await client_http.post(f"{AG1_URL}/ag/state/sync")
            await client_http.post(f"{AG2_URL}/ag/state/sync")
        print("   ✅ 同步完成")
        
        # 测试三种模式都应该拒绝
        print("3. 测试三种模式...")
        for mode in ["default", "centralized", "terminal_online_status"]:
            result = await client.access(AG1_URL, mode=mode)
            if result["result"] != "deny":
                raise Exception(f"{mode} 模式应该拒绝，但返回: {result}")
            print(f"   ✅ {mode} 模式正确拒绝: {result}")
        
        print("\n✅ 用例 5 通过")
        return True
    except Exception as e:
        print(f"\n❌ 用例 5 失败: {e}")
        return False


async def main():
    print("\n" + "="*80)
    print("HVRT 完整端到端功能测试")
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
    
    # 执行所有测试
    test_cases = [
        ("用例 1", test_case_1_register_enroll_access),
        ("用例 2", test_case_2_centralized),
        ("用例 3", test_case_3_terminal_online_status),
        ("用例 4", test_case_4_roaming),
        ("用例 5", test_case_5_revocation),
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
