from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router


app = FastAPI(
    title="ComicCraft",
    description="AI-powered comic generator",
    version="1.0.0",
)


# Static files
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# Application routes
app.include_router(router)