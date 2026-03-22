#!/usr/bin/env python3
"""
HVRT 并发测试（Docker 容器化版本）
包含完整的同步步骤
"""

import asyncio
import httpx
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"


async def register_device(device_id: str):
    """注册单个设备"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{CTA_URL}/register",
            json={"device_id": device_id, "region": "regionA"}
        )
        response.raise_for_status()
        result = response.json()
        return {
            "device_id": device_id,
            "device_secret": result["device_secret"],
            "gtt": result["gtt"]
        }


async def single_device_test(device_info: dict):
    """单个设备的完整认证测试"""
    device_id = device_info["device_id"]
    device_secret = device_info["device_secret"]
    
    try:
        # Issue RRT
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/issue_rrt",
                json={"device_id": device_id, "region": "regionA"}
            )
            response.raise_for_status()
            rrt_data = response.json()
            rrt = rrt_data["rrt"]
        
        # Issue SAT
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/issue_sat",
                json={"device_id": device_id, "rrt_id": rrt["rrt_id"]}
            )
            response.raise_for_status()
            sat_data = response.json()
            sat = sat_data["sat"]
        
        # Generate Challenge
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AG1_URL}/generate_challenge",
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
        
        # Verify
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
        
        return verify_result
    except Exception as e:
        return {"result": "error", "reason": str(e)}


async def run_concurrency_test(num_devices: int = 5):
    print(f"=== Running Concurrency Test with {num_devices} devices (Docker version) ===")
    
    print(f"\nStep 1: Registering all {num_devices} devices with CTA...")
    register_tasks = []
    for i in range(num_devices):
        device_id = f"td_conc_docker_{i:03d}"
        task = asyncio.create_task(register_device(device_id))
        register_tasks.append(task)
    
    register_results = await asyncio.gather(*register_tasks, return_exceptions=True)
    device_infos = []
    for result in register_results:
        if not isinstance(result, Exception):
            device_infos.append(result)
    
    print(f"Registration complete! Successfully registered {len(device_infos)}/{num_devices} devices")
    
    print("\nStep 2: Syncing EC from CTA...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{EC_URL}/sync")
        response.raise_for_status()
    print("   ✓ EC sync complete")
    
    print("\nStep 3: Syncing AG from EC...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{AG1_URL}/sync")
        response.raise_for_status()
    print("   ✓ AG sync complete")
    
    start_time = datetime.now()
    
    print(f"\nStep 4: Running {len(device_infos)} concurrent authentication tests...")
    auth_tasks = []
    for device_info in device_infos:
        task = asyncio.create_task(single_device_test(device_info))
        auth_tasks.append(task)
    
    results = await asyncio.gather(*auth_tasks, return_exceptions=True)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    success_count = 0
    fail_count = 0
    error_count = 0
    
    for i, result in enumerate(results):
        device_id = device_infos[i]["device_id"] if i < len(device_infos) else f"unknown_{i}"
        if isinstance(result, Exception):
            print(f"Device {device_id}: ERROR - {result}")
            error_count += 1
        elif result.get("result") == "allow":
            print(f"Device {device_id}: SUCCESS - {result.get('reason')}")
            success_count += 1
        else:
            print(f"Device {device_id}: FAIL - {result.get('reason')}")
            fail_count += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Total devices: {len(device_infos)}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Errors: {error_count}")
    print(f"Duration: {duration:.2f} seconds")
    if duration > 0:
        print(f"Throughput: {len(device_infos) / duration:.2f} devices/second")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run concurrency test (Docker version)")
    parser.add_argument("--num-devices", type=int, default=5, help="Number of concurrent devices")
    args = parser.parse_args()
    
    asyncio.run(run_concurrency_test(args.num_devices))
