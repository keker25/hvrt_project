import uvicorn
from fastapi import FastAPI
from .routes import router

app = FastAPI(title="HVRT CTA Service", version="1.0.0")
app.include_router(router)


@app.get("/")
async def root():
    return {"service": "cta", "status": "running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
