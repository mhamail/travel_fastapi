from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel

from src.api.core.response import api_response
from .lib.db_con import engine
from src.api.routers import authRoute, userRoute, mediaRoute, rideRoute


# Define app lifespan — this runs once when the app starts and when it shuts down
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Runs once on startup ---
    # print("🟢 Checking if tables exist...")

    # # Create all tables that are missing (safe – only creates non-existent ones)
    # SQLModel.metadata.create_all(engine)
    # print("✅ All tables verified / created.")
    # # --- Runs once on shutdown ---
    # print("🔴 App shutting down...")

    yield  # 👈 after this, FastAPI starts handling requests


# Initialize the FastAPI app with the custom lifespan
app = FastAPI(lifespan=lifespan, root_path="/api")
# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],  # or "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422, content={"data": exc.errors(), "message": "Validation failed"}
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    msg = str(exc.orig)
    if "duplicate key" in msg or "UNIQUE constraint failed" in msg:
        error_msg = "Duplicate entry — record already exists."
    elif "violates not-null constraint" in msg:
        error_msg = "Required field missing in database insert."
    else:
        error_msg = "Database integrity error."
    return JSONResponse(status_code=422, content={"data": msg, "message": error_msg})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    # This catches model assignment errors like "User has no field ..."
    if "has no field" in str(exc):
        message = str(exc).split('"')[-2] + " is not a valid field name."
    else:
        message = str(exc)
    return JSONResponse(
        status_code=400,
        content={"message": message},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"message": str(exc)})


@app.get("/")
def root():
    return {"message": "Hello, FastAPI with uv!"}


app.include_router(authRoute.router)
app.include_router(userRoute.router)
app.include_router(mediaRoute.router)
app.include_router(rideRoute.router)
