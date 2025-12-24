from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import db
import asyncio

# --- FIX IS HERE: Add 'faculty_projects' to the end of this list ---
from app.routers import auth, users, openings, recommendations, student_projects, faculty_projects,dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, db.connect)
        yield
    finally:
        await loop.run_in_executor(None, db.close)
    db.connect()
    yield
    db.close()
app = FastAPI(title="Guru Setu API", lifespan=lifespan)
@app.get("/")
def read_root():
    return {"message": "Guru Setu Backend is Running 🚀"}

# Register Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Profiles"])
app.include_router(openings.router, prefix="/openings", tags=["Openings"])
app.include_router(recommendations.router, prefix="/recommend", tags=["AI"])

# Project Routers
app.include_router(student_projects.router, prefix="/student-projects", tags=["Student Portfolio"])
app.include_router(faculty_projects.router, prefix="/faculty-projects", tags=["Faculty Research"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])