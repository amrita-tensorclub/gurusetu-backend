from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import db

# Import all your routers
from app.routers import auth, users, openings, recommendations, student_projects

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    yield
    db.close()

app = FastAPI(title="Guru Setu API", lifespan=lifespan)

# Register Routers (Connect the "wires")
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Profiles"])
app.include_router(openings.router, prefix="/openings", tags=["Openings"])
app.include_router(recommendations.router, prefix="/recommend", tags=["AI"])
app.include_router(student_projects.router, prefix="/student-projects", tags=["Portfolio"])

@app.get("/")
def read_root():
    return {"message": "Guru Setu Backend is Running 🚀"}