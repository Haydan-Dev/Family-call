from fastapi import FastAPI
from backend.app.routes.userroutes import router  as user_router

app = FastAPI()

@app.get("/")
def Home():
    return {"message":"main.py kaam karahi hai !"}

app.include_router(user_router)