"""
Capa de Servicios POO (Reglas de Negocio Críticas + Catálogo Oficial 12 Movimientos + Control DEMO).
Implementa:
1. Catálogo exacto de los 12 movimientos del profesor (01..12) + 13 (DETENER) sin borrar historial.
2. Movimiento individual CON registro en historial_comandos, actualización en
   estado_vehiculo y emisión inmediata por WebSocket.
3. Secuencia DEMO temporizada con cancelación instantánea en memoria (asyncio.Event
   por id_vehiculo), prevención de demos simultáneas (409 Conflict), tiempos mínimos
   visibles (1500 ms movimiento / 800 ms pausa), detención automática al finalizar y
   PROHIBICIÓN de contaminar historial_comandos.
"""
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from app.repositories.iot_repository import IoTRepository, iot_repository
from app.websocket.websocket_manager import WebSocketManager, ws_manager


class VehiculoService:
    """Clase POO que orquesta las reglas de negocio del vehículo IoT."""

    CATALOGO_OFICIAL_12_MAS_DETENER = [
        (1,  1, "ADELANTE",          1,  "01. ADELANTE — desplazamiento físico hacia adelante"),
        (2,  1, "ATRAS",             2,  "02. ATRÁS — desplazamiento físico hacia atrás"),
        (3,  1, "GIRAR_IZQUIERDA",   3,  "03. GIRAR IZQUIERDA — giro a la izquierda"),
        (4,  1, "GIRAR_DERECHA",     4,  "04. GIRAR DERECHA — giro a la derecha"),
        (5,  1, "MOVER_IZQUIERDA",   5,  "05. MOVER IZQUIERDA — desplazamiento lateral izquierda"),
        (6,  1, "MOVER_DERECHA",     6,  "06. MOVER DERECHA — desplazamiento lateral derecha"),
        (7,  1, "SUBIR_BRAZO",       7,  "07. SUBIR BRAZO — elevación del brazo o palanca"),
        (8,  1, "BAJAR_BRAZO",       8,  "08. BAJAR BRAZO — descenso del brazo o palanca"),
        (9,  1, "LUZ_LED",           9,  "09. LUZ / LED — encendido o apagado real de iluminación"),
        (10, 1, "ACTIVAR_SONIDO",    10, "10. ACTIVAR SONIDO — encendido del sonido"),
        (11, 1, "DESACTIVAR_SONIDO", 11, "11. DESACTIVAR SONIDO — apagado del sonido"),
        (12, 1, "CONTROL_REMOTO",    12, "12. CONTROL REMOTO — encendido o apagado de interfaz electrónica segura"),
        (13, 1, "DETENER",           13, "13. DETENER — paro total prioritario inmediato"),
    ]

    def __init__(
        self,
        repo: IoTRepository = iot_repository,
        ws: WebSocketManager = ws_manager,
    ) -> None:
        self.repo = repo
        self.ws = ws
        self._catalogo_sincronizado = False
        # Bandera de cancelación real en memoria por vehículo
        self.active_demo_events: Dict[int, asyncio.Event] = {}
        self.active_demo_ids: Dict[int, int] = {}

    def asegurar_catalogo_12_movimientos(self, id_vehiculo: int = 1) -> None:
        """
        Sincroniza de forma idempotente el catálogo exacto de 12 movimientos + DETENER (13)
        en Amazon RDS sin ejecutar DELETE sobre comandos ni alterar historial_comandos.
        """
        if self._catalogo_sincronizado or id_vehiculo != 1:
            return
        try:
            cmds = self.repo.obtener_comandos_vehiculo(1)
            nombres_actuales = {str(c.get("nombre", "")).upper(): int(c.get("codigo", 0)) for c in cmds if c.get("activo", 1)}
            esperados = {row[2]: row[3] for row in self.CATALOGO_OFICIAL_12_MAS_DETENER}

            if nombres_actuales == esperados:
                self._catalogo_sincronizado = True
                return

            # 1. Reubicar temporalmente códigos y nombres sin DELETE para evitar colisión UNIQUE
            self.repo.db.execute_query(
                "UPDATE comandos SET codigo = id_comando + 1000, nombre = CONCAT('HIST_CMD_', id_comando), activo = 0 WHERE id_vehiculo = 1;"
            )

            # 2. Upsert de los 13 comandos oficiales (01..12 + 13 DETENER)
            q_upsert = """
                INSERT INTO comandos (id_comando, id_vehiculo, nombre, codigo, descripcion, activo)
                VALUES (%s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                  id_vehiculo = VALUES(id_vehiculo),
                  nombre = VALUES(nombre),
                  codigo = VALUES(codigo),
                  descripcion = VALUES(descripcion),
                  activo = 1;
            """
            for row in self.CATALOGO_OFICIAL_12_MAS_DETENER:
                self.repo.db.execute_query(q_upsert, row)

            self._catalogo_sincronizado = True
        except Exception:
            pass

    def asegurar_catalogo_11_comandos(self, id_vehiculo: int = 1) -> None:
        """Alias de compatibilidad."""
        self.asegurar_catalogo_12_movimientos(id_vehiculo)

    def _buscar_comando_detener(self, id_vehiculo: int) -> Dict[str, Any]:
        """Busca el comando DETENER (código 13) del vehículo para pausas, cancelación y fin de DEMO."""
        try:
            comandos = self.repo.obtener_comandos_vehiculo(id_vehiculo)
            for cmd in comandos:
                if str(cmd.get("nombre", "")).upper() == "DETENER":
                    return cmd
        except Exception:
            pass
        return {"id_comando": 13, "id_vehiculo": id_vehiculo, "nombre": "DETENER", "codigo": 13}

    def is_demo_running(self, id_vehiculo: int) -> bool:
        """Indica si el vehículo tiene actualmente una DEMO en ejecución."""
        return id_vehiculo in self.active_demo_events

    async def _sleep_cancelable(self, cancel_event: asyncio.Event, duracion_ms: int) -> bool:
        """
        Espera `duracion_ms` milisegundos, pero se despierta y retorna True en la misma
        milésima de segundo si `cancel_event.set()` es activado por DETENER o Cancelar DEMO.
        """
        if duracion_ms <= 0:
            return cancel_event.is_set()
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=duracion_ms / 1000.0)
            return True  # Se activó la cancelación
        except asyncio.TimeoutError:
            return cancel_event.is_set()

    async def cancelar_demo_activa(self, id_vehiculo: int, origen: str = "CANCELAR-DEMO") -> Dict[str, Any]:
        """
        Aborta inmediatamente cualquier secuencia DEMO en curso sobre `id_vehiculo`
        y envía el comando físico prioritario DETENER al hardware y por WebSocket.
        """
        self.asegurar_catalogo_12_movimientos(id_vehiculo)
        cancel_ev = self.active_demo_events.get(id_vehiculo)
        id_demo_activa = self.active_demo_ids.get(id_vehiculo, 1)

        if cancel_ev:
            cancel_ev.set()

        cmd_detener = self._buscar_comando_detener(id_vehiculo)
        id_cmd_detener = int(cmd_detener["id_comando"])

        # Actualizar estado a DETENER en RDS
        try:
            self.repo.actualizar_estado(
                id_vehiculo=id_vehiculo, id_comando=id_cmd_detener, conectado=True
            )
            estado_detenido = self.repo.obtener_estado(id_vehiculo)
        except Exception:
            estado_detenido = {
                "id_vehiculo": id_vehiculo,
                "vehiculo": "Excavadora IoT",
                "id_comando": id_cmd_detener,
                "comando": "DETENER",
                "codigo": 13,
                "conectado": 1,
            }

        payload_cancel = {
            "evento": "DEMO_FINALIZADA",
            "cancelada": True,
            "id_demo": id_demo_activa,
            "id_vehiculo": id_vehiculo,
            "comando": "DETENER",
            "codigo": 13,
            "origen": origen,
            "guardado_en_historial": False,
            "estado": estado_detenido,
            "estado_final": estado_detenido,
        }
        await self.ws.broadcast_to_vehiculo(id_vehiculo, payload_cancel)
        return payload_cancel

    async def ejecutar_movimiento_individual(
        self, id_vehiculo: int, id_comando: int, origen: str = "MANUAL"
    ) -> Dict[str, Any]:
        """
        REGLA DE NEGOCIO 1 (Movimiento Individual CON Historial):
        - Si se envía DETENER (13 o 9) mientras corre una DEMO, aborta la DEMO de inmediato.
        - Actualiza `estado_vehiculo` en RDS (sp_actualizar_estado).
        - SÍ registra el movimiento en `historial_comandos` (sp_registrar_historial).
        - Transmite el estado enriquecido en tiempo real por WebSocket.
        """
        self.asegurar_catalogo_12_movimientos(id_vehiculo)

        cmd_detener = self._buscar_comando_detener(id_vehiculo)
        id_cmd_detener = int(cmd_detener["id_comando"])

        # Compatibilidad si algún cliente envía código 9 para DETENER cuando DETENER es 13
        if id_comando == 9 and "DETENER" in str(origen or "").upper():
            id_comando = id_cmd_detener

        # Si el comando es DETENER y hay una DEMO corriendo, abortar la DEMO al instante
        if id_comando == id_cmd_detener and id_vehiculo in self.active_demo_events:
            self.active_demo_events[id_vehiculo].set()

        vehiculo = self.repo.obtener_vehiculo(id_vehiculo)
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        # 1. Actualizar estado actual en RDS
        self.repo.actualizar_estado(
            id_vehiculo=id_vehiculo, id_comando=id_comando, conectado=True
        )

        # 2. SÍ registrar en historial_comandos (Regla de Negocio 1)
        self.repo.registrar_historial(
            id_vehiculo=id_vehiculo, id_comando=id_comando, origen=origen
        )

        # 3. Obtener estado actual y emitir por WebSocket al canal del vehículo
        estado_actual = self.repo.obtener_estado(id_vehiculo) or {}
        nombre_cmd = str(estado_actual.get("comando") or "").strip().upper()
        codigo_num = int(estado_actual.get("codigo") or id_comando)

        payload = {
            "evento": "MOVIMIENTO_INDIVIDUAL",
            "guardado_en_historial": True,
            "origen": origen,
            "id_vehiculo": id_vehiculo,
            "id_comando": id_comando,
            "codigo": nombre_cmd,
            "codigo_num": codigo_num,
            "comando": nombre_cmd,
            "accion": nombre_cmd,
            "estado": estado_actual,
        }
        await self.ws.broadcast_to_vehiculo(id_vehiculo, payload)
        return payload

    async def ejecutar_secuencia_demo(self, id_demo: int) -> Dict[str, Any]:
        """
        REGLA DE NEGOCIO 2 (DEMO Temporizada SIN Historial y con Cancelación Instantánea):
        1. Rechaza con 409 Conflict si ya hay una DEMO corriendo en el mismo vehículo.
        2. Recorre cada paso respetando `duracion_ms` (mín 1500 ms) y `pausa_ms` (mín 800 ms)
           mediante espera cancelable `asyncio.Event`.
        3. En cada paso actualiza `estado_vehiculo` y emite por WebSocket SIN escribir en `historial_comandos`.
        4. Al terminar o cancelarse, envía automáticamente `DETENER` y libera el bloqueo del vehículo.
        """
        self.asegurar_catalogo_12_movimientos(1)

        movimientos: List[Dict[str, Any]] = self.repo.obtener_movimientos_demo(id_demo)
        if not movimientos:
            raise HTTPException(
                status_code=404,
                detail=f"La demo {id_demo} no existe o no tiene movimientos asignados",
            )

        demo_info = self.repo.obtener_demo(id_demo)
        if demo_info:
            id_vehiculo = int(demo_info["id_vehiculo"])
        else:
            primer_cmd = self.repo.obtener_comando(int(movimientos[0]["id_comando"]))
            id_vehiculo = int(primer_cmd["id_vehiculo"]) if primer_cmd else 1

        # Prevención estricta de 2 demos simultáneas sobre el mismo vehículo (409 Conflict)
        if id_vehiculo in self.active_demo_events:
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay una secuencia DEMO activa en el vehículo #{id_vehiculo}. Detén o espera a que finalice.",
            )

        cancel_event = asyncio.Event()
        self.active_demo_events[id_vehiculo] = cancel_event
        self.active_demo_ids[id_vehiculo] = id_demo

        cmd_detener = self._buscar_comando_detener(id_vehiculo)
        id_cmd_detener = int(cmd_detener["id_comando"])
        pasos_ejecutados: List[Dict[str, Any]] = []
        fue_cancelada = False

        DURACION_MINIMA_MS = 1500
        PAUSA_MINIMA_MS = 800

        try:
            # Notificar inicio de DEMO por WebSocket
            await self.ws.broadcast_to_vehiculo(
                id_vehiculo,
                {
                    "evento": "DEMO_INICIADA",
                    "id_demo": id_demo,
                    "id_vehiculo": id_vehiculo,
                    "total_pasos": len(movimientos),
                    "guardado_en_historial": False,
                },
            )

            for idx, paso in enumerate(movimientos):
                if cancel_event.is_set():
                    fue_cancelada = True
                    break

                id_comando = int(paso["id_comando"])
                orden = int(paso.get("orden", idx + 1))
                nombre_paso = str(paso.get("comando", "")).upper()
                raw_duracion = int(paso.get("duracion_ms") or 1800)
                raw_pausa = int(paso.get("pausa_ms") or 900)

                duracion_ms = max(raw_duracion, DURACION_MINIMA_MS)
                es_ultimo_paso = (idx == len(movimientos) - 1)
                pausa_ms = 0 if (es_ultimo_paso or nombre_paso == "DETENER") else max(raw_pausa, PAUSA_MINIMA_MS)

                # A) Actualizar estado_vehiculo con el movimiento del paso (SIN HISTORIAL)
                self.repo.actualizar_estado(
                    id_vehiculo=id_vehiculo, id_comando=id_comando, conectado=True
                )
                estado_paso = self.repo.obtener_estado(id_vehiculo) or {}
                cmd_str = str(paso.get("comando") or estado_paso.get("comando") or nombre_paso).strip().upper()
                cod_num = int(paso.get("codigo") or estado_paso.get("codigo") or id_comando)

                await self.ws.broadcast_to_vehiculo(
                    id_vehiculo,
                    {
                        "evento": "DEMO_PASO",
                        "id_demo": id_demo,
                        "id_vehiculo": id_vehiculo,
                        "id_comando": id_comando,
                        "orden": orden,
                        "comando": cmd_str,
                        "codigo": cmd_str,
                        "codigo_num": cod_num,
                        "accion": cmd_str,
                        "duracion_ms": duracion_ms,
                        "pausa_ms": pausa_ms,
                        "guardado_en_historial": False,
                        "estado": estado_paso,
                    },
                )

                # B) Espera cancelable durante la ejecución física del movimiento
                if await self._sleep_cancelable(cancel_event, duracion_ms):
                    fue_cancelada = True
                    break

                # C) Pausa intermedia en DETENER entre pasos (SIN HISTORIAL)
                if pausa_ms > 0 and not cancel_event.is_set():
                    self.repo.actualizar_estado(
                        id_vehiculo=id_vehiculo,
                        id_comando=id_cmd_detener,
                        conectado=True,
                    )
                    estado_pausa = self.repo.obtener_estado(id_vehiculo)
                    await self.ws.broadcast_to_vehiculo(
                        id_vehiculo,
                        {
                            "evento": "DEMO_PAUSA",
                            "id_demo": id_demo,
                            "id_vehiculo": id_vehiculo,
                            "orden": orden,
                            "comando": "DETENER",
                            "codigo": 13,
                            "duracion_ms": 0,
                            "pausa_ms": pausa_ms,
                            "guardado_en_historial": False,
                            "estado": estado_pausa,
                        },
                    )
                    if await self._sleep_cancelable(cancel_event, pausa_ms):
                        fue_cancelada = True
                        break

                pasos_ejecutados.append(
                    {
                        "orden": orden,
                        "id_comando": id_comando,
                        "comando": paso.get("comando"),
                        "codigo": paso.get("codigo"),
                        "duracion_ms": duracion_ms,
                        "pausa_ms": pausa_ms,
                    }
                )

            # Al finalizar o cancelar la DEMO, forzar siempre DETENER (SIN HISTORIAL)
            self.repo.actualizar_estado(
                id_vehiculo=id_vehiculo,
                id_comando=id_cmd_detener,
                conectado=True,
            )
            estado_final = self.repo.obtener_estado(id_vehiculo)

            resumen = {
                "evento": "DEMO_FINALIZADA",
                "cancelada": fue_cancelada,
                "id_demo": id_demo,
                "id_vehiculo": id_vehiculo,
                "comando": "DETENER",
                "codigo": 13,
                "pasos_ejecutados": pasos_ejecutados,
                "guardado_en_historial": False,
                "estado": estado_final,
                "estado_final": estado_final,
            }
            await self.ws.broadcast_to_vehiculo(id_vehiculo, resumen)
            return resumen
        finally:
            self.active_demo_events.pop(id_vehiculo, None)
            self.active_demo_ids.pop(id_vehiculo, None)


vehiculo_service = VehiculoService()
