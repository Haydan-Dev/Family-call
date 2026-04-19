# Imp imports hai jo ki websocke ke liye zaruri hai and token verify karne ke liye bhi zaruri hai 
from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from app.core.security import get_current_user_token
import json

# idhar same wo i kiya hai router naam ke variable se apirouter se ek route bana ke main.py may daal diya hai websocket_routes naam se  
router = APIRouter(
    prefix="/ws", # ws likhna industry standards hai , warna websocket bhi likh sakte hai par theek nah hai frontend waala pagal ho jaayega
    tags=["WebSockets"]
)
# saare active connection iss may jaayenge jesse hi koi bhi online hoga login hote hi iss may apne aap aajayega  
active_connections: dict = {}

# apni main api hai ye websocket ki par ye normal api jesse kaam nahi karti hai 
@router.websocket("/message/{user_id}") # user_id frontend se aayegi 
async def chat_endpoint(websocket:WebSocket,user_id:str,token:str | None = None):
    # token bhi frontend se aayega url ke sath user_id ke theek baad piche piche 
    if token is None: # agar nahi aaya to await may code dikha ye error return 
        await websocket.close(code=1008)
        return
    # agar aaya to phir uss token ko apne webtoken waale function se varfy karna hai 
    try:
        # agar token milla to code aage jaayega warna phir se code error dega
        varified_token = get_current_user_token(jwt_token=token)
        # agar code user_id se match nahi hua to error 
        if varified_token !=user_id:
            await websocket.close(code=1008)
            return
        else:   
            # agar match hua to websocket connection ko accept karega 
            await websocket.accept()
            # frontend se aai hui user_id ko active connection ki user_id se websocket may daalega 
            active_connections[user_id] = websocket
            try:
                # agar user_id websocket may chali gai to data/message/chat/audio/video recieve hoga warna ,  
                while True:
                    # idhar data jo hai wo raw string may aayega  
                    data = await websocket.receive_text()
                    # hamme uss data ko disc format may convert karna padega taaki uss disc ki keys ko access kar saku
                    data_disc = json.loads(data)
                    # db se sender id overwrite karna hai sender ke khude ka id hacker change bhi karsakta hia 
                    data_disc["sender_id"] = user_id
                    # abb disc se receiver id nikalna padega
                    receiver_id = data_disc.get("receiver_id")
                    # agar reciver_id active_connection ki list may hai to 
                    clean_data = json.dumps(data_disc)
                    if receiver_id in active_connections:
                        receiver_websocket = active_connections[receiver_id]
                        await receiver_websocket.send_text(clean_data)
                    else:
                        print(f"Offline: {receiver_id} is not online right now.") 
                    print(f"message from:{user_id}:{data}")
             # except waale may jaayega and user ko offline samjh ke active_connection ko band kardega       
            except WebSocketDisconnect: 
                del active_connections[user_id]
    except Exception:
        await websocket.close(code=1008)
        return