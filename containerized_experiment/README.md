# HVRT 容器化多终端真实网络实验

## 📋 实验架构

| 节点 | 容器名 | 端口 | 功能 |
|------|--------|------|------|
| CTA | hvrt-cta | 8000 | 云端信任中心 |
| EC | hvrt-ec | 8050 | 边缘协调节点 |
| AG1 | hvrt-ag1 | 8100 | 接入网关 1 |
| AG2 | hvrt-ag2 | 8200 | 接入网关 2 |
| TD | - | 随机 | 终端设备（多实例） |

---

## 🚀 快速开始

### 1. 启动基础设施
```bash
cd containerized_experiment
docker-compose up -d --build
```

### 2. 等待服务健康
```bash
docker-compose ps
```

### 3. 配置网络延迟（可选，模拟真实 IoT 网络）
```bash
# 为所有容器设置 50ms 延迟 + 5% 丢包
./setup_network.sh hvrt-cta 50 5
./setup_network.sh hvrt-ec 50 5
./setup_network.sh hvrt-ag1 50 5
./setup_network.sh hvrt-ag2 50 5
```

### 4. 运行实验
```bash
# 在本地运行实验编排脚本（连接到容器服务）
python run_experiment.py --num-terminals 10 --num-rounds 10 --roaming-rounds 5
```

---

## 📁 文件说明

| 文件 | 描述 |
|------|------|
| `cta_server.py` | CTA 服务端 |
| `ec_server.py` | EC 服务端 |
| `ag_server.py` | AG 服务端 |
| `td_client.py` | TD 终端客户端 |
| `run_experiment.py` | 实验编排脚本 |
| `setup_network.sh` | 网络延迟配置脚本 |
| `docker-compose.yml` | Docker 编排配置 |
| `Dockerfile` | Docker 镜像构建文件 |
| `requirements.txt` | Python 依赖 |

---

## 📊 实验指标

### 普通认证
- 票据签发耗时
- 挑战生成/响应耗时
- 票据验证耗时
- 状态检查耗时
- 总认证延迟
- P50/P95/P99 分位数

### 漫游认证
- 漫游认证总时延
- 成功率

### 撤销同步
- 各阶段认证结果（allow/deny）
- 节点版本号

---

## 🎯 实验流程

```
1. 启动 CTA → EC → AG1 → AG2
   ↓
2. 初始化 TD 终端（注册、获取密钥）
   ↓
3. 多终端并发认证（M 轮）
   ↓
4. 多终端漫游认证（K 轮）
   ↓
5. 撤销同步实验（4 个阶段）
   ↓
6. 保存日志、分析结果
```

---

## 🔧 高级配置

### 环境变量
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CTA_PORT` | 8000 | CTA 端口 |
| `EC_PORT` | 8050 | EC 端口 |
| `AG_PORT` | 8100/8200 | AG 端口 |
| `CTA_URL` | http://cta:8000 | CTA 地址 |
| `EC_URL` | http://ec:8050 | EC 地址 |

### 网络模拟
```bash
# 清除网络配置
docker exec hvrt-cta tc qdisc del dev eth0 root

# 验证网络配置
docker exec hvrt-cta tc qdisc show dev eth0
```

---

## 📈 结果分析

所有 JSON 日志保存在 `logs/` 目录：
- `terminal_td_001.jsonl` - 终端 1 的日志
- `terminal_td_002.jsonl` - 终端 2 的日志
- 等等...

---

## 🎊 总结

这是一个完整的、真实的容器化实验环境，可以：
- ✅ 验证 HVRT 认证性能
- ✅ 测试漫游认证
- ✅ 验证撤销同步
- ✅ 模拟真实网络延迟
- ✅ 多终端并发测试
