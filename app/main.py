"""
Punto de entrada principal de la API FastAPI y servidor WebSocket (Práctica 2.5 y 2.6).
Expone:
- Los 21 Stored Procedures en endpoints RESTful organizados por entidad.
- Endpoints de Reglas de Negocio (Movimiento Individual CON historial y DEMO SIN historial).
- Endpoint WebSocket en tiempo real: /ws y /ws/{id_vehiculo}
- Sirve también la interfaz de control en http://127.0.0.1:8000/control/
"""
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
from app.routers.auth import router as auth_router, validar_reglas_bola_idor
from app.routers.admin_router import router as admin_router

app = FastAPI(
    title="API Vehículo IoT - Amazon RDS & WebSocket",
    description="Arquitectura POO con 21 Stored Procedures en Amazon RDS, WebSocket por vehículo, Login Real y Seguridad BOLA/IDOR.",
    version="4.4.0",
)

# Habilitar CORS explícito para GitHub Pages y AWS EC2 con allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://brendah18.github.io",
        "https://52.4.170.82:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Routers de Autenticación Real y Administración RBAC
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/", tags=["Health Check"])
def root() -> Dict[str, Any]:
    """Verifica que el servidor FastAPI esté en línea."""
    return {
        "status": "online",
        "servicio": "API Vehículo IoT con Amazon RDS y WebSocket",
        "total_sp_soportados": 21,
    }


@app.get("/api/health/db", tags=["Health Check"])
def health_db() -> Dict[str, Any]:
    """Verifica la conexión real hacia la base de datos MySQL / Amazon RDS."""
    try:
        vehiculos = iot_repository.obtener_vehiculos()
        return {"status": "online", "rds_status": "online", "vehiculos_registrados": len(vehiculos)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RDS no disponible: {exc}") from exc


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
    try:
        return iot_repository.obtener_vehiculos()
    except Exception:
        # Si la base de datos aún no responde, devolvemos vehículo por defecto para no bloquear el ping de la API
        return [{"id_vehiculo": 1, "nombre": "Excavadora IoT", "modelo": "Modelo X", "activo": 1}]


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
@app.get("/api/comandos", tags=["2. Comandos"], summary="Catálogo de comandos por vehículo")
def api_listar_comandos_query(id_vehiculo: int = Query(1)) -> List[Dict[str, Any]]:
    """GET /api/comandos?id_vehiculo=1 -> CALL sp_obtener_comandos_vehiculo(id_vehiculo)"""
    try:
        vehiculo_service.asegurar_catalogo_11_comandos(id_vehiculo)
        return iot_repository.obtener_comandos_vehiculo(id_vehiculo)
    except Exception:
        return []


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
    vehiculo_service.asegurar_catalogo_11_comandos(id_vehiculo)
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
@app.get("/api/demos", tags=["5. Demos"], summary="Catálogo de demos por vehículo")
def api_listar_demos_query(id_vehiculo: int = Query(1)) -> List[Dict[str, Any]]:
    """GET /api/demos?id_vehiculo=1 -> CALL sp_obtener_demos(id_vehiculo)"""
    try:
        return iot_repository.obtener_demos(id_vehiculo)
    except Exception:
        return []


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
    "/api/movimientos",
    tags=["7. Reglas de Negocio IoT"],
    summary="Alias Frontend: Ejecutar movimiento individual (CON Historial + WebSocket)",
)
@app.post(
    "/api/control/movimiento",
    tags=["7. Reglas de Negocio IoT"],
    summary="Regla 1: Ejecutar movimiento individual (CON Historial + WebSocket + BOLA/IDOR)",
)
async def api_ejecutar_movimiento_individual(
    body: EjecutarMovimientoRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    Ejecuta un movimiento manual/individual de los 12 movimientos oficiales (+ 13 DETENER):
    - Validación estricta de seguridad RBAC y BOLA/IDOR:
      * ADMINISTRADOR: No puede mover unidades ya vendidas a un cliente.
      * USUARIO (Comprador): Solo opera sus unidades asignadas (acceso a los 12 movimientos + DETENER).
      * INVITADO: Solo puede ejecutar 01-ADELANTE (1), 02-ATRÁS (2) y DETENER (13) por 5 min.
    - Actualiza `estado_vehiculo` (`sp_actualizar_estado`).
    - SÍ registra en `historial_comandos` (`sp_registrar_historial`).
    - Notifica en tiempo real por WebSocket a `/ws` y `/ws/{id_vehiculo}`.
    """
    es_paro = "DETENER" in str(body.origen or "").upper() or body.id_comando == 13
    validar_reglas_bola_idor(
        token=authorization,
        origen=body.origen,
        id_vehiculo=body.id_vehiculo,
        id_comando=body.id_comando,
        es_demo=False,
        es_detener_prioritario=es_paro,
    )

    return await vehiculo_service.ejecutar_movimiento_individual(
        body.id_vehiculo, body.id_comando, body.origen
    )


@app.post(
    "/api/control/claxon",
    tags=["7. Reglas de Negocio IoT"],
    summary="Emitir sonido de claxon en el vehículo",
)
async def api_control_claxon(body: Dict[str, Any]) -> Dict[str, Any]:
    """Emite evento de claxon y actualiza estado si aplica."""
    id_vehiculo = int(body.get("id_vehiculo", 1))
    await ws_manager.broadcast_to_vehiculo(
        id_vehiculo,
        {
            "evento": "CLAXON",
            "id_vehiculo": id_vehiculo,
            "mensaje": "Bocina activada en el vehículo",
        },
    )
    return {"status": "ok", "accion": "CLAXON", "id_vehiculo": id_vehiculo}


@app.post(
    "/api/control/volumen",
    tags=["7. Reglas de Negocio IoT"],
    summary="Ajustar nivel de volumen del hardware",
)
async def api_control_volumen(body: Dict[str, Any]) -> Dict[str, Any]:
    """Ajusta nivel de volumen y lo transmite por WebSocket."""
    id_vehiculo = int(body.get("id_vehiculo", 1))
    volumen = int(body.get("volumen", 70))
    await ws_manager.broadcast_to_vehiculo(
        id_vehiculo,
        {
            "evento": "VOLUMEN_ACTUALIZADO",
            "id_vehiculo": id_vehiculo,
            "volumen": volumen,
        },
    )
    return {"status": "ok", "volumen": volumen, "id_vehiculo": id_vehiculo}


@app.post(
    "/api/control/velocidad",
    tags=["7. Reglas de Negocio IoT"],
    summary="Ajustar nivel de velocidad de los motores",
)
async def api_control_velocidad(body: Dict[str, Any]) -> Dict[str, Any]:
    """Ajusta porcentaje de velocidad del vehículo."""
    id_vehiculo = int(body.get("id_vehiculo", 1))
    velocidad = int(body.get("velocidad", 70))
    await ws_manager.broadcast_to_vehiculo(
        id_vehiculo,
        {
            "evento": "VELOCIDAD_ACTUALIZADA",
            "id_vehiculo": id_vehiculo,
            "velocidad": velocidad,
        },
    )
    return {"status": "ok", "velocidad": velocidad, "id_vehiculo": id_vehiculo}


@app.post(
    "/api/demos/iniciar",
    tags=["7. Reglas de Negocio IoT"],
    summary="Alias Frontend: Iniciar DEMO temporizada (SIN Historial + WebSocket)",
)
async def api_iniciar_demo_body(
    body: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """Inicia la DEMO recibiendo `{"id_demo": 1, "id_vehiculo": 1}` con protección de concurrencia (409 Conflict)."""
    id_demo = int(body.get("id_demo", 1))
    id_vehiculo = int(body.get("id_vehiculo", 1))
    origen = str(body.get("origen", "WEB-USUARIO"))
    validar_reglas_bola_idor(
        token=authorization,
        origen=origen,
        id_vehiculo=id_vehiculo,
        es_demo=True,
    )
    return await vehiculo_service.ejecutar_secuencia_demo(id_demo)


@app.post(
    "/api/control/demos/{id_demo}/ejecutar",
    tags=["7. Reglas de Negocio IoT"],
    summary="Regla 2: Ejecutar DEMO temporizada (SIN Historial + WebSocket)",
)
async def api_ejecutar_demo(
    id_demo: int,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    Ejecuta la secuencia completa de una DEMO respetando `duracion_ms` y `pausa_ms`:
    - Rechaza con 409 Conflict si ya hay una DEMO en ejecución.
    - Actualiza `estado_vehiculo` en cada paso (`sp_actualizar_estado`).
    - NO registra en `historial_comandos` (prohibido contaminar el historial durante la DEMO).
    - Emite cada paso en tiempo real por WebSocket y envía DETENER automáticamente al finalizar.
    """
    validar_reglas_bola_idor(
        token=authorization,
        origen="SWAGGER-DEMO",
        id_vehiculo=1,
        es_demo=True,
    )
    return await vehiculo_service.ejecutar_secuencia_demo(id_demo)


@app.post(
    "/api/demos/cancelar",
    tags=["7. Reglas de Negocio IoT"],
    summary="Cancelar DEMO en ejecución inmediatamente y enviar DETENER",
)
async def api_cancelar_demo(body: Dict[str, Any]) -> Dict[str, Any]:
    """Aborta en esa milésima de segundo la tarea asíncrona de la DEMO y envía DETENER."""
    id_vehiculo = int(body.get("id_vehiculo", 1))
    return await vehiculo_service.cancelar_demo_activa(
        id_vehiculo=id_vehiculo, origen="CANCELAR-DEMO"
    )


# ==============================================================================
# SECCIÓN 8: SERVIDOR WEBSOCKET (/ws y /ws/{id_vehiculo})
# ==============================================================================
@app.websocket("/ws")
async def websocket_default_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> None:
    """Ruta WebSocket base (`wss://52.4.170.82:8000/ws`) para el vehículo por defecto (ID 1)."""
    await websocket_vehiculo_endpoint(websocket, id_vehiculo=1, token=token)


@app.websocket("/ws/{id_vehiculo}")
async def websocket_vehiculo_endpoint(
    websocket: WebSocket,
    id_vehiculo: int,
    token: Optional[str] = Query(None),
) -> None:
    """
    Canal WebSocket en tiempo real exclusivo por vehículo (`wss://52.4.170.82:8000/ws/1`).
    Acepta conexiones tanto de usuarios autenticados (?token=tk_...) como del hardware
    ESP8266/ESP32 (?token=ESP8266_DEVICE o sin token en modo escucha).
    """
    await ws_manager.connect(id_vehiculo, websocket)
    try:
        try:
            estado_inicial = iot_repository.obtener_estado(id_vehiculo)
        except Exception:
            estado_inicial = {"id_vehiculo": id_vehiculo, "comando": "DETENER", "codigo": 13, "conectado": 1}

        await websocket.send_json(
            jsonable_encoder(
                {
                    "evento": "CONEXION_ESTABLECIDA",
                    "id_vehiculo": id_vehiculo,
                    "estado": estado_inicial,
                }
            )
        )

        while True:
            data = await websocket.receive_json()
            accion_ws = str(data.get("accion", "")).upper()
            token_ws = data.get("token") or token
            origen_ws = str(data.get("origen", "WEBSOCKET"))

            if accion_ws == "CANCELAR_DEMO":
                await vehiculo_service.cancelar_demo_activa(id_vehiculo=id_vehiculo, origen="WSS-CANCELAR-DEMO")
            elif "id_demo" in data:
                try:
                    validar_reglas_bola_idor(
                        token=token_ws,
                        origen=origen_ws,
                        id_vehiculo=id_vehiculo,
                        es_demo=True,
                    )
                    if not vehiculo_service.is_demo_running(id_vehiculo):
                        asyncio.create_task(vehiculo_service.ejecutar_secuencia_demo(int(data["id_demo"])))
                except HTTPException as exc:
                    await websocket.send_json(
                        {"evento": "ERROR_RBAC", "id_vehiculo": id_vehiculo, "mensaje": exc.detail}
                    )
            elif "id_comando" in data or "codigo" in data:
                id_cmd = int(data.get("id_comando") or data.get("codigo"))
                es_paro = id_cmd in (13, 9) or "DETENER" in origen_ws.upper()
                try:
                    validar_reglas_bola_idor(
                        token=token_ws,
                        origen=origen_ws,
                        id_vehiculo=id_vehiculo,
                        id_comando=id_cmd,
                        es_demo=False,
                        es_detener_prioritario=es_paro,
                    )
                    await vehiculo_service.ejecutar_movimiento_individual(
                        id_vehiculo=id_vehiculo,
                        id_comando=id_cmd,
                        origen=origen_ws,
                    )
                except HTTPException as exc:
                    await websocket.send_json(
                        {"evento": "ERROR_RBAC", "id_vehiculo": id_vehiculo, "mensaje": exc.detail}
                    )
            else:
                await websocket.send_json(
                    {
                        "evento": "PING",
                        "id_vehiculo": id_vehiculo,
                    }
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(id_vehiculo, websocket)
        if not ws_manager.has_connections(id_vehiculo):
            try:
                estado_prev = iot_repository.obtener_estado(id_vehiculo)
                ult_cmd = estado_prev.get("id_comando") if estado_prev else None
                iot_repository.actualizar_estado(
                    id_vehiculo=id_vehiculo, id_comando=ult_cmd, conectado=False
                )
            except Exception:
                pass


# Montar el frontend en /control para evitar bloqueo CORS por protocolo file:///
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend_control"
if FRONTEND_DIR.exists():
    app.mount("/control", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend_control")
