import asyncio
import httpx

CTA_URL = "http://127.0.0.1:8000"
EC_URL = "http://127.0.0.1:8050"

async def test_register_and_sync():
    print("Testing register and sync...")
    
    # 1. 注册设备
    print("1. Registering device...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{CTA_URL}/cta/register_device",
            json={"device_id": "test_simple_001", "region_id": "regionA"}
        )
        print(f"   Register status: {response.status_code}")
        print(f"   Register response: {response.text}")
    
    # 2. EC 同步
    print("2. Syncing EC...")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{EC_URL}/ec/state/sync")
        print(f"   EC sync status: {response.status_code}")
        print(f"   EC sync response: {response.text}")
    
    # 3. 检查 EC 状态
    print("3. Checking EC state...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{EC_URL}/ec/state/current")
        print(f"   EC state status: {response.status_code}")
        state = response.json()
        print(f"   EC version: {state['revocation_version']}")
        print(f"   Device state: {state['device_states'].get('test_simple_001')}")
        print(f"   Device secret exists: {'test_simple_001' in state.get('device_secrets', {})}")

if __name__ == "__main__":
    asyncio.run(test_register_and_sync())
