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

        async with httpx.AsyncClient(timeout=10.0) as client:
            gtt_response = await client.get(f"{self.cta_url}/cta/gtt/current")
            gtt_response.raise_for_status()
            gtt_data = gtt_response.json()["gtt"]
            self.storage.save_gtt(gtt_data)

            delta_response = await client.get(
                f"{self.cta_url}/cta/revocation/delta",
                params={"from_version": current_version}
            )
            delta_response.raise_for_status()
            delta_data = delta_response.json()

            if delta_data["to_version"] > current_version:
                events = delta_data["changes"]
                self.storage.add_revocation_events(events)
                
                register_events = [e for e in events if e.get("type") == "device_register"]
                revoke_events = [e for e in events if e.get("type") != "device_register"]
                
                current_states = self.storage.get_device_states()
                
                for event in register_events:
                    current_states[event["device_id"]] = event["status"]
                    if event.get("device_secret"):
                        self.storage.save_device_secret(
                            event["device_id"], 
                            event["device_secret"]
                        )
                
                if revoke_events:
                    new_states, _ = apply_delta(
                        current_states,
                        current_version,
                        [type("RevocationEvent", (object,), e) for e in revoke_events]
                    )
                else:
                    new_states = current_states
                
                self.storage.save_device_states(new_states)
                self.storage.set_revocation_version(delta_data["to_version"])
                logger.info(f"Synced to version {delta_data['to_version']}")

    def stop(self):
        self.running = False
        logger.info("Stopping EC sync worker")

    def set_auto_sync(self, enabled: bool):
        self.auto_sync_enabled = enabled
        logger.info(f"Auto sync {'enabled' if enabled else 'disabled'}")
