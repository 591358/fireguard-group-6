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

app.include_router(users_router)
app.include_router(firerisk_router)
