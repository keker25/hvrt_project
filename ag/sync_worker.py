import asyncio
import httpx
from common import get_logger, apply_delta, Config

logger = get_logger("ag_sync_worker")


class AGSyncWorker:
    def __init__(self, storage, ec_url: str = Config.EC_URL):
        self.storage = storage
        self.ec_url = ec_url
        self.running = False
        self._task = None
    
    async def sync_with_ec(self):
        logger.debug("Syncing with EC")
        current_version = self.storage.get_revocation_version()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 获取 GTT - 兼容 EC 的不同端点
                gtt_data = None
                gtt_endpoints = [
                    f"{self.ec_url}/ec/gtt/current",
                    f"{self.ec_url}/gtt",
                    f"{self.ec_url}/ec/gtt",
                ]
                for ep in gtt_endpoints:
                    try:
                        resp = await client.get(ep)
                        resp.raise_for_status()
                        j = resp.json()
                        if isinstance(j, dict) and j.get("gtt"):
                            gtt_data = j.get("gtt")
                        elif isinstance(j, dict) and j.get("gtt_id"):
                            gtt_data = j
                        if gtt_data:
                            self.storage.save_gtt(gtt_data)
                            logger.debug(f"Updated GTT from EC endpoint {ep}: {gtt_data.get('gtt_id')}")
                            break
                    except Exception:
                        logger.debug(f"EC GTT endpoint not available: {ep}")
                
                # 获取当前状态 - 支持不同返回路径
                state_data = None
                state_endpoints = [
                    f"{self.ec_url}/ec/state/current",
                    f"{self.ec_url}/state/current",
                    f"{self.ec_url}/ec/state",
                ]
                for ep in state_endpoints:
                    try:
                        resp = await client.get(ep)
                        resp.raise_for_status()
                        state_data = resp.json()
                        if state_data:
                            self.storage.save_device_states(state_data.get("device_states", {}))
                            for device_id, secret in state_data.get("device_secrets", {}).items():
                                self.storage.save_device_secret(device_id, secret)
                            if state_data.get("ec_pubkey"):
                                self.storage.set_ec_pubkey(state_data["ec_pubkey"])
                                logger.debug("Updated EC public key from %s" % ep)
                            break
                    except Exception:
                        logger.debug(f"EC state endpoint not available: {ep}")
                
                # 获取状态增量
                try:
                    delta_response = await client.get(
                        f"{self.ec_url}/ec/state/delta",
                        params={"from_version": current_version}
                    )
                    delta_response.raise_for_status()
                    delta_data = delta_response.json()
                    
                    if delta_data.get("to_version") > current_version:
                        logger.info(f"Applying delta from {current_version} to {delta_data['to_version']}")
                        events = delta_data.get("changes", [])
                        
                        if events:
                            # 按版本顺序处理事件
                            events_sorted = sorted(events, key=lambda e: e.get("version", 0))
                            
                            current_states = self.storage.get_device_states()
                            
                            for event in events_sorted:
                                if event.get("type") == "device_register":
                                    # 处理注册事件
                                    current_states[event["device_id"]] = event["status"]
                                    if event.get("device_secret"):
                                        self.storage.save_device_secret(
                                            event["device_id"], 
                                            event["device_secret"]
                                        )
                                else:
                                    # 处理撤销事件
                                    current_states[event["device_id"]] = event["status"]
                            
                            self.storage.save_device_states(current_states)
                        
                        self.storage.set_revocation_version(delta_data["to_version"])
                        logger.info(f"Synced to version {delta_data['to_version']}")
                except Exception as e:
                    logger.error(f"Failed to get state delta: {e}")
        except Exception as e:
            logger.error(f"Sync with EC failed: {e}")
    
    async def _run_loop(self):
        while self.running:
            try:
                await self.sync_with_ec()
            except Exception as e:
                logger.error(f"Sync error: {e}")
            await asyncio.sleep(10)
    
    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
    
    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
