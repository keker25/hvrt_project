import asyncio
from .client import TDClient
from .storage import TDStorage
from common import get_logger

logger = get_logger("td_scenarios")


async def run_full_scenario(device_id: str, cta_url: str, ag_url: str):
    logger.info("=== Running Full Scenario ===")
    
    storage = TDStorage()
    
    if not storage.load_device(device_id):
        logger.info(f"Initializing device {device_id}")
        storage.save_device(device_id, f"secret_{device_id}")
    
    client = TDClient(device_id, storage)
    
    logger.info("Enrolling with AG...")
    await client.enroll(ag_url)
    
    logger.info("Accessing AG...")
    result = await client.access(ag_url)
    
    logger.info(f"Scenario complete. Result: {result}")
    return result
