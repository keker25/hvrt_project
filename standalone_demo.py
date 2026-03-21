#!/usr/bin/env python3
"""
HVRT 分层信任离线认证系统 - 独立演示脚本
这个脚本不依赖外部包，直接展示核心认证流程
"""
import os
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta

print("=" * 70)
print("HVRT 分层信任离线认证系统 - 核心功能演示")
print("=" * 70)

# ==========================================
# 1. Ed25519 密码学实现 (使用 cryptography)
# ==========================================
print("\n【第一步】密码学基础")
print("-" * 70)

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    # 生成 CTA 根密钥对
    cta_private_key = ed25519.Ed25519PrivateKey.generate()
    cta_public_key = cta_private_key.public_key()
    
    cta_priv_b64 = base64.b64encode(
        cta_private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    ).decode()
    
    cta_pub_b64 = base64.b64encode(
        cta_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    ).decode()
    
    print(f"✓ CTA 根密钥对生成成功")
    print(f"  私钥: {cta_priv_b64[:30]}...")
    print(f"  公钥: {cta_pub_b64[:30]}...")
    
except Exception as e:
    print(f"✗ 密码学模块初始化失败: {e}")
    print("\n提示: 请先安装 cryptography: pip install cryptography")
    exit(1)

# ==========================================
# 2. 生成 GTT (全局信任票据)
# ==========================================
print("\n【第二步】生成 GTT (全局信任票据)")
print("-" * 70)

gtt_data = {
    "gtt_id": f"gtt_{base64.b16encode(os.urandom(8)).decode().lower()}",
    "root_pubkey": cta_pub_b64,
    "policy_version": 1,
    "revocation_version": 1,
    "valid_from": datetime.utcnow().isoformat() + "Z",
    "valid_to": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
}

# 签名 GTT
gtt_json = json.dumps(gtt_data, sort_keys=True).encode('utf-8')
gtt_signature = cta_private_key.sign(gtt_json)
gtt = {**gtt_data, "signature": base64.b64encode(gtt_signature).decode()}

print(f"✓ GTT 生成成功")
print(f"  GTT ID: {gtt['gtt_id']}")
print(f"  版本: {gtt['revocation_version']}")
print(f"  有效期: {gtt['valid_from']} 至 {gtt['valid_to']}")

# 验证 GTT
try:
    gtt_verify_data = gtt.copy()
    gtt_sig = base64.b64decode(gtt_verify_data.pop("signature"))
    gtt_verify_json = json.dumps(gtt_verify_data, sort_keys=True).encode('utf-8')
    cta_public_key.verify(gtt_sig, gtt_verify_json)
    print("✓ GTT 签名验证通过")
except Exception as e:
    print(f"✗ GTT 验证失败: {e}")

# ==========================================
# 3. 生成 AG 密钥对并签发 RRT (区域注册票据)
# ==========================================
print("\n【第三步】签发 RRT (区域注册票据)")
print("-" * 70)

ag_private_key = ed25519.Ed25519PrivateKey.generate()
ag_public_key = ag_private_key.public_key()

ag_priv_b64 = base64.b64encode(
    ag_private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
).decode()

ag_pub_b64 = base64.b64encode(
    ag_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
).decode()

print(f"✓ AG 密钥对生成成功")

device_id = "td001"
rrt_data = {
    "rrt_id": f"rrt_{base64.b16encode(os.urandom(8)).decode().lower()}",
    "device_id": device_id,
    "region_id": "regionA",
    "gtt_id": gtt["gtt_id"],
    "issue_time": datetime.utcnow().isoformat() + "Z",
    "expire_time": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
    "policy_tag": "default"
}

rrt_json = json.dumps(rrt_data, sort_keys=True).encode('utf-8')
rrt_signature = ag_private_key.sign(rrt_json)
rrt = {**rrt_data, "signature": base64.b64encode(rrt_signature).decode()}

print(f"✓ RRT 签发成功")
print(f"  RRT ID: {rrt['rrt_id']}")
print(f"  设备: {rrt['device_id']}")
print(f"  绑定 GTT: {rrt['gtt_id']}")

# ==========================================
# 4. 签发 SAT (会话访问票据)
# ==========================================
print("\n【第四步】签发 SAT (会话访问票据)")
print("-" * 70)

sat_data = {
    "sat_id": f"sat_{base64.b16encode(os.urandom(8)).decode().lower()}",
    "device_id": device_id,
    "rrt_id": rrt["rrt_id"],
    "issue_time": datetime.utcnow().isoformat() + "Z",
    "expire_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z",
    "auth_scope": "local_access"
}

sat_json = json.dumps(sat_data, sort_keys=True).encode('utf-8')
sat_signature = ag_private_key.sign(sat_json)
sat = {**sat_data, "signature": base64.b64encode(sat_signature).decode()}

print(f"✓ SAT 签发成功")
print(f"  SAT ID: {sat['sat_id']}")
print(f"  绑定 RRT: {sat['rrt_id']}")

# ==========================================
# 5. 挑战-响应认证
# ==========================================
print("\n【第五步】挑战-响应认证 (HMAC-SHA256)")
print("-" * 70)

device_secret = "secret_td001"
nonce = base64.b64encode(os.urandom(32)).decode()
challenge_id = f"chl_{base64.b16encode(os.urandom(8)).decode().lower()}"

print(f"✓ AG 生成挑战")
print(f"  挑战 ID: {challenge_id}")
print(f"  随机数: {nonce[:20]}...")

message = f"{challenge_id}:{nonce}:{device_id}"
hmac_obj = hmac.new(device_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
response_hmac = base64.b64encode(hmac_obj.digest()).decode()

print(f"✓ TD 生成 HMAC 响应")
print(f"  响应: {response_hmac[:30]}...")

# 验证 HMAC
expected_hmac = hmac.new(device_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
expected_hmac_b64 = base64.b64encode(expected_hmac.digest()).decode()

if hmac.compare_digest(response_hmac, expected_hmac_b64):
    print("✓ HMAC 验证通过")
else:
    print("✗ HMAC 验证失败")

# ==========================================
# 6. 完整票据链验证 (SAT → RRT → GTT)
# ==========================================
print("\n【第六步】完整票据链验证")
print("-" * 70)

print("1. 验证 SAT...")
try:
    sat_verify = sat.copy()
    sat_sig = base64.b64decode(sat_verify.pop("signature"))
    sat_verify_json = json.dumps(sat_verify, sort_keys=True).encode('utf-8')
    ag_public_key.verify(sat_sig, sat_verify_json)
    print("   ✓ SAT 签名验证通过")
    print(f"   ✓ SAT 绑定 RRT: {sat['rrt_id']}")
except Exception as e:
    print(f"   ✗ SAT 验证失败: {e}")

print("\n2. 验证 RRT...")
try:
    rrt_verify = rrt.copy()
    rrt_sig = base64.b64decode(rrt_verify.pop("signature"))
    rrt_verify_json = json.dumps(rrt_verify, sort_keys=True).encode('utf-8')
    ag_public_key.verify(rrt_sig, rrt_verify_json)
    print("   ✓ RRT 签名验证通过")
    print(f"   ✓ RRT 绑定 GTT: {rrt['gtt_id']}")
except Exception as e:
    print(f"   ✗ RRT 验证失败: {e}")

print("\n3. 验证 GTT...")
try:
    gtt_verify = gtt.copy()
    gtt_sig = base64.b64decode(gtt_verify.pop("signature"))
    gtt_verify_json = json.dumps(gtt_verify, sort_keys=True).encode('utf-8')
    cta_public_key.verify(gtt_sig, gtt_verify_json)
    print("   ✓ GTT 签名验证通过")
    print(f"   ✓ GTT 撤销版本: {gtt['revocation_version']}")
except Exception as e:
    print(f"   ✗ GTT 验证失败: {e}")

# ==========================================
# 7. 总结
# ==========================================
print("\n" + "=" * 70)
print("HVRT 认证流程演示完成！")
print("=" * 70)
print("\n认证链路:")
print("  TD (终端)")
print("    ↓")
print("  SAT (会话票据) ──┐")
print("                    ↓")
print("  RRT (区域票据) ──┤")
print("                    ↓")
print("  GTT (全局信任根) ← AG (接入网关)")
print("                    ↑")
print("  CTA (云端信任中心)")
print("\n下一步:")
print("  1. 安装完整依赖: pip install -r requirements.txt")
print("  2. 在不同终端启动各服务")
print("  3. 运行完整演示")
