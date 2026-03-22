#!/usr/bin/env python3
"""简单的同步测试"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://127.0.0.1:8000"
EC_URL = "http://127.0.0.1:8050"


async def test_basic_sync():
    print("=== 简单同步测试 ===")
    
    device_id = "simple_test_001"
    
    try:
        # 1. 注册设备
        print(f"\n1. 注册设备 {device_id}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CTA_URL}/cta/register_device",
                json={"device_id": device_id, "region_id": "regionA"}
            )
            response.raise_for_status()
            register_result = response.json()
        print(f"   ✅ 注册成功，secret: {register_result['device_secret'][:10]}...")
        
        # 2. 检查 CTA 状态
        print("\n2. 检查 CTA 状态...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CTA_URL}/cta/revocation/delta?from_version=0")
            response.raise_for_status()
            cta_data = response.json()
        print(f"   ✅ CTA version: {cta_data.get('to_version')}")
        print(f"   ✅ CTA changes: {len(cta_data.get('changes', []))}")
        
        # 3. EC 同步
        print("\n3. EC 同步...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("   正在发送同步请求...")
            response = await client.post(f"{EC_URL}/ec/state/sync")
            print(f"   响应状态: {response.status_code}")
            response.raise_for_status()
            sync_result = response.json()
        print(f"   ✅ EC 同步完成: {sync_result}")
        
        # 4. 检查 EC 状态
        print("\n4. 检查 EC 状态...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{EC_URL}/ec/state/current")
            response.raise_for_status()
            ec_state = response.json()
        
        device_state = ec_state["device_states"].get(device_id)
        device_secret = ec_state.get("device_secrets", {}).get(device_id)
        
        print(f"   EC 设备状态: {device_state}")
        print(f"   EC 设备密钥: {'存在' if device_secret else '不存在'}")
        print(f"   EC 版本: {ec_state['revocation_version']}")
        
        if device_state != "active":
            raise Exception(f"EC 设备状态错误: {device_state}")
        if not device_secret:
            raise Exception("EC 没有设备密钥")
        
        print("\n🎉 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_basic_sync())
