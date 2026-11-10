"""
Capa de Servicios POO (FASE 3: Reglas de Negocio Críticas).
Implementa:
1. Movimiento individual CON registro en historial_comandos, actualización en
   estado_vehiculo y emisión inmediata por WebSocket.
2. Secuencia DEMO temporizada (duracion_ms y pausa_ms) SIN contaminar
   la tabla historial_comandos, actualizando estado_vehiculo en cada paso y
   notificando por WebSocket en tiempo real.
"""
import asyncio
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from app.repositories.iot_repository import IoTRepository, iot_repository
from app.websocket.websocket_manager import WebSocketManager, ws_manager


class VehiculoService:
    """Clase POO que orquesta las reglas de negocio del vehículo IoT."""

    def __init__(
        self,
        repo: IoTRepository = iot_repository,
        ws: WebSocketManager = ws_manager,
    ) -> None:
        self.repo = repo
        self.ws = ws

    def _buscar_comando_detener(self, id_vehiculo: int) -> Optional[Dict[str, Any]]:
        """Busca el comando DETENER (o código 9) del vehículo para las pausas y fin de DEMO."""
        comandos = self.repo.obtener_comandos_vehiculo(id_vehiculo)
        for cmd in comandos:
            if str(cmd.get("nombre", "")).upper() == "DETENER" or cmd.get("codigo") == 9:
                return cmd
        return None

    async def ejecutar_movimiento_individual(
        self, id_vehiculo: int, id_comando: int, origen: str = "MANUAL"
    ) -> Dict[str, Any]:
        """
        REGLA DE NEGOCIO 1 (Movimiento Individual CON Historial):
        1. Actualiza el estado actual del vehículo en RDS (sp_actualizar_estado).
        2. SÍ registra el movimiento en el historial de RDS (sp_registrar_historial).
        3. Consulta el estado enriquecido (sp_obtener_estado) y lo transmite por WebSocket.
        """
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
        estado_actual = self.repo.obtener_estado(id_vehiculo)
        payload = {
            "evento": "MOVIMIENTO_INDIVIDUAL",
            "guardado_en_historial": True,
            "origen": origen,
            "estado": estado_actual,
        }
        await self.ws.broadcast_to_vehiculo(id_vehiculo, payload)
        return payload

    async def ejecutar_secuencia_demo(self, id_demo: int) -> Dict[str, Any]:
        """
        REGLA DE NEGOCIO 2 (DEMO Temporizada SIN Historial):
        1. Obtiene la demo y sus movimientos ordenados desde RDS (sp_obtener_movimientos_demo).
        2. Recorre cada paso respetando `duracion_ms` y `pausa_ms` con asyncio.sleep().
        3. En cada paso actualiza `estado_vehiculo` (sp_actualizar_estado) y emite por WebSocket.
        4. PROHIBIDO llamar a `sp_registrar_historial` durante la DEMO (no ensucia el historial).
        """
        movimientos: List[Dict[str, Any]] = self.repo.obtener_movimientos_demo(id_demo)
        if not movimientos:
            raise HTTPException(
                status_code=404,
                detail=f"La demo {id_demo} no existe o no tiene movimientos asignados",
            )

        # Determinar id_vehiculo a partir de la demo o del primer comando
        demo_info = self.repo.obtener_demo(id_demo)
        if demo_info:
            id_vehiculo = int(demo_info["id_vehiculo"])
        else:
            primer_cmd = self.repo.obtener_comando(int(movimientos[0]["id_comando"]))
            id_vehiculo = int(primer_cmd["id_vehiculo"]) if primer_cmd else 1

        cmd_detener = self._buscar_comando_detener(id_vehiculo)
        pasos_ejecutados: List[Dict[str, Any]] = []

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

        for paso in movimientos:
            id_comando = int(paso["id_comando"])
            orden = int(paso["orden"])
            duracion_ms = int(paso["duracion_ms"])
            pausa_ms = int(paso["pausa_ms"])

            # A) Actualizar estado del vehículo con el movimiento del paso (SIN HISTORIAL)
            self.repo.actualizar_estado(
                id_vehiculo=id_vehiculo, id_comando=id_comando, conectado=True
            )
            estado_paso = self.repo.obtener_estado(id_vehiculo)

            await self.ws.broadcast_to_vehiculo(
                id_vehiculo,
                {
                    "evento": "DEMO_PASO",
                    "id_demo": id_demo,
                    "orden": orden,
                    "comando": paso.get("comando"),
                    "codigo": paso.get("codigo"),
                    "duracion_ms": duracion_ms,
                    "pausa_ms": pausa_ms,
                    "guardado_en_historial": False,
                    "estado": estado_paso,
                },
            )

            # B) Esperar duración exacta del movimiento en segundos
            if duracion_ms > 0:
                await asyncio.sleep(duracion_ms / 1000.0)

            # C) Si hay pausa entre movimientos, poner en DETENER durante pausa_ms (SIN HISTORIAL)
            if pausa_ms > 0:
                if cmd_detener:
                    self.repo.actualizar_estado(
                        id_vehiculo=id_vehiculo,
                        id_comando=int(cmd_detener["id_comando"]),
                        conectado=True,
                    )
                    estado_pausa = self.repo.obtener_estado(id_vehiculo)
                    await self.ws.broadcast_to_vehiculo(
                        id_vehiculo,
                        {
                            "evento": "DEMO_PAUSA",
                            "id_demo": id_demo,
                            "orden": orden,
                            "pausa_ms": pausa_ms,
                            "guardado_en_historial": False,
                            "estado": estado_pausa,
                        },
                    )
                await asyncio.sleep(pausa_ms / 1000.0)

            pasos_ejecutados.append(
                {
                    "orden": orden,
                    "id_comando": id_comando,
                    "comando": paso.get("comando"),
                    "duracion_ms": duracion_ms,
                    "pausa_ms": pausa_ms,
                }
            )

        # Al concluir la secuencia, asegurar estado final DETENER (SIN HISTORIAL)
        if cmd_detener:
            self.repo.actualizar_estado(
                id_vehiculo=id_vehiculo,
                id_comando=int(cmd_detener["id_comando"]),
                conectado=True,
            )

        estado_final = self.repo.obtener_estado(id_vehiculo)
        resumen = {
            "evento": "DEMO_FINALIZADA",
            "id_demo": id_demo,
            "id_vehiculo": id_vehiculo,
            "guardado_en_historial": False,
            "pasos_ejecutados": pasos_ejecutados,
            "estado_final": estado_final,
        }
        await self.ws.broadcast_to_vehiculo(id_vehiculo, resumen)
        return resumen


vehiculo_service = VehiculoService()
