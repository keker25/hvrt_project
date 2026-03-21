import asyncio
import httpx
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient


async def single_device_test(device_id: str, ag_url: str):
    storage = TDStorage()
    
    if not storage.load_device(device_id):
        storage.save_device(device_id, f"secret_{device_id}")
    
    client = TDClient(device_id, storage)
    await client.enroll(ag_url)
    result = await client.access(ag_url)
    return result


async def run_concurrency_test(num_devices: int = 5):
    print(f"=== Running Concurrency Test with {num_devices} devices ===")
    
    ag_url = "http://127.0.0.1:8100"
    
    start_time = datetime.now()
    
    tasks = []
    for i in range(num_devices):
        device_id = f"td_conc_{i:03d}"
        task = asyncio.create_task(single_device_test(device_id, ag_url))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
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
