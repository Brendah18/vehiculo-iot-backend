# 📡 Conexión de Excavadora ESP8266 al WebSocket IoT (AWS EC2 & RDS)

Este documento explica cómo está integrado el microcontrolador **ESP8266 (NodeMCU / D1 Mini)** de la excavadora con el backend FastAPI y el canal WebSocket de `vehiculo_iot_api` / `websocket_iot`.

---

## 1. Archivos del Código Arduino
- **Sketch original actualizado:** `c:\Users\brend\OneDrive\Documentos\10 Semestre\sketch_oct22a\sketch_oct22a.ino`
- **Copia de respaldo en el proyecto:** [sketch_esp8266_excavadora.ino](file:///c:/Users/brend/OneDrive/Documentos/10%20Semestre/vehiculo_iot_api/sketch_esp8266_excavadora.ino)

---

## 2. Ajustes Realizados en el Código Arduino

### A. Extracción Correcta del JSON de FastAPI / WebSocket
El servidor FastAPI envía payloads JSON estructurados de dos formas principales:

1. **Movimiento Manual / Individual (`MOVIMIENTO_INDIVIDUAL`):**
   ```json
   {
     "evento": "MOVIMIENTO_INDIVIDUAL",
     "guardado_en_historial": true,
     "origen": "MANUAL",
     "estado": {
       "id_vehiculo": 1,
       "vehiculo": "Excavadora IoT",
       "id_comando": 1,
       "comando": "AVANZAR",
       "codigo": 1,
       "conectado": 1,
       "fecha_actualizacion": "2026-11-17T05:00:00"
     }
   }
   ```
   *El valor del comando viene dentro de `doc["estado"]["comando"]`.*

2. **Secuencia DEMO Automática (`DEMO_PASO` / `DEMO_PAUSA`):**
   ```json
   {
     "evento": "DEMO_PASO",
     "id_demo": 1,
     "orden": 1,
     "comando": "AVANZAR",
     "codigo": 1,
     "duracion_ms": 2500,
     "pausa_ms": 1200,
     "guardado_en_historial": false
   }
   ```
   *El valor del comando viene en la raíz: `doc["comando"]`.*

El código ahora verifica **ambas estructuras jerárquicas**:
```cpp
if (doc.containsKey("estado") && doc["estado"].containsKey("comando")) {
  movimiento = doc["estado"]["comando"];
} else if (doc.containsKey("comando")) {
  movimiento = doc["comando"];
}
```

### B. Capacidad del Buffer JSON
Se aumentó el buffer de `StaticJsonDocument<200>` a `DynamicJsonDocument doc(1024);`. El payload con metadatos de base de datos supera los 200 bytes, por lo que anteriormente fallaba la deserialización silenciosamente.

### C. Monitor Serie Limpio ("Solamente el movimiento")
- No se imprimen logs de conexión Wi-Fi ni handshakes WebSocket.
- Se ignora el evento `CONEXION_ESTABLECIDA` para no imprimir `DETENER` antes de que el usuario envíe una acción.
- En la consola Serie (115200 baudios) únicamente aparecerá el texto del comando que se va a ejecutar (ej. `AVANZAR`, `RETROCEDER`, `GIRAR_IZQUIERDA`, `GIRAR_DERECHA`, `DETENER`).

### D. Motores Físicos Desactivados
- Se conservan configurados los pines de los motores (`D1`, `D2`, `D5`, `D6`), pero permanecen en estado `LOW`.
- La llamada a `moverExcavadora(...)` se encuentra comentada.
- Cuando desees mover físicamente la excavadora, solo necesitas descomentar la línea indicada en `webSocketEvent` y el bloque dentro de `moverExcavadora`.

---

## 3. Configuración de Red y Conexión WebSocket

| Parámetro | Valor Configurado |
|---|---|
| **SSID Wi-Fi** | `Hulux-MH15022` |
| **Password Wi-Fi** | `PcH4uFuOXfx1` |
| **Servidor Host** | `52.4.170.82` (AWS EC2) |
| **Puerto** | `8000` |
| **Ruta WebSocket** | `/ws/1` |
| **Protocolo** | `wss://` (WebSocket Seguro con `beginSSL`) |

> Si en algún momento pruebas en red local sin SSL (`ws://`), cambia `webSocket.beginSSL(...)` por `webSocket.begin(ws_host, ws_port, ws_path);`.
