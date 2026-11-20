"""
Módulo de gestión de conexión a base de datos Amazon RDS for MySQL aplicando POO.
Permite invocar Stored Procedures devolviendo diccionarios compatibles con Pydantic, FastAPI y WebSockets.
"""
from datetime import date, datetime
from decimal import Decimal
import os
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# 1. Cargar variables de entorno desde el archivo .env al inicio
load_dotenv()


class DatabaseConnection:
    """Clase POO que administra la conexión segura hacia Amazon RDS for MySQL."""

    def __init__(self) -> None:
        self.host: str = os.getenv("DB_HOST", "localhost")
        # 2. Conversión explícita de DB_PORT a entero (int)
        self.port: int = int(os.getenv("DB_PORT", 3306))
        self.user: str = os.getenv("DB_USER", "admin")
        self.password: str = os.getenv("DB_PASSWORD", "Admin1234#")
        self.database: str = os.getenv("DB_NAME", "vehiculo_iot")

    def get_connection(self):
        """
        Crea y retorna una conexión activa a MySQL en Amazon RDS.
        Garantiza que el parámetro port se pase explícitamente como int.
        """
        try:
            host = os.getenv("DB_HOST", self.host)
            port = int(os.getenv("DB_PORT", 3306))
            user = os.getenv("DB_USER", self.user)
            password = os.getenv("DB_PASSWORD", self.password)
            database = os.getenv("DB_NAME", self.database)

            # 3. mysql.connector.connect() recibe port como entero (int)
            connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                autocommit=True,
            )
            return connection
        except Error as exc:
            raise RuntimeError(f"Error de conexión a Amazon RDS: {exc}") from exc

    @staticmethod
    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte objetos datetime/date/Decimal a tipos nativos serializables en JSON (para WebSocket)."""
        clean: Dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, (datetime, date)):
                clean[key] = value.isoformat()
            elif isinstance(value, Decimal):
                clean[key] = float(value)
            else:
                clean[key] = value
        return clean

    def call_procedure(
        self, sp_name: str, params: Tuple[Any, ...] = ()
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta un Stored Procedure en MySQL/RDS (ej. sp_obtener_vehiculos) usando CALL
        y retorna las filas en formato de diccionario (dictionary=True) serializable en JSON.
        """
        connection = self.get_connection()
        # 4. Configurar el cursor con dictionary=True para respuestas compatibles con Pydantic y FastAPI
        cursor = connection.cursor(dictionary=True)
        resultados: List[Dict[str, Any]] = []
        try:
            cursor.callproc(sp_name, params)
            for result in cursor.stored_results():
                filas = result.fetchall()
                if filas:
                    resultados.extend(self._serialize_row(f) for f in filas)
            connection.commit()
            return resultados
        except Error as exc:
            connection.rollback()
            raise RuntimeError(f"Error al ejecutar SP '{sp_name}': {exc}") from exc
        finally:
            cursor.close()
            connection.close()

    def execute_query(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> List[Dict[str, Any]]:
        """Ejecuta una consulta SQL segura (SELECT, INSERT, UPDATE) retornando diccionarios."""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if cursor.description:
                filas = cursor.fetchall()
                connection.commit()
                return [self._serialize_row(f) for f in filas] if filas else []
            connection.commit()
            return [{"affected_rows": cursor.rowcount, "last_id": cursor.lastrowid}]
        except Error as exc:
            connection.rollback()
            raise RuntimeError(f"Error al ejecutar query: {exc}") from exc
        finally:
            cursor.close()
            connection.close()


# Función auxiliar directa en caso de importación funcional en otros módulos
def get_connection():
    """Retorna una nueva conexión a Amazon RDS con DB_PORT convertido a int."""
    return db_manager.get_connection()


db_manager = DatabaseConnection()
