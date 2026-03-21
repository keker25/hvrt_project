import asyncio
import httpx
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient


async def register_device(device_id: str, cta_url: str):
    storage = TDStorage()
    temp_storage = TDStorage()
    temp_storage.save_device(device_id, "temp_secret")
    temp_client = TDClient(device_id, temp_storage)
    register_result = await temp_client.register_with_cta(cta_url, "regionA")
    return register_result


async def single_device_test(device_id: str, ag_url: str):
    storage = TDStorage()
    client = TDClient(device_id, storage)
    await client.enroll(ag_url)
    result = await client.access(ag_url)
    return result


async def run_concurrency_test(num_devices: int = 5):
    print(f"=== Running Concurrency Test with {num_devices} devices ===")
    
    CTA_URL = "http://127.0.0.1:8000"
    ag_url = "http://127.0.0.1:8100"
    
    print(f"\nStep 1: Registering all {num_devices} devices with CTA...")
    register_tasks = []
    for i in range(num_devices):
        device_id = f"td_conc_{i:03d}"
        task = asyncio.create_task(register_device(device_id, CTA_URL))
        register_tasks.append(task)
    
    register_results = await asyncio.gather(*register_tasks, return_exceptions=True)
    print("Registration complete!")
    
    start_time = datetime.now()
    
    print(f"\nStep 2: Running {num_devices} concurrent authentication tests...")
    auth_tasks = []
    for i in range(num_devices):
        device_id = f"td_conc_{i:03d}"
        task = asyncio.create_task(single_device_test(device_id, ag_url))
        auth_tasks.append(task)
    
    results = await asyncio.gather(*auth_tasks, return_exceptions=True)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    success_count = 0
    fail_count = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Device {i}: ERROR - {result}")
            fail_count += 1
        elif result["result"] == "allow":
            print(f"Device {i}: SUCCESS - {result['reason']}")
            success_count += 1
        else:
            print(f"Device {i}: FAIL - {result['reason']}")
            fail_count += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Total devices: {num_devices}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Throughput: {num_devices / duration:.2f} devices/second")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run concurrency test")
    parser.add_argument("--num-devices", type=int, default=5, help="Number of concurrent devices")
    args = parser.parse_args()
    
    asyncio.run(run_concurrency_test(args.num_devices))
