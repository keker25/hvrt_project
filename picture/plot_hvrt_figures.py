import os
import json
import math
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # 非交互后端，适合直接保存图片

import matplotlib.pyplot as plt


LOG_FILES = {
    "HVRT": "logs/hvrt.jsonl",
    "Centralized": "logs/centralized.jsonl",
    "Terminal-Online-Status": "logs/terminal_online_status.jsonl",
}

OUT_DIR = "figures"


def ensure_out_dir():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)


def load_jsonl(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def percentile(values, p):
    if not values:
        return 0
    vals = sorted(values)
    k = (len(vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    d0 = vals[f] * (c - k)
    d1 = vals[c] * (k - f)
    return d0 + d1


def stats_summary(values, warmup=5):
    if len(values) > warmup:
        values = values[warmup:]
    if not values:
        return {"mean": 0, "median": 0, "p95": 0, "std": 0, "values": []}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 0.95),
        "std": statistics.pstdev(values) if len(values) > 1 else 0,
        "values": values,
    }


def read_auth_latency():
    result = {}
    for scheme, path in LOG_FILES.items():
        recs = load_jsonl(path)
        values = [
            r["total_latency_ms"]
            for r in recs
            if r.get("event") == "auth_result"
        ]
        result[scheme] = stats_summary(values, warmup=5)
    return result


def read_roaming_latency():
    result = {}
    for scheme, path in LOG_FILES.items():
        recs = load_jsonl(path)
        values = [
            r["roaming_latency_ms"]
            for r in recs
            if r.get("event") == "roaming_auth_result"
        ]
        result[scheme] = stats_summary(values, warmup=0)
    return result


def read_revocation_stages():
    hvrt_path = LOG_FILES["HVRT"]
    recs = load_jsonl(hvrt_path)
    stage_order = [
        "before_revoke",
        "cta_revoked_no_sync",
        "ec_synced_ag_not_synced",
        "ec_ag_both_synced",
    ]
    stage_name_map = {
        "before_revoke": "Before revoke",
        "cta_revoked_no_sync": "CTA revoked\nno sync",
        "ec_synced_ag_not_synced": "EC synced\nAG not synced",
        "ec_ag_both_synced": "EC + AG\nsynced",
    }

    stage_result = {}
    for r in recs:
        if r.get("event") == "revocation_stage_result":
            stage = r["stage"]
            stage_result[stage] = r

    xs = []
    ys = []
    labels = []
    texts = []

    for stage in stage_order:
        if stage in stage_result:
            rec = stage_result[stage]
            xs.append(stage_name_map[stage])
            ys.append(1 if rec["result"] == "allow" else 0)
            labels.append(rec["result"])
            texts.append(
                f"CTA={rec['cta_version']}, EC={rec['ec_version']}, AG={rec['ag_version']}"
            )

    return xs, ys, labels, texts


def plot_fig1_auth_latency():
    data = read_auth_latency()
    schemes = list(data.keys())
    means = [data[s]["mean"] for s in schemes]
    stds = [data[s]["std"] for s in schemes]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(schemes, means, yerr=stds, capsize=6)
    plt.ylabel("Average authentication latency (ms)")
    plt.title("Figure 1. Authentication latency comparison")

    for bar, mean in zip(bars, means):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{mean:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig1_auth_latency.png"), dpi=300)
    plt.close()


def plot_fig2_roaming_latency():
    data = read_roaming_latency()
    schemes = list(data.keys())
    means = [data[s]["mean"] for s in schemes]
    stds = [data[s]["std"] for s in schemes]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(schemes, means, yerr=stds, capsize=6)
    plt.ylabel("Average roaming authentication latency (ms)")
    plt.title("Figure 2. Roaming latency comparison")

    for bar, mean in zip(bars, means):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{mean:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig2_roaming_latency.png"), dpi=300)
    plt.close()


def plot_fig3_revocation_stages():
    xs, ys, labels, texts = read_revocation_stages()

    plt.figure(figsize=(9, 5))
    bars = plt.bar(xs, ys)

    plt.ylim(-0.1, 1.2)
    plt.yticks([0, 1], ["deny", "allow"])
    plt.ylabel("Authentication result")
    plt.title("Figure 3. Authentication result before and after revocation sync")

    for bar, label, text in zip(bars, labels, texts):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.03,
            label,
            ha="center",
            va="bottom",
        )
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            0.5,
            text,
            ha="center",
            va="center",
            rotation=90,
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig3_revocation_stages.png"), dpi=300)
    plt.close()


def print_summary():
    auth = read_auth_latency()
    roaming = read_roaming_latency()

    print("\n[Figure 1] Authentication latency summary")
    for s, d in auth.items():
        print(
            f"{s:24} mean={d['mean']:.2f}  median={d['median']:.2f}  p95={d['p95']:.2f}  std={d['std']:.2f}"
        )

    print("\n[Figure 2] Roaming latency summary")
    for s, d in roaming.items():
        print(
            f"{s:24} mean={d['mean']:.2f}  median={d['median']:.2f}  p95={d['p95']:.2f}  std={d['std']:.2f}"
        )


if __name__ == "__main__":
    ensure_out_dir()
    plot_fig1_auth_latency()
    plot_fig2_roaming_latency()
    plot_fig3_revocation_stages()
    print_summary()
    print(f"\nSaved figures to: {OUT_DIR}/")
