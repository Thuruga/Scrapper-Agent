"""
WebSocket Connection Manager.

Gerencia conexões WebSocket ativas por job_id para streaming de logs em tempo real.
"""

from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    """Mantém um mapa de job_id → WebSocket para envio de mensagens."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        self.active_connections.pop(job_id, None)

    async def send_message(self, message: dict, job_id: str):
        ws = self.active_connections.get(job_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass


# Instância singleton usada pela aplicação
manager = ConnectionManager()
