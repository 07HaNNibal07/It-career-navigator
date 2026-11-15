from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from it_career_navigator.config import settings
from it_career_navigator.routers import career, cover_letters, internal, pages, users, vacancy_search


app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(cover_letters.router)
app.include_router(cover_letters.pages_router)
app.include_router(vacancy_search.router)
app.include_router(vacancy_search.pages_router)
app.include_router(career.router)
app.include_router(career.pages_router)
app.include_router(users.router)
app.include_router(internal.router)
app.include_router(pages.router)
