#!/usr/bin/env python3
"""单独调试 CTA 服务"""
import asyncio
import httpx

async def main():
    print("测试 CTA 服务...")
    async with httpx.AsyncClient() as client:
        try:
            # 测试根路径
            print("\n1. 测试根路径...")
            response = await client.get("http://127.0.0.1:8000/")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.json()}")
            
            # 测试注册设备
            print("\n2. 测试注册设备...")
            response = await client.post(
                "http://127.0.0.1:8000/cta/register_device",
                json={"device_id": "test_debug", "region_id": "regionA"}
            )
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   解析成功: {data}")
            
            # 测试获取 GTT
            print("\n3. 测试获取 GTT...")
            response = await client.get("http://127.0.0.1:8000/cta/gtt/current")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
