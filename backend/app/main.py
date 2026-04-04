from fastapi import FastAPI
from app.routes.authroute import router  as user_router

app = FastAPI()

@app.get("/")
def Home():
    return {"message":"main.py kaam karahi hai !"}

app.include_router(user_router)