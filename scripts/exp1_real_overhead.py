import os
import sys
import time
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timezone

# 引入你项目中的真实密码学工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.crypto_utils import (
    generate_hmac_sha256,
    generate_ed25519_keypair,
    sign_with_ed25519,
    generate_id,
    generate_nonce
)
import hashlib


def measure_real_compute(iterations=5000):
    """实打实地运行各方案底层密码学原语组合，测量真实 CPU 耗时"""
    print(f"正在执行真实密码学原语压测 (循环 {iterations} 次)...")

    # 准备密钥和数据
    secret_key = "test_device_secret_key_base64_encoded"
    priv_key, pub_key = generate_ed25519_keypair()
    msg_str = "device_id:td001:timestamp:1710000000:nonce:abcdefg"
    msg_dict = {"device_id": "td001", "timestamp": 1710000000, "nonce": "abcdefg"}

    times = {}

    # 1. HVRT (你的方案): 仅需计算 1 次 HMAC 作为挑战响应
    start = time.perf_counter()
    for _ in range(iterations):
        generate_hmac_sha256(secret_key, msg_str)
    times['HVRT'] = ((time.perf_counter() - start) / iterations) * 1000

    # 2. LADM (集中轻量方案): 终端通常只做 1 次 SHA256 哈希 + 简单异或 (此处测单次哈希)
    start = time.perf_counter()
    for _ in range(iterations):
        hashlib.sha256(msg_str.encode()).hexdigest()
    times['LADM'] = ((time.perf_counter() - start) / iterations) * 1000

    # 3. NEHA (分层密钥方案): 需要执行动态密钥派生，一般包含 3 次哈希/HMAC
    start = time.perf_counter()
    for _ in range(iterations):
        k1 = generate_hmac_sha256(secret_key, "step1")
        k2 = generate_hmac_sha256(k1, "step2")
        generate_hmac_sha256(k2, msg_str)
    times['NEHA'] = ((time.perf_counter() - start) / iterations) * 1000

    # 4. KBC (在线票据方案): 需用对称密钥解密TGS票据并生成Authenticator，视作2次HMAC + 1次AES(用哈希近似替代)
    start = time.perf_counter()
    for _ in range(iterations):
        generate_hmac_sha256(secret_key, "decrypt_ticket")
        generate_hmac_sha256(secret_key, "build_authenticator")
        hashlib.sha256(msg_str.encode()).hexdigest()
    times['KBC'] = ((time.perf_counter() - start) / iterations) * 1000

    # 5. ECHA (边缘公钥方案): 终端需要对请求报文进行完整的 Ed25519 非对称签名
    start = time.perf_counter()
    for _ in range(iterations):
        sign_with_ed25519(priv_key, msg_dict)
    times['ECHA'] = ((time.perf_counter() - start) / iterations) * 1000

    # 6. BCAE (区块链方案): 终端需要构建交易 -> 序列化 -> Ed25519签名 -> 哈希生成TxID
    start = time.perf_counter()
    for _ in range(iterations):
        sig = sign_with_ed25519(priv_key, msg_dict)
        tx_raw = msg_str + sig
        hashlib.sha256(tx_raw.encode()).hexdigest()  # 生成TxID
    times['BCAE'] = ((time.perf_counter() - start) / iterations) * 1000

    return times


def measure_real_payload_size():
    """根据各协议实际要求，组装真实的 JSON 报文并计算 UTF-8 字节数"""

    pub_key_mock = "A" * 44  # base64 Ed25519 pubkey is ~44 chars
    sig_mock = "B" * 88  # base64 Ed25519 sig is ~88 chars
    hmac_mock = "C" * 44  # base64 HMAC-SHA256 is ~44 chars
    ts = datetime.now(timezone.utc).isoformat()

    sizes = {}

    # 1. HVRT: 提交必要的标识，加上轻量级 SAT 和挑战响应
    hvrt_payload = {
        "device_id": "td001",
        "sat_id": generate_id("sat"),
        "rrt_id": generate_id("rrt"),
        "nonce": generate_nonce(),
        "hmac_response": hmac_mock
    }
    sizes['HVRT'] = len(json.dumps(hvrt_payload).encode('utf-8'))

    # 2. LADM: 轻量身份标识 + 哈希鉴别码
    ladm_payload = {
        "device_id": "td001",
        "timestamp": ts,
        "auth_mac": hmac_mock
    }
    sizes['LADM'] = len(json.dumps(ladm_payload).encode('utf-8'))

    # 3. NEHA: 分层需要携带额外的域标识和派生参数
    neha_payload = {
        "device_id": "td001",
        "domain_id": "domain_A",
        "layer_idx": 2,
        "derivation_salt": generate_nonce(),
        "timestamp": ts,
        "mac": hmac_mock
    }
    sizes['NEHA'] = len(json.dumps(neha_payload).encode('utf-8'))

    # 4. KBC: 类似 Kerberos，需要携带庞大的加密 Ticket 和 Authenticator
    kbc_payload = {
        "device_id": "td001",
        "service_id": "ag_8100",
        "ticket": "E" * 256,  # 模拟加密后的票据块
        "authenticator": "F" * 128  # 模拟认证块
    }
    sizes['KBC'] = len(json.dumps(kbc_payload).encode('utf-8'))

    # 5. ECHA: 基于非对称密码，必须携带终端公钥和完整签名
    echa_payload = {
        "device_id": "td001",
        "public_key": pub_key_mock,
        "timestamp": ts,
        "nonce": generate_nonce(),
        "signature": sig_mock
    }
    sizes['ECHA'] = len(json.dumps(echa_payload).encode('utf-8'))

    # 6. BCAE: 区块链交易结构最臃肿，包含智能合约调用的完整上下文
    bcae_payload = {
        "tx_version": "1.0",
        "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
        "method": "cross_domain_auth",
        "sender_pubkey": pub_key_mock,
        "payload_data": {
            "device_id": "td001",
            "target_ag": "ag_8100",
            "timestamp": ts
        },
        "gas_limit": 21000,
        "signature": sig_mock
    }
    sizes['BCAE'] = len(json.dumps(bcae_payload).encode('utf-8'))

    return sizes


def run_experiment_1():
    print("=" * 60)
    print(" 实验一：终端侧真实计算耗时与报文体积实测 (无伪造)")
    print("=" * 60)

    # 获取绝对真实的实测数据
    times_ms = measure_real_compute(10000)  # 测 1 万次取平均
    payload_bytes = measure_real_payload_size()

    schemes = ['LADM (集中)', 'NEHA (分层)', 'KBC (票据)', 'ECHA (非对称)', 'BCAE (区块链)', 'HVRT (本文)']
    keys = ['LADM', 'NEHA', 'KBC', 'ECHA', 'BCAE', 'HVRT']

    c_times = [times_ms[k] for k in keys]
    c_bytes = [payload_bytes[k] for k in keys]

    print("\n--- 实测结果 (基于 common.crypto_utils) ---")
    print(f"{'方案':<15} | {'CPU耗时 (ms)':<15} | {'序列化载荷 (Bytes)':<15}")
    print("-" * 55)
    for i in range(len(schemes)):
        print(f"{schemes[i]:<15} | {c_times[i]:<15.4f} | {c_bytes[i]:<15}")

    # ===== 绘制高标准学术图表 =====
    fig, ax1 = plt.subplots(figsize=(11, 6))

    x = np.arange(len(schemes))
    width = 0.35

    color1 = '#2c7fb8'
    bars1 = ax1.bar(x - width / 2, c_times, width, label='Computation Latency (ms)', color=color1, edgecolor='black',
                    linewidth=1)
    ax1.set_ylabel('Latency (ms) - Log Scale', color=color1, fontsize=12, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_yscale('log')  # 必须用对数，因为非对称加密比对称加密慢百倍
    ax1.set_ylim(bottom=min(c_times) * 0.5, top=max(c_times) * 5)  # 优化Y轴留白

    ax2 = ax1.twinx()
    color2 = '#f03b20'
    bars2 = ax2.bar(x + width / 2, c_bytes, width, label='Payload Size (Bytes)', color=color2, edgecolor='black',
                    linewidth=1, hatch='//')
    ax2.set_ylabel('Payload Size (Bytes)', color=color2, fontsize=12, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(bottom=0, top=max(c_bytes) * 1.2)

    ax1.set_xticks(x)
    ax1.set_xticklabels(schemes, fontsize=11, fontweight='bold')
    plt.title('Experiment 1: Real Cryptographic Computation & Payload Overhead at Terminal', fontsize=14, pad=15,
              fontweight='bold')

    # 图例合并
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left', framealpha=0.9)

    # 标注数据标签
    def autolabel(rects, ax, is_float=False):
        for rect in rects:
            height = rect.get_height()
            label = f'{height:.4f}' if is_float else f'{int(height)}'
            ax.annotate(label,
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    autolabel(bars1, ax1, is_float=True)
    autolabel(bars2, ax2, is_float=False)

    ax1.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()

    os.makedirs("logs", exist_ok=True)
    save_path = "logs/exp1_real_overhead.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ 真实测算完成！图表已保存至: {save_path}")


if __name__ == "__main__":
    run_experiment_1()