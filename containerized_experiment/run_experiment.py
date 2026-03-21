#!/usr/bin/env python3
"""
容器化实验编排脚本
用于协调多终端实验执行
"""
import os
import sys
import json
import time
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ExperimentOrchestrator:
    def __init__(self, num_terminals: int = 10, num_rounds: int = 10, roaming_rounds: int = 5):
        self.num_terminals = num_terminals
        self.num_rounds = num_rounds
        self.roaming_rounds = roaming_rounds
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
    
    async def run_terminal(self, device_id: str):
        print(f"[{device_id}] Starting...")
        from terminal_client import TerminalDevice
        td = TerminalDevice(
            device_id=device_id,
            cta_url=self.cta_url,
            ag1_url=self.ag1_url,
            ag2_url=self.ag2_url
        )
        
        # Register
        print(f"[{device_id}] Registering...")
        await td.register()
        print(f"[{device_id}] Registered!")
        
        # Run authentication rounds
        for i in range(self.num_rounds):
            print(f"[{device_id}] Auth round {i+1}/{self.num_rounds}")
            await td.run_auth_round(i + 1)
        
        # Run roaming rounds
        for i in range(self.roaming_rounds):
            target_ag = "ag2" if td.current_ag == "ag1" else "ag1"
            print(f"[{device_id}] Roaming to {target_ag}")
            await td.roam(target_ag)
        
        # Save logs
        log_file = os.path.join(self.logs_dir, f"terminal_{device_id}.jsonl")
        td.save_logs(log_file)
        print(f"[{device_id}] Complete!")
        return td.logs
    
    async def run_experiment(self):
        print("=" * 100)
        print("  HVRT 容器化多终端实验")
        print("=" * 100)
        print(f"配置:")
        print(f"  终端数量: {self.num_terminals}")
        print(f"  认证轮次: {self.num_rounds}")
        print(f"  漫游轮次: {self.roaming_rounds}")
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
        
        print("\nStarting terminals...")
        device_ids = [f"td_{i:03d}" for i in range(self.num_terminals)]
        
        # Run all terminals in parallel
        tasks = [self.run_terminal(did) for did in device_ids]
        all_logs = await asyncio.gather(*tasks)
        
        print("\n" + "=" * 100)
        print("  实验完成！分析结果...")
        print("=" * 100)
        
        self.analyze_results(all_logs)
    
    def analyze_results(self, all_logs: List[List[Dict]]):
        auth_latencies = []
        roaming_latencies = []
        auth_results = {"allow": 0, "deny": 0}
        
        for terminal_logs in all_logs:
            for log in terminal_logs:
                if "timings" in log and "total_latency_ms" in log["timings"]:
                    auth_latencies.append(log["timings"]["total_latency_ms"])
                    auth_results[log["result"]] += 1
                if "roaming_latency_ms" in log:
                    roaming_latencies.append(log["roaming_latency_ms"])
        
        print("\n【认证统计】")
        print(f"  总认证数: {len(auth_latencies)}")
        print(f"  成功率: {auth_results['allow']/(auth_results['allow']+auth_results['deny'])*100:.1f}%")
        if auth_latencies:
            print(f"  平均时延: {statistics.mean(auth_latencies):.2f} ms")
            print(f"  P50: {statistics.median(auth_latencies):.2f} ms")
            auth_latencies.sort()
            print(f"  P95: {auth_latencies[int(len(auth_latencies)*0.95)]:.2f} ms")
            print(f"  P99: {auth_latencies[int(len(auth_latencies)*0.99)]:.2f} ms")
        
        print("\n【漫游统计】")
        print(f"  总漫游数: {len(roaming_latencies)}")
        if roaming_latencies:
            print(f"  平均漫游时延: {statistics.mean(roaming_latencies):.2f} ms")
        
        print(f"\n所有终端日志已保存到 {self.logs_dir}/ 目录")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HVRT Containerized Experiment Orchestrator")
    parser.add_argument("--num-terminals", type=int, default=10, help="Number of terminals")
    parser.add_argument("--num-rounds", type=int, default=10, help="Authentication rounds per terminal")
    parser.add_argument("--roaming-rounds", type=int, default=5, help="Roaming rounds per terminal")
    
    args = parser.parse_args()
    
    orchestrator = ExperimentOrchestrator(
        num_terminals=args.num_terminals,
        num_rounds=args.num_rounds,
        roaming_rounds=args.roaming_rounds
    )
    
    asyncio.run(orchestrator.run_experiment())
