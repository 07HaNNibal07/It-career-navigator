from fastapi import FastAPI
from it_career_navigator.routers import users
from contextlib import asynccontextmanager
from it_career_navigator.database import get_db,Base,engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "World"}
app.include_router(users.router)
