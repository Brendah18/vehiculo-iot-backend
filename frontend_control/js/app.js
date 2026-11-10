/**
 * Coordinador Global de la Aplicación de Control IoT (ES6 Module)
 * - Inicializa los 3 indicadores reales de infraestructura (WSS, API AWS, Amazon RDS).
 * - Carga dinámicamente los catálogos GET /api/comandos y GET /api/demos.
 * - Vincula el Joystick Virtual, botones secundarios de maniobra y el botón DETENER prioritario.
 * - Gestiona el bloqueo de controles concurrentes cuando una DEMO está en curso.
 */

import { CONFIG } from "./config.js";
import { api } from "./api.js";
import { IoTWebSocketClient } from "./websocket.js";
import { VirtualJoystick } from "./joystick.js";

class ControlApp {
  constructor() {
    // Mapa de comandos indexado por clave normalizada (ej. "AVANZAR", "DETENER")
    this.commandCatalog = new Map();
    this.isDemoRunning = false;
    this.activeDemoId = null;
    this.healthTimer = null;

    // Referencias DOM
    this.ui = {
      vehiculoId: document.getElementById("lbl-vehiculo-id"),
      badgeWs: document.getElementById("badge-ws"),
      badgeApi: document.getElementById("badge-api"),
      badgeRds: document.getElementById("badge-rds"),
      btnRefreshHealth: document.getElementById("btn-refresh-health"),
      lblComandoActual: document.getElementById("lbl-comando-actual"),
      lblUltimaRespuesta: document.getElementById("lbl-ultima-respuesta"),
      badgeJoystickDir: document.getElementById("badge-direccion-joystick"),
      joystickZone: document.getElementById("joystick-zone"),
      joystickThumb: document.getElementById("joystick-thumb"),
      btnStopPriority: document.getElementById("btn-stop-priority"),
      secondaryButtons: document.querySelectorAll(".cmd-sec-btn"),
      dynamicCatalogContainer: document.getElementById("dynamic-catalog-commands"),
      selectDemo: document.getElementById("select-demo"),
      btnDemoStart: document.getElementById("btn-demo-start"),
      btnDemoCancel: document.getElementById("btn-demo-cancel"),
      badgeDemoStatus: document.getElementById("badge-demo-status")
    };
  }

  async init() {
    if (this.ui.vehiculoId) {
      this.ui.vehiculoId.textContent = String(CONFIG.VEHICULO_ID);
    }

    // 1. Inicializar catálogo base de respaldo y luego sincronizar con GET /api/comandos
    this.seedDefaultCommands();

    // 2. Inicializar Joystick Virtual
    this.joystick = new VirtualJoystick({
      zoneElement: this.ui.joystickZone,
      thumbElement: this.ui.joystickThumb,
      onDirectionChange: (direction) => this.handleJoystickDirection(direction)
    });

    // 3. Inicializar cliente WebSocket WSS real
    this.wsClient = new IoTWebSocketClient({
      onStatusChange: (state) => this.updateWsIndicator(state),
      onMessage: (payload) => this.handleWsMessage(payload)
    });
    this.wsClient.connect();

    // 4. Enlazar eventos de botones y controles
    this.bindUiEvents();

    // 5. Ejecutar verificación de salud y carga inicial de catálogos desde la API AWS
    await this.verifyHealthAndSyncCatalogs();

    // 6. Programar ping HTTPS periódico para el Indicador 2 (API AWS) y 3 (Amazon RDS)
    this.healthTimer = window.setInterval(
      () => this.checkHealthOnly(),
      CONFIG.HEALTH_POLL_INTERVAL_MS
    );
  }

  seedDefaultCommands() {
    Object.entries(CONFIG.DEFAULT_COMMAND_MAP).forEach(([key, cmd]) => {
      this.commandCatalog.set(key.toUpperCase(), { ...cmd });
    });
  }

  normalizeCommandKey(rawName) {
    return String(rawName || "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, "_");
  }

  bindUiEvents() {
    // Botón sincronizar salud/catálogos
    this.ui.btnRefreshHealth.addEventListener("click", () => {
      this.verifyHealthAndSyncCatalogs();
    });

    // Botón DETENER prioritario (cancela cualquier acción y envía DETENER inmediatamente)
    this.ui.btnStopPriority.addEventListener("click", async () => {
      if (this.isDemoRunning && this.activeDemoId) {
        await this.cancelActiveDemo();
      } else {
        this.joystick.forceStop();
        await this.dispatchCommandByName("DETENER", true);
      }
    });

    // Botones secundarios predefinidos (Giros 90° / 360°)
    this.ui.secondaryButtons.forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (this.isDemoRunning) return;
        const cmdName = btn.getAttribute("data-cmd-name");
        if (cmdName) {
          await this.dispatchCommandByName(cmdName, false);
        }
      });
    });

    // Botón Iniciar DEMO
    this.ui.btnDemoStart.addEventListener("click", async () => {
      await this.startSelectedDemo();
    });

    // Botón Cancelar DEMO prioritario
    this.ui.btnDemoCancel.addEventListener("click", async () => {
      await this.cancelActiveDemo();
    });
  }

  /**
   * Verifica salud real de la API AWS y carga catálogos GET /api/comandos y GET /api/demos
   */
  async verifyHealthAndSyncCatalogs() {
    this.updateApiIndicator("checking");
    const { apiAvailable, rdsState } = await api.checkInfrastructureHealth();

    this.updateApiIndicator(apiAvailable ? "available" : "unavailable");
    this.updateRdsIndicator(rdsState);

    if (apiAvailable) {
      await Promise.allSettled([this.loadCommandsCatalog(), this.loadDemosCatalog()]);
    }
  }

  async checkHealthOnly() {
    const { apiAvailable, rdsState } = await api.checkInfrastructureHealth();
    this.updateApiIndicator(apiAvailable ? "available" : "unavailable");
    this.updateRdsIndicator(rdsState);
  }

  /**
   * Carga el catálogo real de comandos desde GET /api/comandos y crea botones táctiles adicionales
   */
  async loadCommandsCatalog() {
    try {
      const comandos = await api.obtenerComandos(CONFIG.VEHICULO_ID);
      if (!Array.isArray(comandos) || comandos.length === 0) return;

      const coreDirections = new Set([
        "AVANZAR",
        "RETROCEDER",
        "IZQUIERDA",
        "GIRAR_IZQUIERDA",
        "DERECHA",
        "GIRAR_DERECHA",
        "DETENER"
      ]);

      this.ui.dynamicCatalogContainer.innerHTML = "";

      comandos.forEach((cmd) => {
        const key = this.normalizeCommandKey(cmd.nombre);
        const entry = {
          id_comando: Number(cmd.id_comando),
          codigo: Number(cmd.codigo ?? cmd.id_comando),
          nombre: String(cmd.nombre),
          descripcion: cmd.descripcion || ""
        };
        this.commandCatalog.set(key, entry);

        // Mapear sinónimos de giro izquierda/derecha para el joystick
        if (key === "GIRAR_IZQUIERDA") {
          this.commandCatalog.set("IZQUIERDA", entry);
        } else if (key === "GIRAR_DERECHA") {
          this.commandCatalog.set("DERECHA", entry);
        }

        // Si es un comando adicional del catálogo (ej. SUBIR_BRAZO, ABRIR_PALA, etc.), agregar botón táctil
        if (!coreDirections.has(key)) {
          const col = document.createElement("div");
          col.className = "col-6 col-sm-3";
          const button = document.createElement("button");
          button.type = "button";
          button.className = "btn btn-outline-secondary text-light w-100 py-2 cmd-sec-btn dynamic-cmd-btn";
          button.disabled = this.isDemoRunning;
          button.innerHTML = `
            <i class="bi bi-cpu d-block fs-6 text-info"></i>
            <span class="small">${entry.nombre.replace(/_/g, " ")}</span>
          `;
          button.addEventListener("click", async () => {
            if (!this.isDemoRunning) {
              await this.dispatchCommandByName(key, false);
            }
          });
          col.appendChild(button);
          this.ui.dynamicCatalogContainer.appendChild(col);
        }
      });
    } catch {
      // Si falla la carga de comandos adicionales, se conserva el mapa base
    }
  }

  /**
   * Carga el selector dinámico de secuencias DEMO desde GET /api/demos
   */
  async loadDemosCatalog() {
    try {
      const demos = await api.obtenerDemos(CONFIG.VEHICULO_ID);
      this.ui.selectDemo.innerHTML = "";

      if (!Array.isArray(demos) || demos.length === 0) {
        const opt = document.createElement("option");
        opt.value = "1";
        opt.textContent = "Demo #1 - Secuencia Principal (Por defecto)";
        this.ui.selectDemo.appendChild(opt);
        return;
      }

      demos.forEach((demo) => {
        const opt = document.createElement("option");
        opt.value = String(demo.id_demo);
        const desc = demo.descripcion ? ` — ${demo.descripcion}` : "";
        opt.textContent = `${demo.nombre}${desc}`;
        this.ui.selectDemo.appendChild(opt);
      });
    } catch {
      this.ui.selectDemo.innerHTML = `<option value="1">Demo #1 - Secuencia Principal</option>`;
    }
  }

  /**
   * Recibe cambios de dirección filtrados desde el Joystick Virtual
   * Al soltar el joystick (direction === 'DETENER'), envía DETENER con prioridad absoluta.
   */
  async handleJoystickDirection(direction) {
    this.ui.badgeJoystickDir.textContent =
      direction === "DETENER" ? "NEUTRAL (CENTRO)" : direction;

    const isPriorityStop = direction === "DETENER";
    if (this.isDemoRunning && !isPriorityStop) {
      return;
    }

    await this.dispatchCommandByName(direction, isPriorityStop);
  }

  /**
   * Resuelve el comando en el catálogo y envía POST /api/movimientos al backend
   */
  async dispatchCommandByName(commandKey, isPriority = false) {
    if (this.isDemoRunning && !isPriority) {
      return;
    }

    const normalized = this.normalizeCommandKey(commandKey);
    const cmdInfo =
      this.commandCatalog.get(normalized) ||
      CONFIG.DEFAULT_COMMAND_MAP[normalized] ||
      CONFIG.DEFAULT_COMMAND_MAP.DETENER;

    this.ui.lblComandoActual.textContent = cmdInfo.nombre;
    this.ui.lblUltimaRespuesta.textContent = `Enviando ${cmdInfo.nombre}...`;

    try {
      await api.enviarMovimiento({
        idVehiculo: CONFIG.VEHICULO_ID,
        idComando: cmdInfo.id_comando,
        codigo: cmdInfo.codigo,
        nombre: cmdInfo.nombre,
        origen: isPriority ? "PRIORIDAD-DETENER" : CONFIG.ORIGEN_CONTROL
      });

      const hora = new Date().toLocaleTimeString();
      this.ui.lblUltimaRespuesta.textContent = `${cmdInfo.nombre} confirmado (${hora})`;
      this.updateApiIndicator("available");
    } catch (err) {
      this.ui.lblUltimaRespuesta.textContent = `Error al enviar ${cmdInfo.nombre}: ${err.message}`;
      this.updateApiIndicator("unavailable");
    }
  }

  /**
   * Ejecuta una secuencia DEMO mediante POST /api/demos/iniciar.
   * Bloquea controles manuales concurrentes mientras está activa.
   */
  async startSelectedDemo() {
    if (this.isDemoRunning) return;

    const selectedDemoId = Number(this.ui.selectDemo.value || 1);
    this.setDemoLockState(true, selectedDemoId);
    this.ui.lblComandoActual.textContent = `DEMO #${selectedDemoId} EN EJECUCIÓN`;
    this.ui.lblUltimaRespuesta.textContent = "Ejecutando secuencia en AWS (sin historial individual)...";

    try {
      await api.iniciarDemo({
        idDemo: selectedDemoId,
        idVehiculo: CONFIG.VEHICULO_ID
      });

      // Si la petición HTTP espera a que termine la DEMO, al resolver liberamos el bloqueo
      if (this.isDemoRunning) {
        this.setDemoLockState(false, null);
        this.ui.lblComandoActual.textContent = "DETENER";
        this.ui.lblUltimaRespuesta.textContent = `DEMO #${selectedDemoId} finalizada correctamente`;
      }
    } catch (err) {
      this.setDemoLockState(false, null);
      this.ui.lblUltimaRespuesta.textContent = `Error en DEMO: ${err.message}`;
    }
  }

  /**
   * Cancela prioritariamente una DEMO activa y envía paro inmediato.
   */
  async cancelActiveDemo() {
    const demoIdToCancel = this.activeDemoId || Number(this.ui.selectDemo.value || 1);
    this.ui.lblUltimaRespuesta.textContent = `Cancelando DEMO #${demoIdToCancel} con prioridad...`;

    try {
      await api.cancelarDemo({
        idDemo: demoIdToCancel,
        idVehiculo: CONFIG.VEHICULO_ID
      });
    } finally {
      this.setDemoLockState(false, null);
      this.ui.lblComandoActual.textContent = "DETENER";
      this.ui.lblUltimaRespuesta.textContent = "DEMO cancelada · Vehículo detenido";
    }
  }

  /**
   * Activa o desactiva el bloqueo de controles concurrentes durante una DEMO
   */
  setDemoLockState(locked, demoId = null) {
    this.isDemoRunning = locked;
    this.activeDemoId = demoId;

    this.joystick.setDisabled(locked);
    this.ui.selectDemo.disabled = locked;
    this.ui.btnDemoStart.disabled = locked;
    this.ui.btnDemoCancel.disabled = !locked;

    this.ui.secondaryButtons.forEach((btn) => {
      btn.disabled = locked;
    });
    document.querySelectorAll(".dynamic-cmd-btn").forEach((btn) => {
      btn.disabled = locked;
    });

    if (locked) {
      this.ui.badgeDemoStatus.className = "badge bg-warning text-dark";
      this.ui.badgeDemoStatus.textContent = `Activa (ID ${demoId})`;
    } else {
      this.ui.badgeDemoStatus.className = "badge bg-secondary";
      this.ui.badgeDemoStatus.textContent = "Inactiva";
    }
  }

  /**
   * Procesa eventos recibidos desde el canal WebSocket WSS en tiempo real
   */
  handleWsMessage(payload) {
    if (!payload || typeof payload !== "object") return;

    if (payload.evento === "DEMO_INICIADA") {
      this.setDemoLockState(true, payload.id_demo || 1);
    } else if (payload.evento === "DEMO_PASO" && payload.comando) {
      this.ui.lblComandoActual.textContent = `DEMO: ${payload.comando}`;
      this.ui.lblUltimaRespuesta.textContent = `Paso #${payload.orden} (${payload.duracion_ms} ms)`;
    } else if (payload.evento === "DEMO_FINALIZADA") {
      this.setDemoLockState(false, null);
      this.ui.lblComandoActual.textContent = "DETENER";
      this.ui.lblUltimaRespuesta.textContent = "DEMO finalizada por el servidor";
    } else if (payload.estado && payload.estado.comando) {
      this.ui.lblComandoActual.textContent = String(payload.estado.comando);
    }
  }

  // ==========================================================================
  // ACTUALIZACIÓN VISUAL DE LOS 3 INDICADORES DE CONEXIÓN REALES
  // ==========================================================================

  /**
   * Indicador 1: WebSocket WSS (En línea / Conectando o Reconectando / Desconectado)
   */
  updateWsIndicator(state) {
    const el = this.ui.badgeWs;
    if (!el) return;

    if (state === "online") {
      el.className = "badge rounded-pill bg-success text-white";
      el.innerHTML = `<span class="status-dot dot-online"></span>En línea`;
    } else if (state === "connecting") {
      el.className = "badge rounded-pill bg-warning text-dark";
      el.innerHTML = `<span class="status-dot dot-warning"></span>Conectando...`;
    } else if (state === "reconnecting") {
      el.className = "badge rounded-pill bg-warning text-dark";
      el.innerHTML = `<span class="status-dot dot-warning"></span>Reconectando...`;
    } else {
      el.className = "badge rounded-pill bg-danger text-white";
      el.innerHTML = `<span class="status-dot dot-offline"></span>Desconectado`;
    }
  }

  /**
   * Indicador 2: API AWS (21 servicios) (Disponible / Comprobando / No disponible)
   */
  updateApiIndicator(state) {
    const el = this.ui.badgeApi;
    if (!el) return;

    if (state === "available") {
      el.className = "badge rounded-pill bg-success text-white";
      el.innerHTML = `<span class="status-dot dot-online"></span>Disponible`;
    } else if (state === "checking") {
      el.className = "badge rounded-pill bg-warning text-dark";
      el.innerHTML = `<span class="status-dot dot-warning"></span>Comprobando...`;
    } else {
      el.className = "badge rounded-pill bg-danger text-white";
      el.innerHTML = `<span class="status-dot dot-offline"></span>No disponible`;
    }
  }

  /**
   * Indicador 3: Amazon RDS (Disponible / No disponible / Sin verificar)
   */
  updateRdsIndicator(state) {
    const el = this.ui.badgeRds;
    if (!el) return;

    if (state === "available") {
      el.className = "badge rounded-pill bg-success text-white";
      el.innerHTML = `<span class="status-dot dot-online"></span>Disponible`;
    } else if (state === "unavailable") {
      el.className = "badge rounded-pill bg-danger text-white";
      el.innerHTML = `<span class="status-dot dot-offline"></span>No disponible`;
    } else {
      el.className = "badge rounded-pill bg-secondary text-light";
      el.innerHTML = `<span class="status-dot dot-neutral"></span>Sin verificar`;
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const app = new ControlApp();
  app.init();
});
