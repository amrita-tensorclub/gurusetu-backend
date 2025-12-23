from fastapi import APIRouter

# You must define this variable named 'router'
router = APIRouter()

@router.get("/")
def get_recommendations():
    return {"message": "Recommendations module working"}