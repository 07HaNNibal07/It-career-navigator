from fastapi import FastAPI
from it_career_navigator.routers import users, internal


app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

app.include_router(users.router)
app.include_router(internal.router)
