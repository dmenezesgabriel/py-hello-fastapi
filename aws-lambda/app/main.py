import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from api.api_v1.api import router as api_router

load_dotenv()


root_path = os.getenv("ENV", default="")

app = FastAPI(
    title="FastAPI on AWS Lambda with Mangum",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path=f"/{root_path}",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


handler = Mangum(app)
