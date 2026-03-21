import asyncio
import httpx
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def revoke_device(device_id: str, reason: str = "manual revoke"):
    print(f"Revoking device: {device_id}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/cta/revoke_device",
            json={
                "device_id": device_id,
                "reason": reason
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Device revoked successfully!")
            print(f"  Device ID: {result['device_id']}")
            print(f"  New Status: {result['status']}")
            print(f"  New Version: {result['new_version']}")
            return result
        else:
            print(f"✗ Failed to revoke device: {response.text}")
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Revoke a device")
    parser.add_argument("--device-id", required=True, help="Device ID")
    parser.add_argument("--reason", default="manual revoke", help="Reason for revocation")
    args = parser.parse_args()
    
    asyncio.run(revoke_device(args.device_id, args.reason))
