"""
Repositorio POO que encapsula la invocación exacta de los 21 Stored Procedures
alojados en Amazon RDS for MySQL (esquema vehiculo_iot).
"""
from typing import Any, Dict, List, Optional
from app.database import DatabaseConnection, db_manager


class IoTRepository:
    """Repositorio de datos que mapea 1 a 1 los 21 Stored Procedures de vehiculo_iot."""

    def __init__(self, db: DatabaseConnection = db_manager) -> None:
        self.db = db

    # ==========================================================================
    # GRUPO 1: VEHÍCULOS (SPs 1 al 5)
    # ==========================================================================
    def crear_vehiculo(
        self,
        nombre: str,
        modelo: Optional[str],
        descripcion: Optional[str],
        microcontrolador: Optional[str],
    ) -> Dict[str, Any]:
        """SP #1: CALL sp_crear_vehiculo(nombre, modelo, descripcion, microcontrolador)"""
        res = self.db.call_procedure(
            "sp_crear_vehiculo", (nombre, modelo, descripcion, microcontrolador)
        )
        return res[0] if res else {"mensaje": "Vehículo creado"}

    def obtener_vehiculos(self) -> List[Dict[str, Any]]:
        """SP #2: CALL sp_obtener_vehiculos()"""
        return self.db.call_procedure("sp_obtener_vehiculos")

    def obtener_vehiculo(self, id_vehiculo: int) -> Optional[Dict[str, Any]]:
        """SP #3: CALL sp_obtener_vehiculo(id_vehiculo)"""
        res = self.db.call_procedure("sp_obtener_vehiculo", (id_vehiculo,))
        return res[0] if res else None

    def actualizar_vehiculo(
        self,
        id_vehiculo: int,
        nombre: str,
        modelo: Optional[str],
        descripcion: Optional[str],
        microcontrolador: Optional[str],
        activo: bool,
    ) -> Dict[str, Any]:
        """SP #4: CALL sp_actualizar_vehiculo(...)"""
        self.db.call_procedure(
            "sp_actualizar_vehiculo",
            (id_vehiculo, nombre, modelo, descripcion, microcontrolador, int(activo)),
        )
        return {"id_vehiculo": id_vehiculo, "actualizado": True}

    def eliminar_vehiculo(self, id_vehiculo: int) -> Dict[str, Any]:
        """SP #5: CALL sp_eliminar_vehiculo(id_vehiculo)"""
        self.db.call_procedure("sp_eliminar_vehiculo", (id_vehiculo,))
        return {"id_vehiculo": id_vehiculo, "eliminado": True}

    # ==========================================================================
    # GRUPO 2: COMANDOS (SPs 6 al 10)
    # ==========================================================================
    def crear_comando(
        self,
        id_vehiculo: int,
        nombre: str,
        codigo: int,
        descripcion: Optional[str],
    ) -> Dict[str, Any]:
        """SP #6: CALL sp_crear_comando(id_vehiculo, nombre, codigo, descripcion)"""
        res = self.db.call_procedure(
            "sp_crear_comando", (id_vehiculo, nombre, codigo, descripcion)
        )
        return res[0] if res else {"mensaje": "Comando creado"}

    def obtener_comandos_vehiculo(self, id_vehiculo: int) -> List[Dict[str, Any]]:
        """SP #7: CALL sp_obtener_comandos_vehiculo(id_vehiculo)"""
        return self.db.call_procedure("sp_obtener_comandos_vehiculo", (id_vehiculo,))

    def obtener_comando(self, id_comando: int) -> Optional[Dict[str, Any]]:
        """SP #8 (SP #20 agregado): CALL sp_obtener_comando(id_comando)"""
        res = self.db.call_procedure("sp_obtener_comando", (id_comando,))
        return res[0] if res else None

    def actualizar_comando(
        self,
        id_comando: int,
        nombre: str,
        codigo: int,
        descripcion: Optional[str],
        activo: bool,
    ) -> Dict[str, Any]:
        """SP #9: CALL sp_actualizar_comando(id_comando, nombre, codigo, descripcion, activo)"""
        self.db.call_procedure(
            "sp_actualizar_comando",
            (id_comando, nombre, codigo, descripcion, int(activo)),
        )
        return {"id_comando": id_comando, "actualizado": True}

    def eliminar_comando(self, id_comando: int) -> Dict[str, Any]:
        """SP #10: CALL sp_eliminar_comando(id_comando)"""
        self.db.call_procedure("sp_eliminar_comando", (id_comando,))
        return {"id_comando": id_comando, "eliminado": True}

    # ==========================================================================
    # GRUPO 3: ESTADO DEL VEHÍCULO (SPs 11 y 12)
    # ==========================================================================
    def actualizar_estado(
        self, id_vehiculo: int, id_comando: Optional[int], conectado: bool
    ) -> Dict[str, Any]:
        """SP #11: CALL sp_actualizar_estado(id_vehiculo, id_comando, conectado)"""
        self.db.call_procedure(
            "sp_actualizar_estado", (id_vehiculo, id_comando, int(conectado))
        )
        return {
            "id_vehiculo": id_vehiculo,
            "id_comando": id_comando,
            "conectado": conectado,
            "estado_actualizado": True,
        }

    def obtener_estado(self, id_vehiculo: int) -> Optional[Dict[str, Any]]:
        """SP #12: CALL sp_obtener_estado(id_vehiculo)"""
        res = self.db.call_procedure("sp_obtener_estado", (id_vehiculo,))
        return res[0] if res else None

    # ==========================================================================
    # GRUPO 4: HISTORIAL DE COMANDOS (SPs 13 y 14)
    # ==========================================================================
    def registrar_historial(
        self, id_vehiculo: int, id_comando: int, origen: str
    ) -> Dict[str, Any]:
        """SP #13: CALL sp_registrar_historial(id_vehiculo, id_comando, origen)"""
        res = self.db.call_procedure(
            "sp_registrar_historial", (id_vehiculo, id_comando, origen)
        )
        return (
            res[0]
            if res
            else {
                "id_vehiculo": id_vehiculo,
                "id_comando": id_comando,
                "origen": origen,
                "registrado": True,
            }
        )

    def obtener_historial(self, id_vehiculo: int) -> List[Dict[str, Any]]:
        """SP #14: CALL sp_obtener_historial(id_vehiculo)"""
        return self.db.call_procedure("sp_obtener_historial", (id_vehiculo,))

    # ==========================================================================
    # GRUPO 5: DEMOS (SPs 15 al 19)
    # ==========================================================================
    def crear_demo(
        self, id_vehiculo: int, nombre: str, descripcion: Optional[str]
    ) -> Dict[str, Any]:
        """SP #15: CALL sp_crear_demo(id_vehiculo, nombre, descripcion)"""
        res = self.db.call_procedure(
            "sp_crear_demo", (id_vehiculo, nombre, descripcion)
        )
        return res[0] if res else {"mensaje": "Demo creada"}

    def obtener_demos(self, id_vehiculo: int) -> List[Dict[str, Any]]:
        """SP #16: CALL sp_obtener_demos(id_vehiculo)"""
        return self.db.call_procedure("sp_obtener_demos", (id_vehiculo,))

    def obtener_demo(self, id_demo: int) -> Optional[Dict[str, Any]]:
        """SP #17 (SP #21 agregado): CALL sp_obtener_demo(id_demo)"""
        res = self.db.call_procedure("sp_obtener_demo", (id_demo,))
        return res[0] if res else None

    def actualizar_demo(
        self,
        id_demo: int,
        nombre: str,
        descripcion: Optional[str],
        activo: bool,
    ) -> Dict[str, Any]:
        """SP #18: CALL sp_actualizar_demo(id_demo, nombre, descripcion, activo)"""
        self.db.call_procedure(
            "sp_actualizar_demo", (id_demo, nombre, descripcion, int(activo))
        )
        return {"id_demo": id_demo, "actualizado": True}

    def eliminar_demo(self, id_demo: int) -> Dict[str, Any]:
        """SP #19: CALL sp_eliminar_demo(id_demo)"""
        self.db.call_procedure("sp_eliminar_demo", (id_demo,))
        return {"id_demo": id_demo, "eliminado": True}

    # ==========================================================================
    # GRUPO 6: MOVIMIENTOS DE DEMO (SPs 20 y 21 del total de 21 SPs)
    # ==========================================================================
    def agregar_movimiento_demo(
        self,
        id_demo: int,
        id_comando: int,
        orden: int,
        duracion_ms: int,
        pausa_ms: int,
    ) -> Dict[str, Any]:
        """SP #20: CALL sp_agregar_movimiento_demo(id_demo, id_comando, orden, duracion_ms, pausa_ms)"""
        res = self.db.call_procedure(
            "sp_agregar_movimiento_demo",
            (id_demo, id_comando, orden, duracion_ms, pausa_ms),
        )
        return res[0] if res else {"mensaje": "Movimiento agregado a demo"}

    def obtener_movimientos_demo(self, id_demo: int) -> List[Dict[str, Any]]:
        """SP #21: CALL sp_obtener_movimientos_demo(id_demo)"""
        return self.db.call_procedure("sp_obtener_movimientos_demo", (id_demo,))

    def actualizar_movimiento_demo(
        self,
        id_demo_movimiento: int,
        id_comando: int,
        orden: int,
        duracion_ms: int,
        pausa_ms: int,
    ) -> Dict[str, Any]:
        """SP #22: CALL sp_actualizar_movimiento_demo(...)"""
        self.db.call_procedure(
            "sp_actualizar_movimiento_demo",
            (id_demo_movimiento, id_comando, orden, duracion_ms, pausa_ms),
        )
        return {"id_demo_movimiento": id_demo_movimiento, "actualizado": True}

    def eliminar_movimiento_demo(self, id_demo_movimiento: int) -> Dict[str, Any]:
        """SP #23: CALL sp_eliminar_movimiento_demo(id_demo_movimiento)"""
        self.db.call_procedure(
            "sp_eliminar_movimiento_demo", (id_demo_movimiento,)
        )
        return {"id_demo_movimiento": id_demo_movimiento, "eliminado": True}


iot_repository = IoTRepository()
