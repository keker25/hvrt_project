#!/usr/bin/env python3
"""测试各端的导入是否正常"""
import sys
import os

print("=" * 60)
print("测试各模块导入")
print("=" * 60)

# 1. 测试 Common 模块
print("\n1. 测试 Common 模块...")
try:
    import common
    print("   ✓ common 导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试 CTA
print("\n2. 测试 CTA 模块...")
try:
    from cta import main
    print("   ✓ cta.main 导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 3. 测试 EC
print("\n3. 测试 EC 模块...")
try:
    from ec import main
    print("   ✓ ec.main 导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试 AG
print("\n4. 测试 AG 模块...")
try:
    from ag import main
    print("   ✓ ag.main 导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试 TD Client
print("\n5. 测试 TD Client 模块...")
try:
    from td_client import main
    print("   ✓ td_client.main 导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("导入测试完成！")
print("=" * 60)
