import uvicorn
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routes import router, service as ag_service
from .sync_worker import AGSyncWorker
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8100)
args = parser.parse_args()

worker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker
    worker = AGSyncWorker(ag_service.storage)
    try:
        await worker.sync_with_ec()
    except Exception as e:
        import sys
        print(f"Warning: Initial sync failed: {e}", file=sys.stderr)
    task = asyncio.create_task(worker.start())
    yield
    worker.stop()
    task.cancel()


app = FastAPI(title="HVRT AG Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def root():
    return {"service": "ag", "status": "running", "port": args.port}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=args.port)
