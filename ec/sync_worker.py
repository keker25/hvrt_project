# import asyncio
# import httpx
# from common import get_logger, apply_delta, Config
#
# logger = get_logger("ec_sync_worker")
#
#
# class ECSyncWorker:
#     def __init__(self, storage, cta_url: str = Config.CTA_URL):
#         self.storage = storage
#         self.cta_url = cta_url
#         self.running = False
#         self.auto_sync_enabled = True
#
#     async def start(self, interval: int = 5):
#         self.running = True
#         logger.info("Starting EC sync worker")
#         while self.running:
#             if self.auto_sync_enabled:
#                 try:
#                     await self.sync_with_cta()
#                 except Exception as e:
#                     logger.error(f"Sync failed: {e}")
#             await asyncio.sleep(interval)
#
#     async def sync_with_cta(self):
#         logger.debug("Syncing with CTA")
#
#         current_version = self.storage.get_revocation_version()
#
#         async with httpx.AsyncClient(timeout=10.0) as client:
#             gtt_response = await client.get(f"{self.cta_url}/cta/gtt/current")
#             gtt_response.raise_for_status()
#             gtt_data = gtt_response.json()["gtt"]
#             self.storage.save_gtt(gtt_data)
#             logger.debug(f"Updated GTT: {gtt_data['gtt_id']}")
#
#             delta_response = await client.get(
#                 f"{self.cta_url}/cta/revocation/delta",
#                 params={"from_version": current_version}
#             )
#             delta_response.raise_for_status()
#             delta_data = delta_response.json()
#
#             if delta_data["to_version"] > current_version:
#                 logger.info(f"Applying delta from {current_version} to {delta_data['to_version']}")
#                 current_states = self.storage.get_device_states()
#                 new_states, new_version = apply_delta(
#                     current_states,
#                     current_version,
#                     [type('RevocationEvent', (object,), e) for e in delta_data["changes"]]
#                 )
#                 self.storage.save_device_states(new_states)
#                 self.storage.set_revocation_version(delta_data["to_version"])
#                 logger.info(f"Synced to version {delta_data['to_version']}")
#
#     def stop(self):
#         self.running = False
#         logger.info("Stopping EC sync worker")
#
#     def set_auto_sync(self, enabled: bool):
#         self.auto_sync_enabled = enabled
#         logger.info(f"Auto sync {'enabled' if enabled else 'disabled'}")


import asyncio
import httpx
from common import get_logger, apply_delta, Config

logger = get_logger("ec_sync_worker")


class ECSyncWorker:
    def __init__(self, storage, cta_url: str = Config.CTA_URL):
        self.storage = storage
        self.cta_url = cta_url
        self.running = False
        self.auto_sync_enabled = True

    async def start(self, interval: int = 5):
        self.running = True
        logger.info("Starting EC sync worker")
        while self.running:
            if self.auto_sync_enabled:
                try:
                    await self.sync_with_cta()
                except Exception as e:
                    logger.error(f"Sync failed: {e}")
            await asyncio.sleep(interval)

    async def sync_with_cta(self):
        logger.debug("Syncing with CTA")
        current_version = self.storage.get_revocation_version()

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 获取 GTT - 支持多个可能的 CTA 路径以兼容容器化和非容器化版本
                gtt_data = None
                gtt_endpoints = [
                    f"{self.cta_url}/cta/gtt/current",
                    f"{self.cta_url}/gtt",
                    f"{self.cta_url}/sync",
                ]
                for ep in gtt_endpoints:
                    try:
                        resp = await client.get(ep)
                        resp.raise_for_status()
                        j = resp.json()
                        # 支持不同返回格式
                        if isinstance(j, dict) and j.get("gtt"):
                            gtt_data = j.get("gtt")
                        elif isinstance(j, dict) and j.get("gtt_id"):
                            gtt_data = j
                        elif isinstance(j, dict) and j.get("revocation_version") and j.get("gtt") is None:
                            # /sync 返回的结构里可能直接包含 gtt under 'gtt'
                            gtt_data = j.get("gtt") or j
                        if gtt_data:
                            self.storage.save_gtt(gtt_data)
                            logger.debug(f"Updated GTT from {ep}: {gtt_data.get('gtt_id')}")
                            break
                    except Exception:
                        logger.debug(f"CTA GTT endpoint not available: {ep}")
                
                # 获取 revocation delta
                try:
                    delta_response = await client.get(
                        f"{self.cta_url}/cta/revocation/delta",
                        params={"from_version": current_version}
                    )
                    delta_response.raise_for_status()
                    delta_data = delta_response.json()

                    if delta_data.get("to_version") > current_version:
                        events = delta_data.get("changes", [])
                        self.storage.add_revocation_events(events)
                        
                        current_states = self.storage.get_device_states()
                        
                        # 按版本顺序处理事件
                        events_sorted = sorted(events, key=lambda e: e.get("version", 0))
                        
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
                                event_dict = event.copy()
                                event_dict["new_status"] = event_dict.pop("status")
                                revocation_event = type("RevocationEvent", (object,), event_dict)
                                current_states[event["device_id"]] = event["status"]
                        
                        new_states = current_states
                        
                        self.storage.save_device_states(new_states)
                        self.storage.set_revocation_version(delta_data["to_version"])
                        logger.info(f"Synced to version {delta_data['to_version']}")
                except Exception as e:
                    logger.error(f"Failed to get revocation delta: {e}")
        except Exception as e:
            logger.error(f"Sync with CTA failed: {e}")

    def stop(self):
        self.running = False
        logger.info("Stopping EC sync worker")

    def set_auto_sync(self, enabled: bool):
        self.auto_sync_enabled = enabled
        logger.info(f"Auto sync {'enabled' if enabled else 'disabled'}")
