#!/usr/bin/env python3
"""
TD (Terminal Device) Client - 容器化实验客户端
用于模拟终端设备发起认证请求
"""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
import random
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CryptoUtils:
    @staticmethod
    def generate_id(prefix: str) -> str:
        return f"{prefix}_{base64.b16encode(os.urandom(8)).decode().lower()}"
    
    @staticmethod
    def generate_nonce() -> str:
        return base64.b64encode(os.urandom(16)).decode()
    
    @staticmethod
    def compute_hmac(secret: str, message: str) -> str:
        hmac_obj = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(hmac_obj.digest()).decode()

class TerminalDevice:
    def __init__(self, device_id: str, cta_url: str, ag1_url: str, ag2_url: str, 
                 min_latency_ms: int = 10, max_latency_ms: int = 100, 
                 packet_loss_rate: float = 0.02):
        self.device_id = device_id
        self.cta_url = cta_url
        self.ag1_url = ag1_url
        self.ag2_url = ag2_url
        self.device_secret = None
        self.gtt = None
        self.current_ag = "ag1"
        self.logs = []
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.packet_loss_rate = packet_loss_rate
    
    def simulate_network_delay(self):
        """模拟网络延迟"""
        delay_ms = random.uniform(self.min_latency_ms, self.max_latency_ms)
        return asyncio.sleep(delay_ms / 1000)
    
    def should_simulate_packet_loss(self):
        """判断是否应该模拟丢包"""
        return random.random() < self.packet_loss_rate
    
    async def register(self):
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.cta_url}/register",
                json={"device_id": self.device_id, "region": "regionA"}
            )
            response.raise_for_status()
            data = response.json()
            self.device_secret = data["device_secret"]
            self.gtt = data["gtt"]
            return True
    
    async def authenticate(self, ag_url: str) -> Dict[str, Any]:
        start_total = time.time()
        timings = {}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Issue RRT
            await self.simulate_network_delay()
            t0 = time.time()
            rrt_resp = await client.post(
                f"{ag_url}/issue_rrt",
                json={"device_id": self.device_id, "region": "regionA"}
            )
            
            # 如果 RRT 签发失败（设备被撤销），直接返回 deny
            if rrt_resp.status_code == 403:
                timings["total_latency_ms"] = (time.time() - start_total) * 1000
                return {
                    "result": "deny",
                    "reason": "device is revoked (AG refused to issue RRT)",
                    "timings": timings
                }
            
            rrt_data = rrt_resp.json()
            rrt = rrt_data["rrt"]
            timings["ticket_issue_ms"] = rrt_data["latency_ms"]
            
            # Issue SAT
            await self.simulate_network_delay()
            sat_resp = await client.post(
                f"{ag_url}/issue_sat",
                json={"device_id": self.device_id, "rrt_id": rrt["rrt_id"]}
            )
            
            # 如果 SAT 签发失败，直接返回 deny
            if sat_resp.status_code == 403:
                timings["total_latency_ms"] = (time.time() - start_total) * 1000
                return {
                    "result": "deny",
                    "reason": "device is revoked (AG refused to issue SAT)",
                    "timings": timings
                }
            
            sat_data = sat_resp.json()
            sat = sat_data["sat"]
            
            # Generate Challenge
            await self.simulate_network_delay()
            t1 = time.time()
            chal_resp = await client.post(
                f"{ag_url}/generate_challenge",
                json={"device_id": self.device_id}
            )
            chal_data = chal_resp.json()
            challenge_id = chal_data["challenge_id"]
            nonce = chal_data["nonce"]
            timings["challenge_ms"] = chal_data["latency_ms"]
            
            # Compute Response HMAC
            response_hmac = CryptoUtils.compute_hmac(self.device_secret, f"{challenge_id}:{nonce}")
            
            # Verify Response
            await self.simulate_network_delay()
            t2 = time.time()
            verify_resp = await client.post(
                f"{ag_url}/verify_response",
                json={
                    "challenge_id": challenge_id,
                    "device_id": self.device_id,
                    "response_hmac": response_hmac,
                    "device_secret": self.device_secret,
                    "sat": sat,
                    "rrt": rrt
                }
            )
            verify_result = verify_resp.json()
            timings.update(verify_result.get("timings", {}))
            timings["total_latency_ms"] = (time.time() - start_total) * 1000
            
            return {
                "result": verify_result["result"],
                "reason": verify_result["reason"],
                "timings": timings
            }
    
    async def run_auth_round(self, round_idx: int):
        ag_url = self.ag1_url if self.current_ag == "ag1" else self.ag2_url
        result = await self.authenticate(ag_url)
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "device_id": self.device_id,
            "ag_id": self.current_ag,
            "round": round_idx,
            "result": result["result"],
            "reason": result["reason"],
            "timings": result["timings"]
        }
        self.logs.append(log_entry)
        return log_entry
    
    async def roam(self, to_ag: str):
        self.current_ag = to_ag
        ag_url = self.ag2_url if to_ag == "ag2" else self.ag1_url
        start = time.time()
        result = await self.authenticate(ag_url)
        roaming_latency = (time.time() - start) * 1000
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "device_id": self.device_id,
            "from_ag": "ag2" if to_ag == "ag2" else "ag1",
            "to_ag": to_ag,
            "roaming_latency_ms": roaming_latency,
            "result": result["result"],
            "reason": result["reason"],
            "timings": result.get("timings", {})
        }
        self.logs.append(log_entry)
        return log_entry
    
    def save_logs(self, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            for log in self.logs:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="HVRT Terminal Device Client")
    parser.add_argument("--device-id", required=True, help="Device ID")
    parser.add_argument("--cta-url", default="http://cta:8000", help="CTA URL")
    parser.add_argument("--ag1-url", default="http://ag1:8100", help="AG1 URL")
    parser.add_argument("--ag2-url", default="http://ag2:8200", help="AG2 URL")
    parser.add_argument("--num-rounds", type=int, default=10, help="Number of authentication rounds")
    parser.add_argument("--roaming-rounds", type=int, default=5, help="Number of roaming rounds")
    parser.add_argument("--log-file", help="Log file path")
    
    args = parser.parse_args()
    
    td = TerminalDevice(
        device_id=args.device_id,
        cta_url=args.cta_url,
        ag1_url=args.ag1_url,
        ag2_url=args.ag2_url
    )
    
    print(f"[{args.device_id}] Registering device...")
    await td.register()
    print(f"[{args.device_id}] Registration complete!")
    
    # Run authentication rounds
    print(f"[{args.device_id}] Starting {args.num_rounds} authentication rounds...")
    for i in range(args.num_rounds):
        await td.run_auth_round(i + 1)
        if (i + 1) % 5 == 0:
            print(f"[{args.device_id}] Completed {i + 1}/{args.num_rounds} rounds")
    
    # Run roaming rounds
    print(f"[{args.device_id}] Starting {args.roaming_rounds} roaming rounds...")
    for i in range(args.roaming_rounds):
        target_ag = "ag2" if td.current_ag == "ag1" else "ag1"
        await td.roam(target_ag)
        print(f"[{args.device_id}] Roamed to {target_ag}")
    
    if args.log_file:
        td.save_logs(args.log_file)
        print(f"[{args.device_id}] Logs saved to {args.log_file}")
    
    print(f"[{args.device_id}] Experiment complete!")

if __name__ == "__main__":
    asyncio.run(main())
