from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB
    db.connect()
    yield
    # Shutdown: Close DB
    db.close()

app = FastAPI(title="Guru Setu API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Guru Setu Backend is Running 🚀"}