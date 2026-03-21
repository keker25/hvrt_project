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
            gtt_data = gtt_response.json()["gtt"]
            self.storage.save_gtt(gtt_data)
            logger.debug(f"Updated GTT from EC: {gtt_data['gtt_id']}")
            
            state_response = await client.get(f"{self.ec_url}/ec/state/current")
            state_response.raise_for_status()
            state_data = state_response.json()
            
            self.storage.save_device_states(state_data["device_states"])
            for device_id, secret in state_data.get("device_secrets", {}).items():
                self.storage.save_device_secret(device_id, secret)
            
            if state_data.get("ec_pubkey"):
                self.storage.set_ec_pubkey(state_data["ec_pubkey"])
                logger.debug("Updated EC public key")
            
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
                    for event in events:
                        if event.get("type") == "device_register":
                            current_states[event["device_id"]] = event["status"]
                            if event.get("device_secret"):
                                self.storage.save_device_secret(
                                    event["device_id"], 
                                    event["device_secret"]
                                )
                    
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
