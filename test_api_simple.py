#!/usr/bin/env python3
"""简单的 API 测试脚本"""
import asyncio
import httpx

async def main():
    print("测试 CTA API...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 测试注册设备
            response = await client.post(
                "http://127.0.0.1:8000/cta/register_device",
                json={"device_id": "test_device", "region_id": "regionA"}
            )
            print(f"注册响应状态: {response.status_code}")
            print(f"注册响应内容: {response.json()}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
