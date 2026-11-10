/**
 * Cliente Fetch async/await centralizado (ES6 Module)
 * Gestiona todas las peticiones HTTPS hacia AWS EC2 (https://52.4.170.82:8000)
 * sin simular historial local y respetando las reglas de negocio del backend.
 */

import { CONFIG } from "./config.js";

class ApiClient {
  constructor() {
    this.baseUrl = CONFIG.API_BASE_URL.replace(/\/+$/, "");
    this.vehiculoId = CONFIG.VEHICULO_ID;
  }

  /**
   * Ejecuta una petición HTTP con control de timeout mediante AbortController.
   * @param {string} path Ruta relativa del endpoint
   * @param {RequestInit} options Opciones de Fetch
   * @param {number} timeoutMs Tiempo máximo de espera
   */
  async request(path, options = {}, timeoutMs = CONFIG.FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const url = `${this.baseUrl}${path}`;
    const headers = {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {})
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      });

      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

      if (!response.ok) {
        const errorMsg =
          typeof data === "object" && data !== null && data.detail
            ? data.detail
            : `HTTP ${response.status}`;
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
      }

      return { ok: true, status: response.status, data };
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Verifica la disponibilidad real de la API AWS (21 servicios) y de Amazon RDS
   * únicamente si el backend provee diagnóstico seguro.
   */
  async checkInfrastructureHealth() {
    let apiAvailable = false;
    let rdsState = "unverified"; // "available" | "unavailable" | "unverified"

    try {
      // 1. Ping HTTPS a GET /api/vehiculos
      const res = await this.request(
        CONFIG.ENDPOINTS.VEHICULOS,
        { method: "GET" },
        5000
      );
      apiAvailable = res.ok;

      // Si GET /api/vehiculos devuelve un arreglo válido o un objeto con datos desde RDS,
      // verificamos si existe un endpoint dedicado de salud de BD; si no, mantenemos "Sin verificar"
      // a menos que el backend exponga explícitamente el estado de RDS.
      if (res.data && typeof res.data === "object" && "rds_status" in res.data) {
        rdsState = res.data.rds_status === "online" ? "available" : "unavailable";
      }
    } catch {
      apiAvailable = false;
    }

    // 2. Comprobación opcional de endpoint de diagnóstico seguro (/api/health/db)
    if (apiAvailable && rdsState === "unverified") {
      try {
        const dbRes = await this.request(
          CONFIG.ENDPOINTS.HEALTH_DB,
          { method: "GET" },
          3500
        );
        if (dbRes.ok && dbRes.data) {
          rdsState = "available";
        }
      } catch (err) {
        // Si devuelve 404 Not Found, el backend no ofrece endpoint de diagnóstico específico:
        // por regla estricta se muestra permanentemente "Sin verificar".
        if (err.status && err.status !== 404) {
          rdsState = "unavailable";
        } else {
          rdsState = "unverified";
        }
      }
    }

    return { apiAvailable, rdsState };
  }

  /**
   * Obtiene el catálogo de comandos del vehículo desde GET /api/comandos
   * (con respaldo automático a /api/vehiculos/{id}/comandos si aplica).
   */
  async obtenerComandos(idVehiculo = this.vehiculoId) {
    try {
      const res = await this.request(
        `${CONFIG.ENDPOINTS.COMANDOS}?id_vehiculo=${idVehiculo}`,
        { method: "GET" }
      );
      if (Array.isArray(res.data)) {
        return res.data;
      }
      if (res.data && Array.isArray(res.data.comandos)) {
        return res.data.comandos;
      }
    } catch {
      // Intento secundario en ruta anidada /api/vehiculos/{id}/comandos
      const fallback = await this.request(
        CONFIG.ENDPOINTS.COMANDOS_VEHICULO(idVehiculo),
        { method: "GET" }
      );
      return Array.isArray(fallback.data) ? fallback.data : [];
    }
    return [];
  }

  /**
   * Obtiene el catálogo de secuencias DEMO desde GET /api/demos
   * (con respaldo automático a /api/vehiculos/{id}/demos).
   */
  async obtenerDemos(idVehiculo = this.vehiculoId) {
    try {
      const res = await this.request(
        `${CONFIG.ENDPOINTS.DEMOS}?id_vehiculo=${idVehiculo}`,
        { method: "GET" }
      );
      if (Array.isArray(res.data)) {
        return res.data;
      }
      if (res.data && Array.isArray(res.data.demos)) {
        return res.data.demos;
      }
    } catch {
      const fallback = await this.request(
        CONFIG.ENDPOINTS.DEMOS_VEHICULO(idVehiculo),
        { method: "GET" }
      );
      return Array.isArray(fallback.data) ? fallback.data : [];
    }
    return [];
  }

  /**
   * Activa un movimiento individual mediante POST /api/movimientos.
   * Si el backend utiliza la ruta alternativa /api/control/movimiento, hace fallback transparente.
   */
  async enviarMovimiento({ idVehiculo = this.vehiculoId, idComando, codigo, nombre, origen = CONFIG.ORIGEN_CONTROL }) {
    const payload = {
      id_vehiculo: Number(idVehiculo),
      id_comando: Number(idComando),
      codigo: Number(codigo ?? idComando),
      comando: String(nombre || ""),
      origen
    };

    try {
      return await this.request(CONFIG.ENDPOINTS.MOVIMIENTOS, {
        method: "POST",
        body: JSON.stringify(payload)
      });
    } catch (err) {
      if (err.status === 404 || err.status === 405) {
        return await this.request(CONFIG.ENDPOINTS.CONTROL_MOVIMIENTO, {
          method: "POST",
          body: JSON.stringify(payload)
        });
      }
      throw err;
    }
  }

  /**
   * Inicia la ejecución de una DEMO en el servidor mediante POST /api/demos/iniciar.
   * IMPORTANTE: El backend gestiona los intervalos N de cada paso y NO contamina el historial.
   */
  async iniciarDemo({ idDemo, idVehiculo = this.vehiculoId }) {
    const payload = {
      id_demo: Number(idDemo),
      id_vehiculo: Number(idVehiculo)
    };

    try {
      return await this.request(
        CONFIG.ENDPOINTS.DEMO_INICIAR,
        {
          method: "POST",
          body: JSON.stringify(payload)
        },
        25000 // Timeout amplio porque el backend puede ejecutar la secuencia temporizada
      );
    } catch (err) {
      if (err.status === 404 || err.status === 405) {
        return await this.request(
          CONFIG.ENDPOINTS.CONTROL_DEMO_EJECUTAR(idDemo),
          {
            method: "POST",
            body: JSON.stringify(payload)
          },
          25000
        );
      }
      throw err;
    }
  }

  /**
   * Cancela de forma prioritaria una DEMO en curso mediante POST /api/demos/cancelar
   * y asegura el envío inmediato del comando DETENER.
   */
  async cancelarDemo({ idDemo, idVehiculo = this.vehiculoId }) {
    const payload = {
      id_demo: Number(idDemo),
      id_vehiculo: Number(idVehiculo)
    };

    try {
      return await this.request(CONFIG.ENDPOINTS.DEMO_CANCELAR, {
        method: "POST",
        body: JSON.stringify(payload)
      });
    } catch {
      // Si el backend no tiene /api/demos/cancelar habilitado aún, forzamos paro con DETENER (id_comando: 9)
      return await this.enviarMovimiento({
        idVehiculo,
        idComando: CONFIG.DEFAULT_COMMAND_MAP.DETENER.id_comando,
        codigo: CONFIG.DEFAULT_COMMAND_MAP.DETENER.codigo,
        nombre: "DETENER",
        origen: "CANCELAR-DEMO"
      });
    }
  }
}

export const api = new ApiClient();
