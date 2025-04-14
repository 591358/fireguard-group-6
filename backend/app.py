import logging

from fastapi import FastAPI

from backend.routers.firerisks import firerisk_router
from backend.routers.users import users_router

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
app = FastAPI()


@app.get("/")
async def root():
    print("🔥 PRINT inside / endpoint")  # This should show up
    logger.debug("🚀 DEBUG: / endpoint called")  # This should show up
    logger.info("✅ INFO: / endpoint accessed")  # This should show up
    return {"message": "Hello from FastAPI app"}


app.include_router(users_router)
app.include_router(firerisk_router)
