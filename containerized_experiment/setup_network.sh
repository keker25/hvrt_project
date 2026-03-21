#!/bin/bash
# 设置容器网络延迟和丢包
# 使用: ./setup_network.sh <container_name> <delay_ms> <loss_percent>

CONTAINER_NAME=$1
DELAY_MS=${2:-50}
LOSS_PERCENT=${3:-5}

if [ -z "$CONTAINER_NAME" ]; then
    echo "Usage: $0 <container_name> [delay_ms] [loss_percent]"
    echo "Example: $0 hvrt-cta 50 5"
    exit 1
fi

echo "Setting up network for $CONTAINER_NAME: delay=${DELAY_MS}ms, loss=${LOSS_PERCENT}%"

# 删除现有 qdisc (如果存在)
docker exec $CONTAINER_NAME tc qdisc del dev eth0 root 2>/dev/null || true

# 添加延迟和丢包
docker exec $CONTAINER_NAME tc qdisc add dev eth0 root netem delay ${DELAY_MS}ms loss ${LOSS_PERCENT}%

echo "Network configuration applied!"
echo "To verify, run: docker exec $CONTAINER_NAME tc qdisc show dev eth0"
