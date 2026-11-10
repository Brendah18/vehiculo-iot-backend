"""
Módulo de configuración centralizada (POO).
Lee las variables de entorno desde el archivo .env para conectar con Amazon RDS.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Clase de configuración del sistema IoT y conexión a Amazon RDS."""

    def __init__(self) -> None:
        self.db_host: str = os.getenv("DB_HOST", "localhost")
        self.db_port: int = int(os.getenv("DB_PORT", "3306"))
        self.db_user: str = os.getenv("DB_USER", "admin")
        self.db_password: str = os.getenv("DB_PASSWORD", "Admin1234#")
        self.db_name: str = os.getenv("DB_NAME", "vehiculo_iot")
        self.api_host: str = os.getenv("API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
