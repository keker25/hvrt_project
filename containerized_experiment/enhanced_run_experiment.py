#!/usr/bin/env python3
"""
增强版容器化实验编排脚本
包含：
1. 多终端并发认证（20-50个终端）
2. 详细的阶段耗时记录
3. 网络延迟和丢包模拟
4. 撤销同步弱连接场景测试
"""
import os
import sys
import json
import time
import asyncio
import httpx
import random
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EnhancedExperimentOrchestrator:
    def __init__(self, num_terminals: int = 30, num_rounds: int = 15, roaming_rounds: int = 8,
                 min_latency_ms: int = 10, max_latency_ms: int = 100, 
                 packet_loss_rate: float = 0.03):
        self.num_terminals = num_terminals
        self.num_rounds = num_rounds
        self.roaming_rounds = roaming_rounds
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.packet_loss_rate = packet_loss_rate
        self.cta_url = "http://localhost:8000"
        self.ag1_url = "http://localhost:8100"
        self.ag2_url = "http://localhost:8200"
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        self.ensure_logs_dir()
    
    def ensure_logs_dir(self):
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    async def wait_for_service(self, url: str, service_name: str, max_wait: int = 120):
        print(f"Waiting for {service_name} to be ready...")
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        print(f"{service_name} is ready!")
                        return True
            except Exception:
                pass
            await asyncio.sleep(2)
        print(f"ERROR: {service_name} did not start within {max_wait} seconds!")
        return False
    
    def sync_services(self):
        """手动同步 EC 和 AG"""
        ec_url = "http://localhost:8050"
        print("\n【初始化】同步 EC 和 AG...")
        
        # 同步 EC
        print("  同步 EC 从 CTA...")
        resp_ec = httpx.post(f"{ec_url}/sync", timeout=30)
        print(f"  EC sync: {resp_ec.status_code}")
        
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
        
        time.sleep(1)
        print("  同步完成！")
    
    async def register_single_terminal(self, device_idx: int):
        from terminal_client import TerminalDevice
        import time
        # 使用时间戳生成唯一的设备 ID，避免 409 冲突
        timestamp = int(time.time())
        device_id = f"td_{timestamp}_{device_idx:03d}"
        td = TerminalDevice(
            device_id=device_id,
            cta_url=self.cta_url,
            ag1_url=self.ag1_url,
            ag2_url=self.ag2_url,
            min_latency_ms=self.min_latency_ms,
            max_latency_ms=self.max_latency_ms,
            packet_loss_rate=self.packet_loss_rate
        )
        await td.register()
        return td
    
    async def run_terminal(self, td: 'TerminalDevice'):
        print(f"[{td.device_id}] Running...")
        
        # Run authentication rounds
        for i in range(self.num_rounds):
            await td.run_auth_round(i + 1)
        
        # Run roaming rounds
        for i in range(self.roaming_rounds):
            target_ag = "ag2" if td.current_ag == "ag1" else "ag1"
            await td.roam(target_ag)
        
        # Save logs
        log_file = os.path.join(self.logs_dir, f"terminal_{td.device_id}.jsonl")
        td.save_logs(log_file)
        print(f"[{td.device_id}] Complete!")
        return td.logs
    
    async def revoke_device(self, device_id: str):
        print(f"Revoking device {device_id}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.cta_url}/revoke",
                json={"device_id": device_id}
            )
            response.raise_for_status()
            print(f"Device {device_id} revoked!")
            return response.json()
    
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
                resp = await client.get(f"http://localhost:8050/debug/device_status/{device_id}")
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
    
    async def run_revocation_sync_experiment(self, terminals: List):
        print("\n" + "=" * 100)
        print("  模块 5: 撤销同步实验（弱连接场景）")
        print("=" * 100)
        
        # 选择3个终端进行撤销测试
        revoke_devices = random.sample([td.device_id for td in terminals], min(3, len(terminals)))
        print(f"选择撤销的终端: {revoke_devices}")
        
        results = []
        
        # 阶段 1: 撤销前
        print("\n【阶段 1】撤销前")
        for device_id in revoke_devices:
            await self.print_device_status(device_id, "撤销前")
            td = next(t for t in terminals if t.device_id == device_id)
            result = await td.authenticate(td.ag1_url if td.current_ag == "ag1" else td.ag2_url)
            results.append({
                "stage": "stage1_pre_revocation",
                "device_id": device_id,
                "result": result["result"],
                "reason": result["reason"]
            })
            print(f"  {device_id}: {result['result']}")
        
        # 阶段 2: CTA 已撤销，EC/AG 未同步
        print("\n【阶段 2】CTA 已撤销，EC/AG 未同步")
        for device_id in revoke_devices:
            await self.revoke_device(device_id)
        
        for device_id in revoke_devices:
            await self.print_device_status(device_id, "CTA已撤销未同步")
            td = next(t for t in terminals if t.device_id == device_id)
            result = await td.authenticate(td.ag1_url if td.current_ag == "ag1" else td.ag2_url)
            results.append({
                "stage": "stage2_cta_revoked_not_synced",
                "device_id": device_id,
                "result": result["result"],
                "reason": result["reason"]
            })
            print(f"  {device_id}: {result['result']}")
        
        # 阶段 3: EC 已同步，AG 未同步
        print("\n【阶段 3】EC 已同步，AG 未同步")
        print("  手动同步 EC...")
        self.sync_services()
        
        for device_id in revoke_devices:
            await self.print_device_status(device_id, "EC已同步AG未同步")
            td = next(t for t in terminals if t.device_id == device_id)
            result = await td.authenticate(td.ag1_url if td.current_ag == "ag1" else td.ag2_url)
            results.append({
                "stage": "stage3_ec_synced_ag_not_synced",
                "device_id": device_id,
                "result": result["result"],
                "reason": result["reason"]
            })
            print(f"  {device_id}: {result['result']}")
        
        # 阶段 4: EC 与 AG 均同步
        print("\n【阶段 4】EC 与 AG 均同步")
        print("  手动同步 AG1 和 AG2...")
        self.sync_services()
        
        for device_id in revoke_devices:
            await self.print_device_status(device_id, "全部同步")
            td = next(t for t in terminals if t.device_id == device_id)
            result = await td.authenticate(td.ag1_url if td.current_ag == "ag1" else td.ag2_url)
            results.append({
                "stage": "stage4_all_synced",
                "device_id": device_id,
                "result": result["result"],
                "reason": result["reason"]
            })
            print(f"  {device_id}: {result['result']}")
        
        # 保存撤销实验结果
        revocation_log_file = os.path.join(self.logs_dir, "revocation_experiment.jsonl")
        with open(revocation_log_file, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        print(f"\n撤销实验日志已保存到 {revocation_log_file}")
        return results
    
    def analyze_results(self, all_logs: List[List[Dict]]):
        auth_latencies = []
        ticket_issue_latencies = []
        challenge_latencies = []
        ticket_verify_latencies = []
        state_check_latencies = []
        roaming_latencies = []
        auth_results = {"allow": 0, "deny": 0}
        
        for terminal_logs in all_logs:
            for log in terminal_logs:
                if "timings" in log:
                    timings = log["timings"]
                    if "total_latency_ms" in timings:
                        auth_latencies.append(timings["total_latency_ms"])
                    if "ticket_issue_ms" in timings:
                        ticket_issue_latencies.append(timings["ticket_issue_ms"])
                    if "challenge_ms" in timings:
                        challenge_latencies.append(timings["challenge_ms"])
                    if "ticket_verify_ms" in timings:
                        ticket_verify_latencies.append(timings["ticket_verify_ms"])
                    if "state_check_ms" in timings:
                        state_check_latencies.append(timings["state_check_ms"])
                    
                    if "result" in log:
                        auth_results[log["result"]] += 1
                
                if "roaming_latency_ms" in log:
                    roaming_latencies.append(log["roaming_latency_ms"])
        
        def print_latency_stats(name, latencies):
            if not latencies:
                return
            latencies.sort()
            print(f"\n【{name} 统计】")
            print(f"  样本数: {len(latencies)}")
            print(f"  均值: {statistics.mean(latencies):.2f} ms")
            print(f"  P50: {statistics.median(latencies):.2f} ms")
            print(f"  P95: {latencies[int(len(latencies)*0.95)]:.2f} ms")
            if len(latencies) > 100:
                print(f"  P99: {latencies[int(len(latencies)*0.99)]:.2f} ms")
        
        print("\n" + "=" * 100)
        print("  实验结果分析")
        print("=" * 100)
        
        print(f"\n【认证统计】")
        print(f"  总认证数: {len(auth_latencies)}")
        print(f"  成功率: {auth_results['allow']/(auth_results['allow']+auth_results['deny'])*100:.1f}%")
        
        print_latency_stats("总认证时延", auth_latencies)
        print_latency_stats("票据签发", ticket_issue_latencies)
        print_latency_stats("挑战响应", challenge_latencies)
        print_latency_stats("票据验证", ticket_verify_latencies)
        print_latency_stats("状态检查", state_check_latencies)
        print_latency_stats("漫游", roaming_latencies)
        
        print(f"\n所有终端日志已保存到 {self.logs_dir}/ 目录")
    
    async def run_experiment(self):
        print("=" * 100)
        print("  HVRT 增强版容器化多终端实验")
        print("=" * 100)
        print(f"配置:")
        print(f"  终端数量: {self.num_terminals}")
        print(f"  认证轮次: {self.num_rounds}")
        print(f"  漫游轮次: {self.roaming_rounds}")
        print(f"  网络延迟: {self.min_latency_ms}-{self.max_latency_ms} ms")
        print(f"  丢包率: {self.packet_loss_rate * 100:.0f}%")
        print()
        
        # Wait for services
        services = [
            (self.cta_url, "CTA"),
            (self.ag1_url, "AG1"),
            (self.ag2_url, "AG2")
        ]
        for url, name in services:
            ready = await self.wait_for_service(url, name)
            if not ready:
                print("Experiment failed: services not ready")
                return
        
        # 同步 EC 和 AG
        self.sync_services()
        
        print("\n【初始化】注册所有终端...")
        register_tasks = [self.register_single_terminal(i) for i in range(self.num_terminals)]
        terminals = await asyncio.gather(*register_tasks)
        print("所有终端注册完成！")
        
        print("\n【注册后同步】同步 EC 和 AG 以获取新注册的设备状态...")
        self.sync_services()
        print("同步完成！")
        
        print("\n" + "=" * 100)
        print("  模块 1-4: 多终端认证与漫游")
        print("=" * 100)
        
        print("\nStarting terminals...")
        # 分批运行终端，避免同时请求过多导致超时
        MAX_CONCURRENT = 5
        all_logs = []
        for i in range(0, len(terminals), MAX_CONCURRENT):
            batch = terminals[i:i+MAX_CONCURRENT]
            print(f"  运行批次 {i//MAX_CONCURRENT + 1}（{len(batch)} 个终端）...")
            batch_tasks = [self.run_terminal(td) for td in batch]
            batch_logs = await asyncio.gather(*batch_tasks)
            all_logs.extend(batch_logs)
        
        print("\n" + "=" * 100)
        print("  模块 1-4 完成！")
        print("=" * 100)
        
        self.analyze_results(all_logs)
        
        # 运行撤销同步实验
        await self.run_revocation_sync_experiment(terminals)
        
        print("\n" + "=" * 100)
        print("  所有实验完成！")
        print("=" * 100)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HVRT Enhanced Containerized Experiment Orchestrator")
    parser.add_argument("--num-terminals", type=int, default=30, help="Number of terminals (20-50 recommended)")
    parser.add_argument("--num-rounds", type=int, default=15, help="Authentication rounds per terminal")
    parser.add_argument("--roaming-rounds", type=int, default=8, help="Roaming rounds per terminal")
    parser.add_argument("--min-latency", type=int, default=10, help="Minimum network latency in ms")
    parser.add_argument("--max-latency", type=int, default=100, help="Maximum network latency in ms")
    parser.add_argument("--packet-loss", type=float, default=0.03, help="Packet loss rate (0.0-1.0)")
    
    args = parser.parse_args()
    
    orchestrator = EnhancedExperimentOrchestrator(
        num_terminals=args.num_terminals,
        num_rounds=args.num_rounds,
        roaming_rounds=args.roaming_rounds,
        min_latency_ms=args.min_latency,
        max_latency_ms=args.max_latency,
        packet_loss_rate=args.packet_loss
    )
    
    asyncio.run(orchestrator.run_experiment())
