#!/usr/bin/env python3
"""
撤销逻辑专用测试脚本
只测试撤销逻辑，不做多余的认证和漫游
"""
import asyncio
import httpx
import random
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terminal_client import TerminalDevice

class RevocationTester:
    def __init__(self):
        self.cta_url = "http://localhost:8000"
        self.ec_url = "http://localhost:8050"
        self.ag1_url = "http://localhost:8100"
        self.ag2_url = "http://localhost:8200"
        self.terminals = []
    
    async def wait_for_service(self, url, name):
        """等待服务就绪"""
        print(f"Waiting for {name} to be ready...")
        for _ in range(30):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{url}/health")
                    if resp.status_code == 200:
                        print(f"{name} is ready!")
                        return True
            except Exception:
                pass
            await asyncio.sleep(1)
        print(f"{name} not ready after 30 seconds")
        return False
    
    def sync_services(self):
        """同步 EC 和 AG"""
        print("\n【同步】同步 EC 和 AG...")
        
        # 同步 EC
        print("  同步 EC 从 CTA...")
        resp_ec = httpx.post(f"{self.ec_url}/sync", timeout=30)
        print(f"  EC sync: {resp_ec.status_code}")
        
        import time
        time.sleep(0.5)
        
        # 同步 AG1
        print("  同步 AG1 从 EC...")
        resp_ag1 = httpx.post(f"{self.ag1_url}/sync", timeout=30)
        print(f"  AG1 sync: {resp_ag1.status_code}")
        
        time.sleep(0.5)
        
        # 同步 AG2
        print("  同步 AG2 从 EC...")
        resp_ag2 = httpx.post(f"{self.ag2_url}/sync", timeout=30)
        print(f"  AG2 sync: {resp_ag2.status_code}")
        
        print("  同步完成！")
    
    async def print_device_status(self, device_id: str, stage: str):
        """打印 CTA/EC/AG 的设备状态"""
        print(f"\n  [状态检查] 阶段: {stage}, 设备: {device_id}")
        
        # 查询 CTA 状态
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.cta_url}/debug/device_status/{device_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"    [CTA] revoked={data.get('revoked')}, version={data.get('cta_revocation_version')}, status={data.get('status')}")
        except Exception as e:
            print(f"    [CTA] 查询失败: {e}")
        
        # 查询 EC 状态
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.ec_url}/debug/device_status/{device_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"    [EC] revoked={data.get('revoked')}, version={data.get('ec_revocation_version')}, status={data.get('status')}")
        except Exception as e:
            print(f"    [EC] 查询失败: {e}")
        
        # 查询 AG1 状态
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.ag1_url}/debug/device_status/{device_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"    [AG1] revoked={data.get('revoked')}, version={data.get('ag_revocation_version')}, status={data.get('status')}")
        except Exception as e:
            print(f"    [AG1] 查询失败: {e}")
        
        # 查询 AG2 状态
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.ag2_url}/debug/device_status/{device_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"    [AG2] revoked={data.get('revoked')}, version={data.get('ag_revocation_version')}, status={data.get('status')}")
        except Exception as e:
            print(f"    [AG2] 查询失败: {e}")
    
    async def revoke_device(self, device_id: str):
        """撤销设备"""
        print(f"\nRevoking device {device_id}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.cta_url}/revoke",
                json={"device_id": device_id}
            )
            response.raise_for_status()
            print(f"Device {device_id} revoked!")
            return response.json()
    
    async def run_test(self):
        print("=" * 100)
        print("  撤销逻辑专用测试")
        print("=" * 100)
        
        # 等待服务就绪
        services = [
            (self.cta_url, "CTA"),
            (self.ag1_url, "AG1"),
            (self.ag2_url, "AG2")
        ]
        for url, name in services:
            ready = await self.wait_for_service(url, name)
            if not ready:
                print("Test failed: services not ready")
                return
        
        # 初始同步
        self.sync_services()
        
        # 注册 1 个终端
        print("\n【初始化】注册 1 个终端...")
        device_id = f"test_revoke_{int(datetime.now().timestamp())}"
        print(f"  设备 ID: {device_id}")
        
        td = TerminalDevice(device_id, self.cta_url, self.ag1_url, self.ag2_url)
        print("  注册中...")
        await td.register()
        print("  ✅ 注册成功！")
        
        # 注册后同步
        print("\n【注册后同步】再次同步 EC 和 AG...")
        self.sync_services()
        
        # 阶段 1: 撤销前
        print("\n【阶段 1】撤销前")
        await self.print_device_status(device_id, "撤销前")
        result = await td.authenticate(self.ag1_url)
        print(f"  认证结果: {result['result']} (期望: allow)")
        
        # 阶段 2: 撤销后
        print("\n【阶段 2】撤销设备")
        await self.revoke_device(device_id)
        
        print("\n【阶段 3】CTA 已撤销，未同步")
        await self.print_device_status(device_id, "CTA已撤销未同步")
        result = await td.authenticate(self.ag1_url)
        print(f"  认证结果: {result['result']} (期望: allow, 因为还没同步)")
        
        # 阶段 4: 同步后
        print("\n【阶段 4】同步所有服务")
        self.sync_services()
        
        await self.print_device_status(device_id, "全部同步后")
        result = await td.authenticate(self.ag1_url)
        print(f"  认证结果: {result['result']} (期望: deny)")
        
        print("\n" + "=" * 100)
        if result['result'] == 'deny':
            print("  ✅ 撤销逻辑测试通过！阶段 4 正确拒绝了已撤销设备！")
        else:
            print("  ❌ 撤销逻辑测试失败！阶段 4 没有拒绝已撤销设备！")
        print("=" * 100)

if __name__ == "__main__":
    tester = RevocationTester()
    asyncio.run(tester.run_test())
