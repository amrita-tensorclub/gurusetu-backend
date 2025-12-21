from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import db
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, db.connect)
        yield
    finally:
        await loop.run_in_executor(None, db.close)

app = FastAPI(title="Guru Setu API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Guru Setu Backend is Running 🚀"}