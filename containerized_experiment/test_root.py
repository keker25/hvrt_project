#!/usr/bin/env python3
"""测试根路径"""

import asyncio
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CTA_URL = "http://localhost:8000"


async def main():
    print("Testing root paths...")
    
    try:
        print(f"Testing {CTA_URL}/...")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(CTA_URL)
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
