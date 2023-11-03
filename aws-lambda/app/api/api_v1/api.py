from fastapi import APIRouter
from api.api_v1.endpoints import items, users

router = APIRouter()


@router.get("/")
async def read_root():
    return {"message": "Hello World"}


router.include_router(items.router)
router.include_router(users.router)
