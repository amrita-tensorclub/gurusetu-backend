from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # <--- THIS WAS MISSING
from contextlib import asynccontextmanager
from app.core.database import db
import asyncio
import os

# Import Routers
from app.routers import (
    auth, 
    users, 
    openings, 
    recommendations, 
    student_projects, 
    faculty_projects, 
    dashboard,
    applications,
    notifications
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    try:
        # Connect to DB on startup
        await loop.run_in_executor(None, db.connect)
        yield
    finally:
        # Close DB on shutdown
        await loop.run_in_executor(None, db.close)

app = FastAPI(title="Guru Setu API", lifespan=lifespan)

# 1. Ensure directory exists
os.makedirs("uploads", exist_ok=True)

# 2. Mount static files (This line caused the error before)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://gurusetu.netlify.app" # ✅ Use your specific Netlify URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def read_root():
    return {"message": "Guru Setu Backend is Running 🚀"}

# Register Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Profiles"])
app.include_router(openings.router, prefix="/openings", tags=["Openings"])
app.include_router(recommendations.router, prefix="/recommend", tags=["AI"])
app.include_router(student_projects.router, prefix="/student-projects", tags=["Student Portfolio"])
app.include_router(faculty_projects.router, prefix="/faculty-projects", tags=["Faculty Research"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"]) # <--- NEW REGISTER
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"]) # <--- 2. REGISTER IT