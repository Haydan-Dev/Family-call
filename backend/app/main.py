from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db import connect_to_mongo, close_mongo_connection

# Routers import (Tere wale same rahenge)
from app.routes.authroute import router  as user_router
from app.routes.contactroutes import router as contact_router
from app.routes.conversationsroutes import router as conversation_router
from app.routes.messageroutes import router as message_router
from app.routes.callroutes import router as call_router
from app.websockets.websocket_routes import router as websocket_router

# Lifespan - Server start aur stop hone ka Engine
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()  # Start hote hi DB se pipe jod dega
    yield
    await close_mongo_connection() # Band hote hi pipe kaat dega

# Lifespan ko app ke sath jodo
app = FastAPI(lifespan=lifespan)

@app.get("/")
def Home():
    return {"message":"main.py is running completely fine !"}

# Tere saare include_router same rahenge
app.include_router(user_router)
app.include_router(contact_router)  
app.include_router(conversation_router)
app.include_router(message_router)
app.include_router(call_router)
app.include_router(websocket_router)