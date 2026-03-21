import uvicorn
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routes import router, service as ec_service
from .sync_worker import ECSyncWorker

worker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker
    worker = ECSyncWorker(ec_service.storage)
    task = asyncio.create_task(worker.start())
    yield
    worker.stop()
    task.cancel()


app = FastAPI(title="HVRT EC Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def root():
    return {"service": "ec", "status": "running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8050)
