# HVRT 分层信任离线认证原型系统

## 项目简介

HVRT (Hierarchical Verified Trust) 是一个分层信任离线认证原型系统，实现了基于 Ed25519 和 HMAC-SHA256 的分层票据链认证机制。

## 系统架构

系统包含四类实体：

- **CTA (Cloud Trust Authority)** - 云端信任中心 (端口 8000)
- **EC (Edge Coordinator)** - 边缘协调节点 (端口 8050)
- **AG (Access Gateway)** - 接入网关 (端口 8100, 8200)
- **TD (Terminal Device)** - 终端设备 (命令行客户端)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速启动

### 1. 启动服务

在不同的终端中分别运行：

```bash
# 启动 CTA
python -m cta.main

# 启动 EC
python -m ec.main

# 启动 AG1
python -m ag.main --port 8100

# 启动 AG2
python -m ag.main --port 8200
```

### 2. 初始化系统

```bash
python scripts/init_system.py
```

### 3. 注册设备

```bash
python scripts/issue_device.py --device-id td001
```

### 4. 使用 TD 客户端

```bash
# 注册设备到 CTA (必须 - 论文实验要求真实注册流程)
python -m td_client.main register --device-id td001 --cta http://127.0.0.1:8000 --region regionA

# 向 AG 注册(enroll)获取票据
python -m td_client.main enroll --device-id td001 --ag http://127.0.0.1:8100

# 访问 AG
python -m td_client.main access --device-id td001 --ag http://127.0.0.1:8100

# 漫游到另一个 AG
python -m td_client.main roam --device-id td001 --ag http://127.0.0.1:8200
```

注意: `init` 命令仅用于 DEMO 演示，论文实验必须使用 `register` 命令获取真实的 device_secret。

## 测试脚本

- `scripts/run_roaming_test.py` - 运行漫游测试
- `scripts/run_concurrency_test.py` - 运行并发测试
- `scripts/revoke_device.py` - 撤销设备
- `scripts/collect_metrics.py` - 收集性能指标

## 密码学特性

- **Ed25519** - 用于 GTT、RRT、SAT 签名
- **HMAC-SHA256** - 用于终端挑战响应
- **票据链验证** - SAT → RRT → GTT 完整链式验证

## 对比模式

- **default** - AG 本地离线验证
- **centralized** - AG 转发给 CTA 验证
- **terminal_online_status** - TD 从 CTA 获取状态回执
