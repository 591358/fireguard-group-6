# backend/app.py
from fastapi import FastAPI

from backend.routers.users import users_router

app = FastAPI()

# Include routers here
app.include_router(users_router)
