/**
 * Gestor de Conexión WebSocket Seguro WSS (ES6 Module)
 * Conecta directamente a wss://52.4.170.82:8000/ws (con soporte para canal /ws/{id_vehiculo})
 * y mantiene actualizado el Indicador 1 en tiempo real:
 * - "En línea"
 * - "Conectando..." / "Reconectando..."
 * - "Desconectado"
 */

import { CONFIG } from "./config.js";

export class IoTWebSocketClient {
  /**
   * @param {Object} handlers Callbacks para cambios de estado y mensajes entrantes
   * @param {(state: 'online'|'connecting'|'reconnecting'|'disconnected') => void} handlers.onStatusChange
   * @param {(payload: any) => void} handlers.onMessage
   */
  constructor({ onStatusChange, onMessage } = {}) {
    this.onStatusChange = onStatusChange || (() => {});
    this.onMessage = onMessage || (() => {});
    this.socket = null;
    this.reconnectTimer = null;
    this.hasConnectedOnce = false;
    this.useVehiclePathFallback = false;
    this.manualClose = false;
  }

  /**
   * Construye la URL WSS objetivo.
   * Por defecto utiliza wss://52.4.170.82:8000/ws/{id_vehiculo} o wss://52.4.170.82:8000/ws
   */
  buildWsUrl() {
    const base = CONFIG.WS_BASE_URL.replace(/\/+$/, "");
    if (this.useVehiclePathFallback) {
      return `${base}/${CONFIG.VEHICULO_ID}`;
    }
    return base;
  }

  /**
   * Inicia la conexión WSS real desde el navegador.
   */
  connect() {
    this.manualClose = false;
    this.clearReconnectTimer();

    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.onStatusChange(this.hasConnectedOnce ? "reconnecting" : "connecting");

    const wsUrl = this.buildWsUrl();
    try {
      this.socket = new WebSocket(wsUrl);
    } catch {
      this.onStatusChange("disconnected");
      this.scheduleReconnect();
      return;
    }

    this.socket.addEventListener("open", () => {
      this.hasConnectedOnce = true;
      this.onStatusChange("online");
    });

    this.socket.addEventListener("message", (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.onMessage(parsed);
      } catch {
        this.onMessage({ raw: event.data });
      }
    });

    this.socket.addEventListener("error", () => {
      // El evento close se dispara inmediatamente después de error y gestiona la reconexión
    });

    this.socket.addEventListener("close", () => {
      this.onStatusChange("disconnected");
      if (!this.manualClose) {
        // Si falló /ws sin haber conectado nunca, alterna automáticamente a /ws/{id_vehiculo}
        if (!this.hasConnectedOnce) {
          this.useVehiclePathFallback = !this.useVehiclePathFallback;
        }
        this.scheduleReconnect();
      }
    });
  }

  /**
   * Programa un intento de reconexión automática.
   */
  scheduleReconnect() {
    this.clearReconnectTimer();
    this.reconnectTimer = window.setTimeout(() => {
      this.onStatusChange("reconnecting");
      this.connect();
    }, CONFIG.WS_RECONNECT_DELAY_MS);
  }

  clearReconnectTimer() {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Envía un mensaje JSON opcional por el socket si está abierto.
   */
  sendJson(payload) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  disconnect() {
    this.manualClose = true;
    this.clearReconnectTimer();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.onStatusChange("disconnected");
  }
}
