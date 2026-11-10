# Proyecto Integrador IoT: Amazon RDS (21 Stored Procedures) + FastAPI POO + WebSocket

Arquitectura modular orientada a objetos (POO) para el control y monitoreo en tiempo real de vehículos IoT (`ESP8266` / `ESP32`) respaldada por **Amazon RDS for MySQL** y **WebSockets** (`WS`/`WSS`).

## Estructura del Proyecto (`websocket_iot` / `vehiculo_iot_api`)

```text
websocket_iot/
├── .venv/
├── .env                  <-- Credenciales de RDS (IGNORADO EN GIT)
├── .env.example          <-- Plantilla sin contraseñas para GitHub
├── .gitignore
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py
    ├── main.py           <-- Punto de entrada FastAPI (21 APIs + Control + WebSocket)
    ├── config.py         <-- Lectura de variables de entorno (POO)
    ├── database.py       <-- Conexión segura a Amazon RDS (POO)
    ├── models/           <-- Esquemas Pydantic
    │   ├── __init__.py
    │   └── schemas.py
    ├── repositories/     <-- Ejecución de los 21 Stored Procedures
    │   ├── __init__.py
    │   └── iot_repository.py
    ├── services/         <-- Lógica de negocio (Movimientos CON historial, DEMO SIN historial)
    │   ├── __init__.py
    │   └── vehiculo_service.py
    └── websocket/        <-- Gestor WebSocket por vehículo
        ├── __init__.py
        └── websocket_manager.py
```

## Ejecución Local / EC2

1. Activar entorno virtual e instalar dependencias:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Configurar `.env` con el Endpoint de `Instancia-RDS-IoT`.
3. Iniciar servidor FastAPI (HTTP + WS):
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Documentación interactiva Swagger UI:
   - `http://localhost:8000/docs`
