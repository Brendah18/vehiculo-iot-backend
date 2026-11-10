/**
 * Módulo de Configuración Centralizada (ES6 Module)
 * Contiene las URLs reales de AWS EC2 (HTTPS y WSS), ID de vehículo
 * y mapeo de comandos base.
 */

export const CONFIG = Object.freeze({
  // Infraestructura AWS EC2 real
  API_BASE_URL: "https://52.4.170.82:8000",
  WS_BASE_URL: "wss://52.4.170.82:8000/ws",

  // Identificador del vehículo por defecto registrado en Amazon RDS
  VEHICULO_ID: 1,

  // Identificador de origen para movimientos manuales enviados desde esta app
  ORIGEN_CONTROL: "WEB-CONTROL-GH",

  // Intervalo de verificación periódica (ping HTTPS) hacia la API AWS (ms)
  HEALTH_POLL_INTERVAL_MS: 12000,

  // Timeout por petición Fetch (ms)
  FETCH_TIMEOUT_MS: 8000,

  // Tiempo base de reconexión WebSocket (ms)
  WS_RECONNECT_DELAY_MS: 3500,

  // Endpoints principales expuestos por el backend en EC2
  ENDPOINTS: {
    VEHICULOS: "/api/vehiculos",
    COMANDOS: "/api/comandos",
    COMANDOS_VEHICULO: (idVehiculo) => `/api/vehiculos/${idVehiculo}/comandos`,
    DEMOS: "/api/demos",
    DEMOS_VEHICULO: (idVehiculo) => `/api/vehiculos/${idVehiculo}/demos`,
    MOVIMIENTOS: "/api/movimientos",
    CONTROL_MOVIMIENTO: "/api/control/movimiento",
    DEMO_INICIAR: "/api/demos/iniciar",
    CONTROL_DEMO_EJECUTAR: (idDemo) => `/api/control/demos/${idDemo}/ejecutar`,
    DEMO_CANCELAR: "/api/demos/cancelar",
    HEALTH_DB: "/api/health/db" // Si no existe en el backend, el indicador RDS mostrará "Sin verificar"
  },

  // Catálogo de respaldo local por nombre/código en caso de que el catálogo remoto use IDs estándar
  DEFAULT_COMMAND_MAP: {
    AVANZAR: { id_comando: 1, codigo: 1, nombre: "AVANZAR" },
    RETROCEDER: { id_comando: 2, codigo: 2, nombre: "RETROCEDER" },
    IZQUIERDA: { id_comando: 3, codigo: 3, nombre: "GIRAR_IZQUIERDA" },
    GIRAR_IZQUIERDA: { id_comando: 3, codigo: 3, nombre: "GIRAR_IZQUIERDA" },
    DERECHA: { id_comando: 4, codigo: 4, nombre: "GIRAR_DERECHA" },
    GIRAR_DERECHA: { id_comando: 4, codigo: 4, nombre: "GIRAR_DERECHA" },
    SUBIR_BRAZO: { id_comando: 5, codigo: 5, nombre: "SUBIR_BRAZO" },
    BAJAR_BRAZO: { id_comando: 6, codigo: 6, nombre: "BAJAR_BRAZO" },
    ABRIR_PALA: { id_comando: 7, codigo: 7, nombre: "ABRIR_PALA" },
    CERRAR_PALA: { id_comando: 8, codigo: 8, nombre: "CERRAR_PALA" },
    DETENER: { id_comando: 9, codigo: 9, nombre: "DETENER" },
    GIRO_90_IZQ: { id_comando: 3, codigo: 3, nombre: "GIRO_90_IZQ" },
    GIRO_90_DER: { id_comando: 4, codigo: 4, nombre: "GIRO_90_DER" },
    GIRO_360_IZQ: { id_comando: 3, codigo: 3, nombre: "GIRO_360_IZQ" },
    GIRO_360_DER: { id_comando: 4, codigo: 4, nombre: "GIRO_360_DER" }
  }
});
