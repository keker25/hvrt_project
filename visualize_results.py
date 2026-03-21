import json
import os
import statistics
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 中文字体设置（Windows 示例）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题


# plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
# plt.rcParams['axes.unicode_minus'] = False

def analyze_logs():
    files = {
        "HVRT": "logs/hvrt.jsonl",
        "Centralized": "logs/centralized.jsonl",
        "Terminal-Online-Status": "logs/terminal_online_status.jsonl"
    }
    
    auth_data = defaultdict(list)
    roaming_data = defaultdict(list)
    revocation_data = []
    
    for name, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    if rec.get("event") == "auth_result":
                        auth_data[name].append(rec["total_latency_ms"])
                    elif rec.get("event") == "roaming_auth_result":
                        roaming_data[name].append(rec["roaming_latency_ms"])
                    elif rec.get("event") == "revocation_stage_result":
                        revocation_data.append(rec)
    
    return auth_data, roaming_data, revocation_data

def plot_figure1(auth_data):
    print("\n生成图 1: 三种模式平均认证时延对比...")
    
    schemes = []
    means = []
    medians = []
    p95s = []
    std_devs = []
    
    for name in ["HVRT", "Centralized", "Terminal-Online-Status"]:
        if name in auth_data and len(auth_data[name]) > 5:
            vals = auth_data[name][5:]
            sorted_vals = sorted(vals)
            schemes.append(name)
            means.append(statistics.mean(vals))
            medians.append(statistics.median(vals))
            p95s.append(sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0)
            std_devs.append(statistics.pstdev(vals))
    
    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(schemes))
    width = 0.2
    
    ax.bar([i - 1.5 * width for i in x], means, width, label='均值', color='#3498db')
    ax.bar([i - 0.5 * width for i in x], medians, width, label='中位数', color='#2ecc71')
    ax.bar([i + 0.5 * width for i in x], p95s, width, label='P95', color='#f39c12')
    ax.bar([i + 1.5 * width for i in x], std_devs, width, label='标准差', color='#e74c3c')
    
    ax.set_xlabel('认证模式', fontsize=12)
    ax.set_ylabel('时延 (ms)', fontsize=12)
    ax.set_title('图 1: 三种模式平均认证时延对比', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(schemes, fontsize=11)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig('logs/figure1_auth_latency.png', dpi=300, bbox_inches='tight')
    print("✓ 图 1 已保存到 logs/figure1_auth_latency.png")

def plot_figure2(roaming_data):
    print("\n生成图 2: 三种模式漫游认证时延对比...")
    
    schemes = []
    means = []
    medians = []
    p95s = []
    
    for name in ["HVRT", "Centralized", "Terminal-Online-Status"]:
        if name in roaming_data and roaming_data[name]:
            vals = roaming_data[name]
            sorted_vals = sorted(vals)
            schemes.append(name)
            means.append(statistics.mean(vals))
            medians.append(statistics.median(vals))
            p95s.append(sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    x = range(len(schemes))
    width = 0.25
    
    ax1.bar([i - width for i in x], means, width, label='均值', color='#3498db')
    ax1.bar([i for i in x], medians, width, label='中位数', color='#2ecc71')
    ax1.bar([i + width for i in x], p95s, width, label='P95', color='#f39c12')
    
    ax1.set_xlabel('认证模式', fontsize=12)
    ax1.set_ylabel('时延 (ms)', fontsize=12)
    ax1.set_title('漫游认证时延统计', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(schemes, fontsize=11)
    ax1.legend()
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    for name in ["HVRT", "Centralized", "Terminal-Online-Status"]:
        if name in roaming_data and roaming_data[name]:
            ax2.plot(roaming_data[name], label=name, marker='.', linewidth=1, markersize=4)
    
    ax2.set_xlabel('漫游轮次', fontsize=12)
    ax2.set_ylabel('漫游时延 (ms)', fontsize=12)
    ax2.set_title('漫游认证时延变化趋势', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.suptitle('图 2: 三种模式漫游认证时延对比', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('logs/figure2_roaming_latency.png', dpi=300, bbox_inches='tight')
    print("✓ 图 2 已保存到 logs/figure2_roaming_latency.png")

def plot_figure3(revocation_data):
    print("\n生成图 3: 撤销前后认证结果...")
    
    stage_names = {
        "before_revoke": "撤销前",
        "cta_revoked_no_sync": "CTA已撤销\n未同步",
        "ec_synced_ag_not_synced": "EC已同步\nAG未同步",
        "ec_ag_both_synced": "EC与AG\n均同步"
    }
    
    stages = []
    results = []
    cta_versions = []
    ec_versions = []
    ag_versions = []
    
    for rec in revocation_data:
        stages.append(stage_names.get(rec["stage"], rec["stage"]))
        results.append(1 if rec["result"] == "allow" else 0)
        cta_versions.append(rec["cta_version"])
        ec_versions.append(rec["ec_version"])
        ag_versions.append(rec["ag_version"])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(stages))
    colors = ['#2ecc71' if r == 1 else '#e74c3c' for r in results]
    
    bars = ax.bar(x, [1]*len(stages), color=colors, edgecolor='black', linewidth=1.5)
    
    for i, (bar, res, cta_v, ec_v, ag_v) in enumerate(zip(bars, results, cta_versions, ec_versions, ag_versions)):
        label = "allow" if res == 1 else "deny"
        ax.text(bar.get_x() + bar.get_width()/2, 0.5, 
                f"{label}\n(CTA={cta_v}, EC={ec_v}, AG={ag_v})",
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='white' if res == 1 else 'white')
    
    ax.set_xlabel('同步阶段', fontsize=12)
    ax.set_ylabel('认证结果', fontsize=12)
    ax.set_title('图 3: 撤销前后认证结果变化', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=11)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['deny', 'allow'])
    ax.set_ylim(-0.2, 1.2)
    
    plt.tight_layout()
    plt.savefig('logs/figure3_revocation_result.png', dpi=300, bbox_inches='tight')
    print("✓ 图 3 已保存到 logs/figure3_revocation_result.png")

if __name__ == "__main__":
    print("=" * 80)
    print("  HVRT 实验结果可视化")
    print("=" * 80)
    
    if not os.path.exists("logs"):
        print("❌ 错误: logs 目录不存在！请先运行 hvrt_experiment.py")
        exit(1)
    
    auth_data, roaming_data, revocation_data = analyze_logs()
    
    if auth_data:
        plot_figure1(auth_data)
    else:
        print("\n⚠️  未找到认证数据！")
    
    if roaming_data:
        plot_figure2(roaming_data)
    else:
        print("\n⚠️  未找到漫游数据！")
    
    if revocation_data:
        plot_figure3(revocation_data)
    else:
        print("\n⚠️  未找到撤销数据！")
    
    print("\n" + "=" * 80)
    print("  所有图表已生成！")
    print("=" * 80)
