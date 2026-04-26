from fastapi import WebSocket
from typing import Dict
import logging

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logging.info(f"User {user_id} connected. Total active: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logging.info(f"User {user_id} disconnected. Total active: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logging.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()
