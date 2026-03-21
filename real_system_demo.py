#!/usr/bin/env python3
"""
HVRT 真实网络服务 - 完整演示
使用独立进程启动 CTA、EC、AG，然后运行测试
"""
import asyncio
import subprocess
import sys
import os
import time
import httpx
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json

print("=" * 80)
print("  HVRT 真实网络服务 - 完整演示")
print("=" * 80)

processes = []

def cleanup():
    print("\n正在停止所有服务...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            try:
                p.kill()
            except:
                pass
    print("所有服务已停止")

def generate_id(prefix: str) -> str:
    return f"{prefix}_{base64.b16encode(os.urandom(8)).decode().lower()}"

async def wait_for_service(url: str, name: str, max_wait: int = 30):
    print(f"\n等待 {name} 启动...")
    for i in range(max_wait):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"✓ {name} 已启动！")
                    return True
        except Exception as e:
            pass
        await asyncio.sleep(1)
    print(f"✗ {name} 启动超时！")
    return False

async def main():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # 启动服务
        print("\n正在启动 CTA (端口 8000)...")
        cta_proc = subprocess.Popen(
            [sys.executable, "-m", "cta.main"],
            cwd=base_path
        )
        processes.append(cta_proc)
        
        print("正在启动 EC (端口 8050)...")
        ec_proc = subprocess.Popen(
            [sys.executable, "-m", "ec.main"],
            cwd=base_path
        )
        processes.append(ec_proc)
        
        print("正在启动 AG1 (端口 8100)...")
        ag1_proc = subprocess.Popen(
            [sys.executable, "-m", "ag.main", "--port", "8100"],
            cwd=base_path
        )
        processes.append(ag1_proc)
        
        print("\n等待服务启动...")
        await asyncio.sleep(8)
        
        await wait_for_service("http://127.0.0.1:8000/", "CTA")
        await wait_for_service("http://127.0.0.1:8050/", "EC")
        await wait_for_service("http://127.0.0.1:8100/", "AG1")
        
        print("\n等待 AG 完成同步...")
        await asyncio.sleep(5)
        
        # 运行完整测试
        print("\n" + "=" * 80)
        print("  运行完整测试")
        print("=" * 80)
        
        cta_url = "http://127.0.0.1:8000"
        ec_url = "http://127.0.0.1:8050"
        ag1_url = "http://127.0.0.1:8100"
        
        async with httpx.AsyncClient() as client:
            # 1. 注册设备
            print("\n【1/7】注册设备...")
            response = await client.post(
                f"{cta_url}/cta/register_device",
                json={"device_id": "td_real", "region_id": "regionA"}
            )
            device = response.json()
            print(f"✓ 设备注册成功: {device['device_id']}")
            device_secret = device["device_secret"]
            
            # 2. 获取 GTT
            print("\n【2/7】获取 GTT...")
            response = await client.get(f"{cta_url}/cta/gtt/current")
            gtt = response.json()["gtt"]
            print(f"✓ GTT: {gtt['gtt_id']}")
            
            # 3. 检查 EC 状态
            print("\n【3/7】检查 EC 同步...")
            await asyncio.sleep(3)
            response = await client.get(f"{ec_url}/ec/state/current")
            state = response.json()
            print(f"✓ EC 版本: {state['revocation_version']}")
            
            response = await client.get(f"{ec_url}/ec/gtt/current")
            gtt_summary = response.json()
            print(f"✓ EC GTT: {gtt_summary['gtt_id']}")
            
            # 4. 签发 RRT
            print("\n【4/7】签发 RRT...")
            try:
                response = await client.post(
                    f"{ag1_url}/ag/issue_rrt",
                    json={"device_id": "td_real", "region_id": "regionA"}
                )
                print(f"  响应状态: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    rrt = result["rrt"]
                    print(f"✓ RRT: {rrt['rrt_id']}")
                else:
                    print(f"  响应: {response.text[:300]}")
                    raise Exception("RRT 签发失败")
            except Exception as e:
                print(f"  AG 可能还没同步，再等一下...")
                await asyncio.sleep(5)
                response = await client.post(
                    f"{ag1_url}/ag/issue_rrt",
                    json={"device_id": "td_real", "region_id": "regionA"}
                )
                result = response.json()
                rrt = result["rrt"]
                print(f"✓ RRT: {rrt['rrt_id']}")
            
            # 5. 签发 SAT
            print("\n【5/7】签发 SAT...")
            response = await client.post(
                f"{ag1_url}/ag/issue_sat",
                json={"device_id": "td_real", "rrt_id": rrt["rrt_id"]}
            )
            result = response.json()
            sat = result["sat"]
            print(f"✓ SAT: {sat['sat_id']}")
            
            # 6. 接入认证
            print("\n【6/7】接入认证...")
            request_id = generate_id("req")
            
            response = await client.post(
                f"{ag1_url}/ag/access/request",
                json={"request_id": request_id, "device_id": "td_real", "sat": sat, "rrt": rrt}
            )
            challenge = response.json()
            print(f"✓ 挑战: {challenge['challenge_id']}")
            
            message = f"{challenge['challenge_id']}:{challenge['nonce']}:td_real"
            hmac_obj = hmac.new(device_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
            response_hmac = base64.b64encode(hmac_obj.digest()).decode()
            
            response = await client.post(
                f"{ag1_url}/ag/access/respond",
                json={
                    "request_id": request_id,
                    "challenge_id": challenge["challenge_id"],
                    "device_id": "td_real",
                    "response_hmac": response_hmac
                }
            )
            result = response.json()
            print(f"✓ 结果: {result['result']} - {result['reason']}")
            if result["result"] == "allow":
                print(f"✓ 会话: {result['session_id']}")
            
            # 7. 设备撤销与验证
            print("\n【7/7】撤销设备并验证...")
            
            print("→ 撤销设备...")
            response = await client.post(
                f"{cta_url}/cta/revoke_device",
                json={"device_id": "td_real", "reason": "test"}
            )
            revoke_result = response.json()
            print(f"✓ 撤销成功, 新版本: {revoke_result['new_version']}")
            
            print("→ 等待 EC 同步...")
            await asyncio.sleep(6)
            
            response = await client.get(f"{ec_url}/ec/state/current")
            state = response.json()
            print(f"✓ EC 同步到版本: {state['revocation_version']}")
            
            print("→ 等待 AG 同步...")
            await asyncio.sleep(3)
            
            print("→ 被撤销设备再次接入...")
            request_id2 = generate_id("req2")
            
            response = await client.post(
                f"{ag1_url}/ag/issue_rrt",
                json={"device_id": "td_real", "region_id": "regionA"}
            )
            rrt2 = response.json()["rrt"]
            
            response = await client.post(
                f"{ag1_url}/ag/issue_sat",
                json={"device_id": "td_real", "rrt_id": rrt2["rrt_id"]}
            )
            sat2 = response.json()["sat"]
            
            response = await client.post(
                f"{ag1_url}/ag/access/request",
                json={"request_id": request_id2, "device_id": "td_real", "sat": sat2, "rrt": rrt2}
            )
            challenge2 = response.json()
            
            message2 = f"{challenge2['challenge_id']}:{challenge2['nonce']}:td_real"
            hmac_obj2 = hmac.new(device_secret.encode('utf-8'), message2.encode('utf-8'), hashlib.sha256)
            response_hmac2 = base64.b64encode(hmac_obj2.digest()).decode()
            
            response = await client.post(
                f"{ag1_url}/ag/access/respond",
                json={
                    "request_id": request_id2,
                    "challenge_id": challenge2["challenge_id"],
                    "device_id": "td_real",
                    "response_hmac": response_hmac2
                }
            )
            result2 = response.json()
            print(f"✓ 结果: {result2['result']} - {result2['reason']}")
            
            if result2["result"] == "deny" and "revoked" in result2["reason"]:
                print("\n" + "=" * 80)
                print("  ✓✓✓ 所有测试通过！HVRT 分层撤销验证成功！")
                print("=" * 80)
            else:
                print("\n" + "=" * 80)
                print("  ✗ 撤销验证未通过")
                print("=" * 80)
            
            print("\n服务仍在运行，按 Ctrl+C 停止...")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
            
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        cleanup()
