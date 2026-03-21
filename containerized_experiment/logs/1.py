#!/usr/bin/env python3
import os
import json
import statistics
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

logs_dir = "logs"

def read_terminal_logs():
    """批量读取所有终端日志"""
    auth_data = defaultdict(list)
    roaming_data = defaultdict(list)

    for filename in os.listdir(logs_dir):
        if filename.startswith("terminal_") and filename.endswith(".jsonl"):
            path = os.path.join(logs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    if rec.get("event") == "auth_result":
                        auth_data["HVRT"].append(rec["total_latency_ms"])
                    elif rec.get("event") == "roaming_auth_result":
                        roaming_data["HVRT"].append(rec["roaming_latency_ms"])
    return auth_data, roaming_data

def read_revocation_logs():
    """读取撤销实验日志"""
    revocation_path = os.path.join(logs_dir, "revocation_experiment.jsonl")
    revocation_data = []
    if os.path.exists(revocation_path):
        with open(revocation_path, "r", encoding="utf-8") as f:
            for line in f:
                revocation_data.append(json.loads(line))
    return revocation_data

def plot_auth_latency(auth_data):
    schemes = list(auth_data.keys())
    means, medians, p95s, stds = [], [], [], []

    for s in schemes:
        vals = sorted(auth_data[s])
        means.append(statistics.mean(vals))
        medians.append(statistics.median(vals))
        p95s.append(vals[int(len(vals)*0.95)])
        stds.append(statistics.pstdev(vals))

    x = range(len(schemes))
    width = 0.2
    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar([i - 1.5*width for i in x], means, width, label='均值', color='#3498db')
    ax.bar([i - 0.5*width for i in x], medians, width, label='中位数', color='#2ecc71')
    ax.bar([i + 0.5*width for i in x], p95s, width, label='P95', color='#f39c12')
    ax.bar([i + 1.5*width for i in x], stds, width, label='标准差', color='#e74c3c')
    ax.set_xticks(x)
    ax.set_xticklabels(schemes)
    ax.set_xlabel("认证模式")
    ax.set_ylabel("总认证时延 (ms)")
    ax.set_title("图 1: 多终端认证总时延")
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(logs_dir, "figure1_auth_latency.png"), dpi=300)
    print("✓ 图 1 已保存")

def plot_roaming_latency(roaming_data):
    schemes = list(roaming_data.keys())
    means, medians, p95s, stds = [], [], [], []

    for s in schemes:
        vals = sorted(roaming_data[s])
        means.append(statistics.mean(vals))
        medians.append(statistics.median(vals))
        p95s.append(vals[int(len(vals)*0.95)])
        stds.append(statistics.pstdev(vals))

    x = range(len(schemes))
    width = 0.2
    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar([i - 1.5*width for i in x], means, width, label='均值', color='#3498db')
    ax.bar([i - 0.5*width for i in x], medians, width, label='中位数', color='#2ecc71')
    ax.bar([i + 0.5*width for i in x], p95s, width, label='P95', color='#f39c12')
    ax.bar([i + 1.5*width for i in x], stds, width, label='标准差', color='#e74c3c')
    ax.set_xticks(x)
    ax.set_xticklabels(schemes)
    ax.set_xlabel("认证模式")
    ax.set_ylabel("漫游时延 (ms)")
    ax.set_title("图 2: 多终端漫游时延")
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(logs_dir, "figure2_roaming_latency.png"), dpi=300)
    print("✓ 图 2 已保存")

def plot_revocation_results(revocation_data):
    stage_labels = {
        "stage1_pre_revocation": "撤销前",
        "stage2_cta_revoked_not_synced": "CTA已撤销\n未同步",
        "stage3_ec_synced_ag_not_synced": "EC已同步\nAG未同步",
        "stage4_all_synced": "EC与AG均同步"
    }
    stages, results = [], []

    for rec in revocation_data:
        stages.append(stage_labels.get(rec["stage"], rec["stage"]))
        results.append(1 if rec["result"] == "allow" else 0)

    fig, ax = plt.subplots(figsize=(10,6))
    colors = ['#2ecc71' if r == 1 else '#e74c3c' for r in results]
    bars = ax.bar(range(len(stages)), [1]*len(stages), color=colors)
    for i, (bar, r) in enumerate(zip(bars, results)):
        label = "allow" if r==1 else "deny"
        ax.text(bar.get_x()+bar.get_width()/2, 0.5, label, ha='center', va='center', color='white', fontweight='bold')
    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels(stages)
    ax.set_yticks([0,1])
    ax.set_yticklabels(['deny','allow'])
    ax.set_ylim(-0.2,1.2)
    ax.set_xlabel("同步阶段")
    ax.set_ylabel("认证结果")
    ax.set_title("图 3: 撤销前后认证结果")
    plt.tight_layout()
    plt.savefig(os.path.join(logs_dir, "figure3_revocation_result.png"), dpi=300)
    print("✓ 图 3 已保存")

if __name__ == "__main__":
    auth_data, roaming_data = read_terminal_logs()
    revocation_data = read_revocation_logs()
    plot_auth_latency(auth_data)
    plot_roaming_latency(roaming_data)
    plot_revocation_results(revocation_data)
