#!/usr/bin/env python3
"""
网络模拟工具 - 模拟真实 IoT 网络条件
"""
import time
import random
from typing import Tuple

import os


class NetworkSimulator:
    def __init__(self, delay_min_ms: float = 10, delay_max_ms: float = 100, loss_rate: float = 0.05):
        # allow override from environment variables for experiments
        try:
            env_min = float(os.getenv("NET_DELAY_MIN_MS", ""))
            env_max = float(os.getenv("NET_DELAY_MAX_MS", ""))
        except Exception:
            env_min = None
            env_max = None

        try:
            env_loss = float(os.getenv("NET_LOSS_RATE", ""))
        except Exception:
            env_loss = None

        self.delay_min_ms = env_min if env_min is not None else delay_min_ms
        self.delay_max_ms = env_max if env_max is not None else delay_max_ms
        self.loss_rate = env_loss if env_loss is not None else loss_rate
    
    def simulate_network(self) -> Tuple[float, bool]:
        """
        模拟网络延迟和丢包
        返回: (实际延迟ms, 是否丢包)
        """
        delay_ms = random.uniform(self.delay_min_ms, self.delay_max_ms)
        lost = random.random() < self.loss_rate
        
        time.sleep(delay_ms / 1000)
        return delay_ms, lost
    
    def simulate_delay_only(self) -> float:
        """仅模拟网络延迟，不丢包"""
        delay_ms = random.uniform(self.delay_min_ms, self.delay_max_ms)
        time.sleep(delay_ms / 1000)
        return delay_ms

# 默认网络模拟器
default_network = NetworkSimulator(delay_min_ms=10, delay_max_ms=100, loss_rate=0.05)
