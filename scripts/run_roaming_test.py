import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient


async def run_roaming_test():
    print("=== Running Roaming Test (with Real Registration) ===")
    
    CTA_URL = "http://127.0.0.1:8000"
    device_id = "td001_roaming"
    storage = TDStorage()
    
    if not storage.load_device(device_id):
        print(f"\n1. Registering device {device_id} with CTA...")
        temp_storage = TDStorage()
        temp_storage.save_device(device_id, "temp_secret")
        temp_client = TDClient(device_id, temp_storage)
        register_result = await temp_client.register_with_cta(CTA_URL, "regionA")
        print(f"   ✓ Device registered with real secret: {register_result['device_secret'][:10]}...")
    
    client = TDClient(device_id, storage)
    
    print("\n2. Enrolling with AG1 (http://127.0.0.1:8100)...")
    await client.enroll("http://127.0.0.1:8100")
    
    print("\n3. Accessing AG1...")
    result1 = await client.access("http://127.0.0.1:8100")
    print(f"   Result: {result1['result']} - {result1['reason']}")
    
    print("\n4. Roaming to AG2 (http://127.0.0.1:8200)...")
    result2 = await client.roam("http://127.0.0.1:8200")
    print(f"   Result: {result2['result']} - {result2['reason']}")
    
    print("\n=== Roaming Test Complete ===")


if __name__ == "__main__":
    asyncio.run(run_roaming_test())
