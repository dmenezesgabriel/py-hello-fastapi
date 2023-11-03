from fastapi import FastAPI
from api.api_v1.api import router as api_router
from mangum import Mangum

app = FastAPI(
    title="FastAPI on AWS Lambda with Mangum",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


app.include_router(api_router, prefix="/api/v1")


handler = Mangum(app)
