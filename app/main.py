from fastapi import FastAPI

from app.booking_router import (
    router as booking_router,
)

from . import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(booking_router)
