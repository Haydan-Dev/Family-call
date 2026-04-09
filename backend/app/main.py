from fastapi import FastAPI
from app.routes.authroute import router  as user_router
from app.routes.contactroutes import router as contact_router
from app.routes.conversationsroutes import router as conversation_router
app = FastAPI()

@app.get("/")
def Home():
    return {"message":"main.py is running completely fine !"}

app.include_router(user_router)
app.include_router(contact_router)  
app.include_router(conversation_router)