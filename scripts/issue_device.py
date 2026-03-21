import asyncio
import httpx
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def issue_device(device_id: str, region_id: str = "regionA"):
    print(f"Issuing device: {device_id}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/cta/register_device",
            json={
                "device_id": device_id,
                "region_id": region_id
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Device registered successfully!")
            print(f"  Device ID: {result['device_id']}")
            print(f"  Device Secret: {result['device_secret']}")
            print(f"  Status: {result['status']}")
            return result
        else:
            print(f"✗ Failed to register device: {response.text}")
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Issue a new device")
    parser.add_argument("--device-id", required=True, help="Device ID")
    parser.add_argument("--region", default="regionA", help="Region ID")
    args = parser.parse_args()
    
    asyncio.run(issue_device(args.device_id, args.region))
