"""
Punto de entrada principal de la API FastAPI y servidor WebSocket (Práctica 2.5 y 2.6).
Expone:
- Los 21 Stored Procedures en endpoints RESTful organizados por entidad.
- Endpoints de Reglas de Negocio (Movimiento Individual CON historial y DEMO SIN historial).
- Endpoint WebSocket en tiempo real segmentado por vehículo: /ws/{id_vehiculo}
"""
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    ComandoCreate,
    ComandoUpdate,
    DemoCreate,
    DemoUpdate,
    EjecutarMovimientoRequest,
    EstadoUpdate,
    HistorialCreate,
    MovimientoDemoCreate,
    MovimientoDemoUpdate,
    VehiculoCreate,
    VehiculoUpdate,
)
from app.repositories.iot_repository import iot_repository
from app.services.vehiculo_service import vehiculo_service
from app.websocket.websocket_manager import ws_manager

app = FastAPI(
    title="API Vehículo IoT - Amazon RDS & WebSocket",
    description="Arquitectura POO con 21 Stored Procedures en Amazon RDS y WebSocket por vehículo.",
    version="2.5.0",
)

# Habilitar CORS para permitir peticiones desde clientes web HTTPS y microcontroladores
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health Check"])
def root() -> Dict[str, Any]:
    """Verifica que el servidor FastAPI esté en línea."""
    return {
        "status": "online",
        "servicio": "API Vehículo IoT con Amazon RDS y WebSocket",
        "total_sp_soportados": 21,
    }


# ==============================================================================
# SECCIÓN 1: ENDPOINTS DE VEHÍCULOS (APIs 1 a 5 -> SPs 1 a 5)
# ==============================================================================
@app.post("/api/vehiculos", tags=["1. Vehículos"], summary="1. sp_crear_vehiculo")
def api_crear_vehiculo(body: VehiculoCreate) -> Dict[str, Any]:
    """API #1 -> CALL sp_crear_vehiculo(nombre, modelo, descripcion, microcontrolador)"""
    return iot_repository.crear_vehiculo(
        body.nombre, body.modelo, body.descripcion, body.microcontrolador
    )


@app.get("/api/vehiculos", tags=["1. Vehículos"], summary="2. sp_obtener_vehiculos")
def api_obtener_vehiculos() -> List[Dict[str, Any]]:
    """API #2 -> CALL sp_obtener_vehiculos()"""
    return iot_repository.obtener_vehiculos()


@app.get(
    "/api/vehiculos/{id_vehiculo}",
    tags=["1. Vehículos"],
    summary="3. sp_obtener_vehiculo",
)
def api_obtener_vehiculo(id_vehiculo: int) -> Dict[str, Any]:
    """API #3 -> CALL sp_obtener_vehiculo(id_vehiculo)"""
    vehiculo = iot_repository.obtener_vehiculo(id_vehiculo)
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return vehiculo


@app.put(
    "/api/vehiculos/{id_vehiculo}",
    tags=["1. Vehículos"],
    summary="4. sp_actualizar_vehiculo",
)
def api_actualizar_vehiculo(id_vehiculo: int, body: VehiculoUpdate) -> Dict[str, Any]:
    """API #4 -> CALL sp_actualizar_vehiculo(...)"""
    return iot_repository.actualizar_vehiculo(
        id_vehiculo,
        body.nombre,
        body.modelo,
        body.descripcion,
        body.microcontrolador,
        body.activo,
    )


@app.delete(
    "/api/vehiculos/{id_vehiculo}",
    tags=["1. Vehículos"],
    summary="5. sp_eliminar_vehiculo",
)
def api_eliminar_vehiculo(id_vehiculo: int) -> Dict[str, Any]:
    """API #5 -> CALL sp_eliminar_vehiculo(id_vehiculo)"""
    return iot_repository.eliminar_vehiculo(id_vehiculo)


# ==============================================================================
# SECCIÓN 2: ENDPOINTS DE COMANDOS (APIs 6 a 10 -> SPs 6 a 10)
# ==============================================================================
@app.post("/api/comandos", tags=["2. Comandos"], summary="6. sp_crear_comando")
def api_crear_comando(body: ComandoCreate) -> Dict[str, Any]:
    """API #6 -> CALL sp_crear_comando(id_vehiculo, nombre, codigo, descripcion)"""
    return iot_repository.crear_comando(
        body.id_vehiculo, body.nombre, body.codigo, body.descripcion
    )


@app.get(
    "/api/vehiculos/{id_vehiculo}/comandos",
    tags=["2. Comandos"],
    summary="7. sp_obtener_comandos_vehiculo",
)
def api_obtener_comandos_vehiculo(id_vehiculo: int) -> List[Dict[str, Any]]:
    """API #7 -> CALL sp_obtener_comandos_vehiculo(id_vehiculo)"""
    return iot_repository.obtener_comandos_vehiculo(id_vehiculo)


@app.get(
    "/api/comandos/{id_comando}",
    tags=["2. Comandos"],
    summary="8. sp_obtener_comando",
)
def api_obtener_comando(id_comando: int) -> Dict[str, Any]:
    """API #8 -> CALL sp_obtener_comando(id_comando)"""
    cmd = iot_repository.obtener_comando(id_comando)
    if not cmd:
        raise HTTPException(status_code=404, detail="Comando no encontrado")
    return cmd


@app.put(
    "/api/comandos/{id_comando}",
    tags=["2. Comandos"],
    summary="9. sp_actualizar_comando",
)
def api_actualizar_comando(id_comando: int, body: ComandoUpdate) -> Dict[str, Any]:
    """API #9 -> CALL sp_actualizar_comando(id_comando, nombre, codigo, descripcion, activo)"""
    return iot_repository.actualizar_comando(
        id_comando, body.nombre, body.codigo, body.descripcion, body.activo
    )


@app.delete(
    "/api/comandos/{id_comando}",
    tags=["2. Comandos"],
    summary="10. sp_eliminar_comando",
)
def api_eliminar_comando(id_comando: int) -> Dict[str, Any]:
    """API #10 -> CALL sp_eliminar_comando(id_comando)"""
    return iot_repository.eliminar_comando(id_comando)


# ==============================================================================
# SECCIÓN 3: ENDPOINTS DE ESTADO DEL VEHÍCULO (APIs 11 y 12 -> SPs 11 y 12)
# ==============================================================================
@app.put(
    "/api/estado",
    tags=["3. Estado del Vehículo"],
    summary="11. sp_actualizar_estado",
)
async def api_actualizar_estado(body: EstadoUpdate) -> Dict[str, Any]:
    """API #11 -> CALL sp_actualizar_estado(id_vehiculo, id_comando, conectado)"""
    iot_repository.actualizar_estado(
        body.id_vehiculo, body.id_comando, body.conectado
    )
    estado = iot_repository.obtener_estado(body.id_vehiculo)
    await ws_manager.broadcast_to_vehiculo(
        body.id_vehiculo, {"evento": "ESTADO_ACTUALIZADO", "estado": estado}
    )
    return {"mensaje": "Estado actualizado", "estado": estado}


@app.get(
    "/api/vehiculos/{id_vehiculo}/estado",
    tags=["3. Estado del Vehículo"],
    summary="12. sp_obtener_estado",
)
def api_obtener_estado(id_vehiculo: int) -> Dict[str, Any]:
    """API #12 -> CALL sp_obtener_estado(id_vehiculo)"""
    estado = iot_repository.obtener_estado(id_vehiculo)
    if not estado:
        raise HTTPException(
            status_code=404, detail="Estado no registrado para este vehículo"
        )
    return estado


# ==============================================================================
# SECCIÓN 4: ENDPOINTS DE HISTORIAL DE COMANDOS (APIs 13 y 14 -> SPs 13 y 14)
# ==============================================================================
@app.post(
    "/api/historial",
    tags=["4. Historial de Comandos"],
    summary="13. sp_registrar_historial",
)
def api_registrar_historial(body: HistorialCreate) -> Dict[str, Any]:
    """API #13 -> CALL sp_registrar_historial(id_vehiculo, id_comando, origen)"""
    return iot_repository.registrar_historial(
        body.id_vehiculo, body.id_comando, body.origen
    )


@app.get(
    "/api/vehiculos/{id_vehiculo}/historial",
    tags=["4. Historial de Comandos"],
    summary="14. sp_obtener_historial",
)
def api_obtener_historial(id_vehiculo: int) -> List[Dict[str, Any]]:
    """API #14 -> CALL sp_obtener_historial(id_vehiculo)"""
    return iot_repository.obtener_historial(id_vehiculo)


# ==============================================================================
# SECCIÓN 5: ENDPOINTS DE DEMOS (APIs 15 a 19 -> SPs 15 a 19)
# ==============================================================================
@app.post("/api/demos", tags=["5. Demos"], summary="15. sp_crear_demo")
def api_crear_demo(body: DemoCreate) -> Dict[str, Any]:
    """API #15 -> CALL sp_crear_demo(id_vehiculo, nombre, descripcion)"""
    return iot_repository.crear_demo(body.id_vehiculo, body.nombre, body.descripcion)


@app.get(
    "/api/vehiculos/{id_vehiculo}/demos",
    tags=["5. Demos"],
    summary="16. sp_obtener_demos",
)
def api_obtener_demos(id_vehiculo: int) -> List[Dict[str, Any]]:
    """API #16 -> CALL sp_obtener_demos(id_vehiculo)"""
    return iot_repository.obtener_demos(id_vehiculo)


@app.get("/api/demos/{id_demo}", tags=["5. Demos"], summary="17. sp_obtener_demo")
def api_obtener_demo(id_demo: int) -> Dict[str, Any]:
    """API #17 -> CALL sp_obtener_demo(id_demo)"""
    demo = iot_repository.obtener_demo(id_demo)
    if not demo:
        raise HTTPException(status_code=404, detail="Demo no encontrada")
    return demo


@app.put("/api/demos/{id_demo}", tags=["5. Demos"], summary="18. sp_actualizar_demo")
def api_actualizar_demo(id_demo: int, body: DemoUpdate) -> Dict[str, Any]:
    """API #18 -> CALL sp_actualizar_demo(id_demo, nombre, descripcion, activo)"""
    return iot_repository.actualizar_demo(
        id_demo, body.nombre, body.descripcion, body.activo
    )


@app.delete("/api/demos/{id_demo}", tags=["5. Demos"], summary="19. sp_eliminar_demo")
def api_eliminar_demo(id_demo: int) -> Dict[str, Any]:
    """API #19 -> CALL sp_eliminar_demo(id_demo)"""
    return iot_repository.eliminar_demo(id_demo)


# ==============================================================================
# SECCIÓN 6: ENDPOINTS DE MOVIMIENTOS DEMO (APIs 20 y 21+ -> SPs de Movimientos)
# ==============================================================================
@app.post(
    "/api/demos/movimientos",
    tags=["6. Movimientos Demo"],
    summary="20. sp_agregar_movimiento_demo",
)
def api_agregar_movimiento_demo(body: MovimientoDemoCreate) -> Dict[str, Any]:
    """API #20 -> CALL sp_agregar_movimiento_demo(id_demo, id_comando, orden, duracion_ms, pausa_ms)"""
    return iot_repository.agregar_movimiento_demo(
        body.id_demo, body.id_comando, body.orden, body.duracion_ms, body.pausa_ms
    )


@app.get(
    "/api/demos/{id_demo}/movimientos",
    tags=["6. Movimientos Demo"],
    summary="21. sp_obtener_movimientos_demo",
)
def api_obtener_movimientos_demo(id_demo: int) -> List[Dict[str, Any]]:
    """API #21 -> CALL sp_obtener_movimientos_demo(id_demo)"""
    return iot_repository.obtener_movimientos_demo(id_demo)


@app.put(
    "/api/demos/movimientos/{id_demo_movimiento}",
    tags=["6. Movimientos Demo"],
    summary="sp_actualizar_movimiento_demo",
)
def api_actualizar_movimiento_demo(
    id_demo_movimiento: int, body: MovimientoDemoUpdate
) -> Dict[str, Any]:
    """Actualiza un paso de la demo -> CALL sp_actualizar_movimiento_demo(...)"""
    return iot_repository.actualizar_movimiento_demo(
        id_demo_movimiento,
        body.id_comando,
        body.orden,
        body.duracion_ms,
        body.pausa_ms,
    )


@app.delete(
    "/api/demos/movimientos/{id_demo_movimiento}",
    tags=["6. Movimientos Demo"],
    summary="sp_eliminar_movimiento_demo",
)
def api_eliminar_movimiento_demo(id_demo_movimiento: int) -> Dict[str, Any]:
    """Elimina un paso de la demo -> CALL sp_eliminar_movimiento_demo(id_demo_movimiento)"""
    return iot_repository.eliminar_movimiento_demo(id_demo_movimiento)


# ==============================================================================
# SECCIÓN 7: REGLAS DE NEGOCIO CRÍTICAS (FASE 3: CONTROL Y DEMO TEMPORIZADA)
# ==============================================================================
@app.post(
    "/api/control/movimiento",
    tags=["7. Reglas de Negocio IoT"],
    summary="Regla 1: Ejecutar movimiento individual (CON Historial + WebSocket)",
)
async def api_ejecutar_movimiento_individual(
    body: EjecutarMovimientoRequest,
) -> Dict[str, Any]:
    """
    Ejecuta un movimiento manual/individual:
    - Actualiza `estado_vehiculo` (`sp_actualizar_estado`).
    - SÍ registra en `historial_comandos` (`sp_registrar_historial`).
    - Notifica en tiempo real por WebSocket a `/ws/{id_vehiculo}`.
    """
    return await vehiculo_service.ejecutar_movimiento_individual(
        body.id_vehiculo, body.id_comando, body.origen
    )


@app.post(
    "/api/control/demos/{id_demo}/ejecutar",
    tags=["7. Reglas de Negocio IoT"],
    summary="Regla 2: Ejecutar DEMO temporizada (SIN Historial + WebSocket)",
)
async def api_ejecutar_demo(id_demo: int) -> Dict[str, Any]:
    """
    Ejecuta la secuencia completa de una DEMO respetando `duracion_ms` y `pausa_ms`:
    - Actualiza `estado_vehiculo` en cada paso (`sp_actualizar_estado`).
    - NO registra en `historial_comandos` (prohibido contaminar el historial durante la DEMO).
    - Emite cada paso en tiempo real por WebSocket a `/ws/{id_vehiculo}`.
    """
    return await vehiculo_service.ejecutar_secuencia_demo(id_demo)


# ==============================================================================
# SECCIÓN 8: SERVIDOR WEBSOCKET POR VEHÍCULO (/ws/{id_vehiculo})
# ==============================================================================
@app.websocket("/ws/{id_vehiculo}")
async def websocket_vehiculo_endpoint(
    websocket: WebSocket, id_vehiculo: int
) -> None:
    """
    Canal WebSocket en tiempo real exclusivo por vehículo (`ws://.../ws/1` o `wss://.../ws/1`).
    - Al conectar: envía el estado actual del vehículo desde Amazon RDS.
    - Al recibir comandos JSON `{"id_comando": 1, "origen": "WS"}`: ejecuta movimiento individual.
    - Al recibir `{"id_demo": 1}`: lanza la DEMO temporizada sin historial.
    """
    await ws_manager.connect(id_vehiculo, websocket)
    try:
        estado_inicial = iot_repository.obtener_estado(id_vehiculo)
        await websocket.send_json(
            {
                "evento": "CONEXION_ESTABLECIDA",
                "id_vehiculo": id_vehiculo,
                "estado": estado_inicial,
            }
        )

        while True:
            data = await websocket.receive_json()
            # Si el mensaje solicita ejecutar una DEMO
            if "id_demo" in data:
                await vehiculo_service.ejecutar_secuencia_demo(int(data["id_demo"]))
            # Si el mensaje solicita ejecutar un movimiento individual
            elif "id_comando" in data:
                origen = str(data.get("origen", "WEBSOCKET"))
                await vehiculo_service.ejecutar_movimiento_individual(
                    id_vehiculo=id_vehiculo,
                    id_comando=int(data["id_comando"]),
                    origen=origen,
                )
            else:
                await websocket.send_json(
                    {
                        "evento": "PING",
                        "id_vehiculo": id_vehiculo,
                        "estado": iot_repository.obtener_estado(id_vehiculo),
                    }
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(id_vehiculo, websocket)
        if not ws_manager.has_connections(id_vehiculo):
            estado_prev = iot_repository.obtener_estado(id_vehiculo)
            ult_cmd = estado_prev.get("id_comando") if estado_prev else None
            iot_repository.actualizar_estado(
                id_vehiculo=id_vehiculo, id_comando=ult_cmd, conectado=False
            )
