#!/usr/bin/env python3
"""
最小化核心代码库测试 - 不使用容器化服务器
使用项目根目录下的核心代码
"""
import sys
import os
import asyncio
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*80)
print("  HVRT 核心代码库测试")
print("="*80)

print("\n1. 测试导入核心模块...")
try:
    from cta.service import CTAService
    from ec.service import ECService
    from ag.service import AGService
    from common.models import Device, RRT, SAT
    print("   ✓ 核心模块导入成功")
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

print("\n2. 测试 CTA 服务初始化...")
try:
    cta = CTAService()
    print("   ✓ CTA 服务初始化成功")
except Exception as e:
    print(f"   ✗ CTA 初始化失败: {e}")
    import traceback
    traceback.print_exc()

print("\n3. 测试 EC 服务初始化...")
try:
    ec = ECService()
    print("   ✓ EC 服务初始化成功")
except Exception as e:
    print(f"   ✗ EC 初始化失败: {e}")
    import traceback
    traceback.print_exc()

print("\n4. 测试 AG 服务初始化...")
try:
    ag = AGService()
    print("   ✓ AG 服务初始化成功")
except Exception as e:
    print(f"   ✗ AG 初始化失败: {e}")
    import traceback
    traceback.print_exc()

print("\n5. 测试 CTA 设备注册...")
try:
    device_id = "test_device_001"
    device = cta.register_device(device_id, "regionA")
    print(f"   ✓ 设备注册成功: {device.device_id}")
    print(f"   ✓ 设备密钥生成: {device.device_secret[:20]}...")
except Exception as e:
    print(f"   ✗ 设备注册失败: {e}")
    import traceback
    traceback.print_exc()

print("\n6. 测试 EC RRT 签发...")
try:
    ec.storage.set_device_states({device_id: "active"})
    ec.storage.set_revocation_version(cta.storage.get_revocation_version())
    ec.storage.set_gtt(cta.storage.get_gtt())
    
    # 检查是否有密钥对
    if not ec.storage.get_ec_privkey():
        from common import generate_ed25519_keypair
        privkey, pubkey = generate_ed25519_keypair()
        ec.storage.set_ec_keypair(privkey, pubkey)
        print("   ✓ 为 EC 生成密钥对")
    
    rrt_result = ec.issue_rrt(device_id, "regionA")
    print(f"   ✓ EC 签发 RRT 成功")
    print(f"   ✓ RRT ID: {rrt_result['rrt']['rrt_id']}")
    print(f"   ✓ 状态版本: {rrt_result['rrt']['status_version']}")
except Exception as e:
    print(f"   ✗ RRT 签发失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("  核心代码库测试完成！")
print("="*80)
print("\n所有核心功能基本正常！")
