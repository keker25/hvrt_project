#!/usr/bin/env python3
"""
测试单个 terminal_client 能否正常运行
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_single_terminal():
    from terminal_client import TerminalDevice
    
    td = TerminalDevice(
        device_id="test_single_001",
        cta_url="http://localhost:8000",
        ag1_url="http://localhost:8100",
        ag2_url="http://localhost:8200"
    )
    
    print(f"Registering device {td.device_id}...")
    await td.register()
    print(f"✅ Registration complete! device_secret: {td.device_secret[:20]}...")
    
    print(f"\nRunning 1 authentication round...")
    result = await td.run_auth_round(1)
    print(f"✅ Auth round 1 result: {result}")
    
    print(f"\nRoaming to AG2...")
    roam_result = await td.roam("ag2")
    print(f"✅ Roaming result: {roam_result}")
    
    print(f"\nAll tests passed!")

if __name__ == "__main__":
    asyncio.run(test_single_terminal())
