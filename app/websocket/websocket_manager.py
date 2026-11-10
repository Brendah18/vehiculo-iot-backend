"""
Gestor WebSocket (POO) segmentado por id_vehiculo.
Permite conectar múltiples clientes (navegador web, ESP8266/ESP32, monitoreo)
al canal exclusivo de cada vehículo (/ws/{id_vehiculo}) y difundir estados en tiempo real.
"""
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketManager:
    """Clase POO que administra las conexiones WebSocket activas por vehículo."""

    def __init__(self) -> None:
        # Diccionario: { id_vehiculo: [WebSocket1, WebSocket2, ...] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, id_vehiculo: int, websocket: WebSocket) -> None:
        """Acepta y registra una nueva conexión WebSocket para un vehículo."""
        await websocket.accept()
        if id_vehiculo not in self.active_connections:
            self.active_connections[id_vehiculo] = []
        self.active_connections[id_vehiculo].append(websocket)

    def disconnect(self, id_vehiculo: int, websocket: WebSocket) -> None:
        """Elimina una conexión cerrada del canal del vehículo."""
        if id_vehiculo in self.active_connections:
            if websocket in self.active_connections[id_vehiculo]:
                self.active_connections[id_vehiculo].remove(websocket)
            if not self.active_connections[id_vehiculo]:
                del self.active_connections[id_vehiculo]

    def has_connections(self, id_vehiculo: int) -> bool:
        """Indica si el vehículo tiene al menos un cliente WebSocket conectado."""
        return bool(self.active_connections.get(id_vehiculo))

    async def broadcast_to_vehiculo(
        self, id_vehiculo: int, payload: Dict[str, Any]
    ) -> None:
        """
        Envía un mensaje JSON en tiempo real a todos los clientes suscritos
        al canal del vehículo indicado.
        """
        conexiones = self.active_connections.get(id_vehiculo, [])
        conexiones_caidas: List[WebSocket] = []
        for ws in conexiones:
            try:
                await ws.send_json(payload)
            except Exception:
                conexiones_caidas.append(ws)

        for ws_caido in conexiones_caidas:
            self.disconnect(id_vehiculo, ws_caido)


ws_manager = WebSocketManager()
