# import asyncio
# import httpx
# import time
# import json
# from datetime import datetime
# import sys
# import os
#
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#
# from td_client.storage import TDStorage
# from td_client.client import TDClient
#
#
# async def measure_latency():
#     print("=== Collecting Performance Metrics ===")
#
#     device_id = "td_metrics"
#     storage = TDStorage()
#
#     if not storage.load_device(device_id):
#         storage.save_device(device_id, f"secret_{device_id}")
#
#     client = TDClient(device_id, storage)
#     ag_url = "http://127.0.0.1:8100"
#
#     metrics = {}
#
#     print("\n1. Measuring enrollment latency...")
#     start = time.time()
#     await client.enroll(ag_url)
#     metrics["enroll_latency_ms"] = (time.time() - start) * 1000
#     print(f"   Enrollment: {metrics['enroll_latency_ms']:.2f} ms")
#
#     print("\n2. Measuring access latency (5 iterations)...")
#     access_latencies = []
#     for i in range(5):
#         start = time.time()
#         await client.access(ag_url)
#         latency = (time.time() - start) * 1000
#         access_latencies.append(latency)
#         print(f"   Iteration {i+1}: {latency:.2f} ms")
#
#     metrics["access_latencies_ms"] = access_latencies
#     metrics["access_avg_latency_ms"] = sum(access_latencies) / len(access_latencies)
#     print(f"\n   Average access latency: {metrics['access_avg_latency_ms']:.2f} ms")
#
#     output_file = "metrics.json"
#     with open(output_file, "w") as f:
#         json.dump(metrics, f, indent=2)
#     print(f"\nMetrics saved to {output_file}")
#
#     return metrics
#
#
# if __name__ == "__main__":
#     asyncio.run(measure_latency())

import asyncio
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from td_client.storage import TDStorage
from td_client.client import TDClient


async def measure_latency(mode: str = "default", iterations: int = 20):
    print(f"=== Collecting Performance Metrics ({mode}) ===")

    device_id = f"td_metrics_{mode}"
    storage = TDStorage()

    if not storage.load_device(device_id):
        storage.save_device(device_id, f"secret_{device_id}")

    client = TDClient(device_id, storage)
    ag_url = "http://127.0.0.1:8100"

    metrics = {"mode": mode}

    start = time.time()
    await client.enroll(ag_url)
    metrics["enroll_latency_ms"] = (time.time() - start) * 1000

    access_latencies = []
    for _ in range(iterations):
        start = time.time()
        await client.access(ag_url, mode=mode)
        access_latencies.append((time.time() - start) * 1000)

    metrics["access_latencies_ms"] = access_latencies
    metrics["access_avg_latency_ms"] = sum(access_latencies) / len(access_latencies)

    output_file = f"metrics_{mode}.json"
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {output_file}")
    return metrics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect HVRT metrics")
    parser.add_argument("--mode", type=str, default="default", choices=["default", "centralized", "terminal_online_status"])
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(measure_latency(args.mode, args.iterations))
