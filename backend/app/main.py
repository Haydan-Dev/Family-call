from fastapi import FastAPI
from app.routes.authroute import router  as user_router
from app.routes.contactroutes import router as contact_router
app = FastAPI()

@app.get("/")
def Home():
    return {"message":"main.py kaam karahi hai !"}

app.include_router(user_router)
app.include_router(contact_router)