from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from it_career_navigator.config import settings
from it_career_navigator.routers import internal, pages, users


app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(users.router)
app.include_router(internal.router)
app.include_router(pages.router)
