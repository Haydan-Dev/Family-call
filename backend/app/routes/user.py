from fastapi import APIRouter
from app.models.user import User

router = APIRouter(
    prefix="/user",
    tags=["Users"]
)

@router.get("/",response_model=User)
def user():
    return {User}