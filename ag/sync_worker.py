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
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            gtt_response = await client.get(f"{self.ec_url}/ec/gtt/current")
            gtt_response.raise_for_status()
            gtt_summary = gtt_response.json()
            
            full_gtt_response = await client.get(f"{Config.CTA_URL}/cta/gtt/current")
            full_gtt_response.raise_for_status()
            full_gtt = full_gtt_response.json()["gtt"]
            self.storage.save_gtt(full_gtt)
            logger.debug(f"Updated GTT from EC: {full_gtt['gtt_id']}")
            
            delta_response = await client.get(
                f"{self.ec_url}/ec/state/delta",
                params={"from_version": current_version}
            )
            delta_response.raise_for_status()
            delta_data = delta_response.json()
            
            if delta_data["to_version"] > current_version:
                logger.info(f"Applying delta from {current_version} to {delta_data['to_version']}")
                events = delta_data["changes"]
                
                if events:
                    current_states = self.storage.get_device_states()
                    new_states, _ = apply_delta(
                        current_states,
                        current_version,
                        [type("RevocationEvent", (object,), e) for e in events]
                    )
                    self.storage.save_device_states(new_states)
                
                self.storage.set_revocation_version(delta_data["to_version"])
                logger.info(f"Synced to version {delta_data['to_version']}")
    
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
