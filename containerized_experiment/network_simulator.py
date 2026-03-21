#!/usr/bin/env python3
"""
网络模拟工具 - 模拟真实 IoT 网络条件
"""
import time
import random
from typing import Tuple

class NetworkSimulator:
    def __init__(self, delay_min_ms: float = 10, delay_max_ms: float = 100, loss_rate: float = 0.05):
        self.delay_min_ms = delay_min_ms
        self.delay_max_ms = delay_max_ms
        self.loss_rate = loss_rate
    
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
