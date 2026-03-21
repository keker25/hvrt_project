#!/usr/bin/env python3
"""
HVRT 一键启动演示脚本
启动所有服务并运行完整测试
"""
import asyncio
import subprocess
import sys
import os
import time
import httpx

print("=" * 80)
print("  HVRT 一键启动演示")
print("=" * 80)

processes = []

def cleanup():
    print("\n正在停止所有服务...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            try:
                p.kill()
            except:
                pass
    print("所有服务已停止")

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

async def run_test():
    print("\n" + "=" * 80)
    print("  开始运行完整测试")
    print("=" * 80)
    
    cta_url = "http://127.0.0.1:8000"
    ec_url = "http://127.0.0.1:8050"
    ag1_url = "http://127.0.0.1:8100"
    
    print("\n等待 AG 完成初始同步...")
    await asyncio.sleep(8)
    
    # 1. 测试 CTA
    print("\n【1/6】测试 CTA 接口...")
    try:
        async with httpx.AsyncClient() as client:
            print("→ 注册设备...")
            response = await client.post(
                f"{cta_url}/cta/register_device",
                json={"device_id": "td_oneclick", "region_id": "regionA"}
            )
            print(f"  响应状态: {response.status_code}")
            print(f"  响应内容: {response.text[:200]}...")
            device = response.json()
            print(f"✓ 设备注册成功: {device['device_id']}")
            device_secret = device["device_secret"]
            
            print("→ 获取 GTT...")
            response = await client.get(f"{cta_url}/cta/gtt/current")
            gtt_data = response.json()
            print(f"  响应: {gtt_data}")
            gtt = gtt_data["gtt"]
            print(f"✓ 获取 GTT 成功: {gtt['gtt_id']}")
    except Exception as e:
        print(f"✗ CTA 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 测试 EC
    print("\n【2/6】测试 EC 接口...")
    try:
        await asyncio.sleep(3)
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ec_url}/ec/state/current")
            state = response.json()
            print(f"✓ EC 状态获取成功, 版本: {state['revocation_version']}")
            
            response = await client.get(f"{ec_url}/ec/gtt/current")
            gtt_summary = response.json()
            print(f"✓ EC GTT 摘要获取成功: {gtt_summary['gtt_id']}")
    except Exception as e:
        print(f"✗ EC 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. AG 签发 RRT
    print("\n【3/6】AG1 签发 RRT...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ag1_url}/ag/issue_rrt",
                json={"device_id": "td_oneclick", "region_id": "regionA"}
            )
            print(f"  RRT 响应: {response.text[:300]}...")
            result = response.json()
            rrt = result["rrt"]
            print(f"✓ RRT 签发成功: {rrt['rrt_id']}")
    except Exception as e:
        print(f"✗ RRT 签发失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. AG 签发 SAT
    print("\n【4/6】AG1 签发 SAT...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ag1_url}/ag/issue_sat",
                json={"device_id": "td_oneclick", "rrt_id": rrt["rrt_id"]}
            )
            print(f"  SAT 响应: {response.text[:300]}...")
            result = response.json()
            sat = result["sat"]
            print(f"✓ SAT 签发成功: {sat['sat_id']}")
    except Exception as e:
        print(f"✗ SAT 签发失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 接入认证
    print("\n【5/6】终端接入认证...")
    try:
        import hashlib
        import hmac
        import base64
        
        request_id = f"req_{os.urandom(8).hex()}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ag1_url}/ag/access/request",
                json={
                    "request_id": request_id,
                    "device_id": "td_oneclick",
                    "sat": sat,
                    "rrt": rrt
                }
            )
            print(f"  挑战响应: {response.text[:300]}...")
            challenge = response.json()
            print(f"✓ 获取挑战成功: {challenge['challenge_id']}")
            
            message = f"{challenge['challenge_id']}:{challenge['nonce']}:td_oneclick"
            hmac_obj = hmac.new(device_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
            response_hmac = base64.b64encode(hmac_obj.digest()).decode()
            
            response = await client.post(
                f"{ag1_url}/ag/access/respond",
                json={
                    "request_id": request_id,
                    "challenge_id": challenge["challenge_id"],
                    "device_id": "td_oneclick",
                    "response_hmac": response_hmac
                }
            )
            print(f"  认证响应: {response.text[:300]}...")
            result = response.json()
            print(f"✓ 认证结果: {result['result']} - {result['reason']}")
            if result["result"] == "allow":
                print(f"✓ 会话 ID: {result['session_id']}")
    except Exception as e:
        print(f"✗ 接入认证失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 设备撤销测试
    print("\n【6/6】测试设备撤销...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{cta_url}/cta/revoke_device",
                json={"device_id": "td_oneclick", "reason": "test"}
            )
            print(f"  撤销响应: {response.text[:200]}...")
            revoke_result = response.json()
            print(f"✓ 设备撤销成功, 新版本: {revoke_result['new_version']}")
            
            await asyncio.sleep(4)
            
            response = await client.get(f"{ec_url}/ec/state/current")
            state = response.json()
            print(f"✓ EC 已同步到版本: {state['revocation_version']}")
    except Exception as e:
        print(f"✗ 设备撤销测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        print("\n正在启动 CTA (端口 8000)...")
        cta_proc = subprocess.Popen(
            [sys.executable, "-m", "cta.main"],
            cwd=base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(cta_proc)
        
        print("正在启动 EC (端口 8050)...")
        ec_proc = subprocess.Popen(
            [sys.executable, "-m", "ec.main"],
            cwd=base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(ec_proc)
        
        print("正在启动 AG1 (端口 8100)...")
        ag1_proc = subprocess.Popen(
            [sys.executable, "-m", "ag.main", "--port", "8100"],
            cwd=base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(ag1_proc)
        
        print("正在启动 AG2 (端口 8200)...")
        ag2_proc = subprocess.Popen(
            [sys.executable, "-m", "ag.main", "--port", "8200"],
            cwd=base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        processes.append(ag2_proc)
        
        print("\n等待服务启动...")
        await asyncio.sleep(5)
        
        await wait_for_service("http://127.0.0.1:8000/", "CTA")
        await wait_for_service("http://127.0.0.1:8050/", "EC")
        await wait_for_service("http://127.0.0.1:8100/", "AG1")
        await wait_for_service("http://127.0.0.1:8200/", "AG2")
        
        success = await run_test()
        
        if success:
            print("\n" + "=" * 80)
            print("  ✓ 所有测试通过！HVRT 系统运行正常！")
            print("=" * 80)
            print("\n服务仍在后台运行，按 Ctrl+C 停止...")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
        else:
            print("\n" + "=" * 80)
            print("  ✗ 部分测试失败")
            print("=" * 80)
            
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
