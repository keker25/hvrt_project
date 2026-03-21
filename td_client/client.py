# import httpx
# from common import generate_id, generate_hmac_sha256, get_logger
# from .storage import TDStorage
#
# logger = get_logger("td_client")
#
#
# class TDClient:
#     def __init__(self, device_id: str, storage: TDStorage = None):
#         self.device_id = device_id
#         self.storage = storage or TDStorage()
#         self.device_data = self.storage.load_device(device_id)
#         if not self.device_data:
#             raise ValueError(f"Device {device_id} not initialized. Please run 'init' first.")
#
#     async def register_with_cta(self, cta_url: str, region_id: str):
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{cta_url}/cta/register_device",
#                 json={
#                     "device_id": self.device_id,
#                     "region_id": region_id
#                 }
#             )
#             response.raise_for_status()
#             result = response.json()
#             self.storage.save_device(result["device_id"], result["device_secret"])
#             self.device_data = self.storage.load_device(self.device_id)
#             logger.info(f"Registered device: {result['device_id']}")
#             return result
#
#     async def enroll(self, ag_url: str, region_id: str = "regionA"):
#         async with httpx.AsyncClient() as client:
#             rrt_response = await client.post(
#                 f"{ag_url}/ag/issue_rrt",
#                 json={
#                     "device_id": self.device_id,
#                     "region_id": region_id
#                 }
#             )
#             rrt_response.raise_for_status()
#             rrt = rrt_response.json()["rrt"]
#
#             sat_response = await client.post(
#                 f"{ag_url}/ag/issue_sat",
#                 json={
#                     "device_id": self.device_id,
#                     "rrt_id": rrt["rrt_id"]
#                 }
#             )
#             sat_response.raise_for_status()
#             sat = sat_response.json()["sat"]
#
#             self.storage.save_tickets(self.device_id, rrt=rrt, sat=sat)
#             self.device_data = self.storage.load_device(self.device_id)
#             logger.info(f"Enrolled successfully with AG {ag_url}")
#             return {"rrt": rrt, "sat": sat}
#
#     async def access(self, ag_url: str):
#         if not self.device_data.get("rrt") or not self.device_data.get("sat"):
#             raise ValueError("No tickets found. Please enroll first.")
#
#         request_id = generate_id("req")
#
#         async with httpx.AsyncClient() as client:
#             request_response = await client.post(
#                 f"{ag_url}/ag/access/request",
#                 json={
#                     "request_id": request_id,
#                     "device_id": self.device_id,
#                     "sat": self.device_data["sat"],
#                     "rrt": self.device_data["rrt"]
#                 }
#             )
#             request_response.raise_for_status()
#             challenge = request_response.json()
#
#             message = f"{challenge['challenge_id']}:{challenge['nonce']}:{self.device_id}"
#             device_secret = self.device_data["device_secret"]
#             response_hmac = generate_hmac_sha256(device_secret, message)
#
#             respond_response = await client.post(
#                 f"{ag_url}/ag/access/respond",
#                 json={
#                     "request_id": request_id,
#                     "challenge_id": challenge["challenge_id"],
#                     "device_id": self.device_id,
#                     "response_hmac": response_hmac
#                 }
#             )
#             respond_response.raise_for_status()
#             result = respond_response.json()
#
#             logger.info(f"Access result: {result['result']} - {result['reason']}")
#             return result
#
#     async def roam(self, ag_url: str, region_id: str = "regionA"):
#         logger.info(f"Roaming to AG {ag_url}")
#         await self.enroll(ag_url, region_id)
#         return await self.access(ag_url)
import httpx
from common import generate_id, generate_hmac_sha256, get_logger
from .storage import TDStorage

logger = get_logger("td_client")


class TDClient:
    def __init__(self, device_id: str, storage: TDStorage = None):
        self.device_id = device_id
        self.storage = storage or TDStorage()
        self.device_data = self.storage.load_device(device_id)
        if not self.device_data:
            raise ValueError(f"Device {device_id} not initialized. Please run 'init' first.")

    async def register_with_cta(self, cta_url: str, region_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{cta_url}/cta/register_device",
                json={"device_id": self.device_id, "region_id": region_id}
            )
            response.raise_for_status()
            result = response.json()
            self.storage.save_device(result["device_id"], result["device_secret"])
            self.device_data = self.storage.load_device(self.device_id)
            logger.info(f"Registered device: {result['device_id']}")
            return result

    async def enroll(self, ag_url: str, region_id: str = "regionA"):
        async with httpx.AsyncClient() as client:
            rrt_response = await client.post(
                f"{ag_url}/ag/issue_rrt",
                json={"device_id": self.device_id, "region_id": region_id}
            )
            rrt_response.raise_for_status()
            rrt = rrt_response.json()["rrt"]

            sat_response = await client.post(
                f"{ag_url}/ag/issue_sat",
                json={"device_id": self.device_id, "rrt_id": rrt["rrt_id"]}
            )
            sat_response.raise_for_status()
            sat = sat_response.json()["sat"]

            self.storage.save_tickets(self.device_id, rrt=rrt, sat=sat)
            self.device_data = self.storage.load_device(self.device_id)
            logger.info(f"Enrolled successfully with AG {ag_url}")
            return {"rrt": rrt, "sat": sat}

    async def _fetch_status_receipt(self, cta_url: str, request_id: str = None):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{cta_url}/cta/device/status_receipt",
                json={"device_id": self.device_id, "request_id": request_id}
            )
            response.raise_for_status()
            return response.json()["receipt"]

    async def access(self, ag_url: str, mode: str = "default", cta_url: str = "http://127.0.0.1:8000"):
        if not self.device_data.get("rrt") or not self.device_data.get("sat"):
            raise ValueError("No tickets found. Please enroll first.")

        request_id = generate_id("req")
        status_receipt = None
        if mode == "terminal_online_status":
            status_receipt = await self._fetch_status_receipt(cta_url, request_id)

        async with httpx.AsyncClient() as client:
            request_response = await client.post(
                f"{ag_url}/ag/access/request",
                json={
                    "request_id": request_id,
                    "device_id": self.device_id,
                    "sat": self.device_data["sat"],
                    "rrt": self.device_data["rrt"],
                    "status_receipt": status_receipt
                }
            )
            request_response.raise_for_status()
            challenge = request_response.json()

            message = f"{challenge['challenge_id']}:{challenge['nonce']}:{self.device_id}"
            device_secret = self.device_data["device_secret"]
            response_hmac = generate_hmac_sha256(device_secret, message)

            respond_response = await client.post(
                f"{ag_url}/ag/access/respond",
                json={
                    "request_id": request_id,
                    "challenge_id": challenge["challenge_id"],
                    "device_id": self.device_id,
                    "response_hmac": response_hmac,
                    "mode": mode
                }
            )
            respond_response.raise_for_status()
            result = respond_response.json()
            logger.info(f"Access result: {result['result']} - {result['reason']}")
            return result

    async def roam(self, ag_url: str, region_id: str = "regionA", mode: str = "default"):
        logger.info(f"Roaming to AG {ag_url}")
        await self.enroll(ag_url, region_id)
        return await self.access(ag_url, mode=mode)
