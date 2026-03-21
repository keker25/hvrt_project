import asyncio
import httpx
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_revocation_flow():
    print("=" * 80)
    print("HVRT 撤销功能测试")
    print("=" * 80)
    
    CTA_URL = "http://127.0.0.1:8000"
    AG1_URL = "http://127.0.0.1:8100"
    device_id = "test_rev_001"
    
    print(f"\n【步骤 1: 注册设备 {device_id}")
    async with httpx.AsyncClient() as client:
        # 注册设备
        register_resp = await client.post(
            f"{CTA_URL}/cta/register_device",
            json={"device_id": device_id, "region_id": "regionA"}
        )
        print(f"注册响应: {register_resp.status_code}")
        if register_resp.status_code == 200:
            device_secret = register_resp.json()["device_secret"]
            print(f"✓ 设备注册成功，device_secret: {device_secret[:10]}...")
        else:
            print(f"✗ 设备注册失败: {register_resp.text}")
            return
    
    print(f"\n【步骤 2】 同步 EC 和 AG 从 CTA...")
    async with httpx.AsyncClient() as client:
        # 同步 EC
        ec_sync_resp = await client.post(f"{AG1_URL}/ag/state/sync")  # 实际上应该是 EC 的同步接口，这里用 AG 的同步作为演示
        print(f"AG 同步响应: {ec_sync_resp.status_code}")
        time.sleep(2)
    
    print(f"\n【步骤 3】 检查 CTA 的设备状态...")
    async with httpx.AsyncClient() as client:
        # 获取 CTA 的设备状态（通过 revocation_version 间接检查）
        gtt_resp = await client.get(f"{CTA_URL}/cta/gtt/current")
        print(f"CTA GTT: {gtt_resp.status_code}")
        if gtt_resp.status_code == 200:
            gtt_data = gtt_resp.json()["gtt"]
            print(f"CTA revocation_version: {gtt_data['revocation_version']}")
    
    print(f"\n【步骤 4】 检查 AG1 的设备状态...")
    async with httpx.AsyncClient() as client:
        state_resp = await client.get(f"{AG1_URL}/ag/state/current")
        print(f"AG1 状态响应: {state_resp.status_code}")
        if state_resp.status_code == 200:
            state_data = state_resp.json()
            print(f"AG1 revocation_version: {state_data['revocation_version']}")
            print(f"AG1 device_states: {state_data['device_states']}")
    
    print(f"\n【步骤 5】 撤销设备 {device_id}...")
    async with httpx.AsyncClient() as client:
        revoke_resp = await client.post(
            f"{CTA_URL}/cta/revoke_device",
            json={"device_id": device_id, "reason": "test revocation"}
        )
        print(f"撤销响应: {revoke_resp.status_code}")
        if revoke_resp.status_code == 200:
            revoke_data = revoke_resp.json()
            print(f"✓ 撤销成功，新版本: {revoke_data['new_version']}")
        else:
            print(f"✗ 撤销失败: {revoke_resp.text}")
            return
    
    print(f"\n【步骤 6】 再次同步 EC 和 AG...")
    async with httpx.AsyncClient() as client:
        # 再次同步
        time.sleep(2)
        ag_sync_resp = await client.post(f"{AG1_URL}/ag/state/sync")
        print(f"AG 再次同步: {ag_sync_resp.status_code}")
        time.sleep(3)
    
    print(f"\n【步骤 7】 检查 AG1 撤销后的状态...")
    async with httpx.AsyncClient() as client:
        state_resp = await client.get(f"{AG1_URL}/ag/state/current")
        print(f"AG1 状态响应: {state_resp.status_code}")
        if state_resp.status_code == 200:
            state_data = state_resp.json()
            print(f"AG1 revocation_version: {state_data['revocation_version']}")
            print(f"AG1 device_states: {state_data['device_states']}")
            if device_id in state_data['device_states']:
                if state_data['device_states'][device_id] == 'revoked':
                    print("✓ AG1 已同步到撤销状态！")
                else:
                    print(f"✗ AG1 设备状态不正确: {state_data['device_states'][device_id]}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_revocation_flow())
