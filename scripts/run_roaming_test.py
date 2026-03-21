import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient


async def run_roaming_test():
    print("=== Running Roaming Test ===")
    
    device_id = "td001_roaming"
    storage = TDStorage()
    
    if not storage.load_device(device_id):
        print(f"Initializing device {device_id}")
        storage.save_device(device_id, f"secret_{device_id}")
    
    client = TDClient(device_id, storage)
    
    print("\n1. Enrolling with AG1 (http://127.0.0.1:8100)...")
    await client.enroll("http://127.0.0.1:8100")
    
    print("\n2. Accessing AG1...")
    result1 = await client.access("http://127.0.0.1:8100")
    print(f"   Result: {result1['result']} - {result1['reason']}")
    
    print("\n3. Roaming to AG2 (http://127.0.0.1:8200)...")
    result2 = await client.roam("http://127.0.0.1:8200")
    print(f"   Result: {result2['result']} - {result2['reason']}")
    
    print("\n=== Roaming Test Complete ===")


if __name__ == "__main__":
    asyncio.run(run_roaming_test())
