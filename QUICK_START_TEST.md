# HVRT 快速启动和测试指南

## 启动服务

### 方法 1：使用 start_real_services.py（推荐）

在一个单独的终端中运行：
```bash
python start_real_services.py
```

这会启动：
- CTA: http://127.0.0.1:8000
- EC:  http://127.0.0.1:8050
- AG1: http://127.0.0.1:8100
- AG2: http://127.0.0.1:8200

### 方法 2：分别启动每个服务

打开 4 个终端，分别运行：

终端 1 - CTA：
```bash
python -m cta.main
```

终端 2 - EC：
```bash
python -m ec.main
```

终端 3 - AG1：
```bash
python -m ag.main --port 8100
```

终端 4 - AG2：
```bash
python -m ag.main --port 8200
```

---

## 运行测试

### 1. 同步一致性测试（推荐先运行）

在新的终端中运行：
```bash
python scripts/test_sync_consistency.py
```

测试内容：
- 用例 A：注册事件传播（CTA→EC→AG）
- 用例 B：撤销事件传播
- 用例 C：重复 sync 不应重复写脏数据

### 2. 完整端到端功能测试

```bash
python scripts/test_e2e_full.py
```

测试内容：
- 用例 1：注册—同步—发票据—default 访问成功
- 用例 2：centralized 模式成功
- 用例 3：terminal_online_status 模式成功
- 用例 4：漫游成功
- 用例 5：撤销后全部拒绝

### 3. 性能指标收集

```bash
python scripts/collect_metrics.py
```

---

## 注意事项

1. **确保虚拟环境已激活**
   - 如果使用虚拟环境，确保已激活

2. **服务启动需要时间**
   - 等待 5-10 秒让所有服务完全启动

3. **环境清理**
   - 测试前可以删除数据目录：
     ```
     rm -rf cta/data ec/data ag/data td_client/data
     ```

4. **端口占用**
   - 确保端口 8000, 8050, 8100, 8200 未被占用

---

## 故障排查

### 服务无法启动
- 检查端口是否被占用
- 检查 Python 依赖是否已安装：`pip install -r requirements.txt`

### 测试连接超时
- 确认所有服务都已启动
- 检查防火墙设置
- 等待服务完全启动后再运行测试

### 同步测试失败
- 确认 EC 和 AG 的同步接口正常
- 检查数据目录是否有写入权限
