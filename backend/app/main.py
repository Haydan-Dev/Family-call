from fastapi import FastAPI
from app.routes.user import router  as user_router

app = FastAPI()

@app.get("/")
def Home():
    return {"message":"main.py kaam karahi hai !"}

app.include_router(user_router)