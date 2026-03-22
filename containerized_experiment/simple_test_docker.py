#!/usr/bin/env python3
"""简单的 Docker 服务测试"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://localhost:8000"
EC_URL = "http://localhost:8050"
AG1_URL = "http://localhost:8100"
AG2_URL = "http://localhost:8200"


async def test_service(url, name):
    try:
        print(f"Testing {name} at {url}...")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            print(f"  {name} status: {response.status_code}")
            print(f"  {name} response: {response.json()}")
            return response.status_code == 200
    except Exception as e:
        print(f"  {name} error: {e}")
        return False


async def main():
    print("Testing Docker services...")
    
    services = [
        (CTA_URL, "CTA"),
        (EC_URL, "EC"),
        (AG1_URL, "AG1"),
        (AG2_URL, "AG2"),
    ]
    
    results = []
    for url, name in services:
        result = await test_service(url, name)
        results.append((name, result))
    
    print("\nResults:")
    for name, result in results:
        status = "✅ OK" if result else "❌ FAIL"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
