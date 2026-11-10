/**
 * Módulo de Joystick Virtual Circular (ES6 Module)
 * - Operable por Mouse y Pointer/Touch Events.
 * - Mapeo directo a comandos reales: AVANZAR, RETROCEDER, IZQUIERDA, DERECHA y DETENER.
 * - Control de ráfagas (debouncing por cambio de estado): solo emite evento cuando
 *   cambia la dirección efectiva, evitando saturar la red por cada píxel o fotograma.
 * - Retorno automático al punto neutral central y emisión prioritaria de DETENER
 *   al soltar, cancelar toque o perder foco de ventana.
 */

export class VirtualJoystick {
  /**
   * @param {Object} options
   * @param {HTMLElement} options.zoneElement Contenedor circular del joystick
   * @param {HTMLElement} options.thumbElement Palanca móvil (thumb)
   * @param {(direction: 'AVANZAR'|'RETROCEDER'|'IZQUIERDA'|'DERECHA'|'DETENER') => void} options.onDirectionChange
   */
  constructor({ zoneElement, thumbElement, onDirectionChange }) {
    this.zone = zoneElement;
    this.thumb = thumbElement;
    this.onDirectionChange = onDirectionChange || (() => {});

    this.isDragging = false;
    this.activePointerId = null;
    this.currentDirection = "DETENER";
    this.disabled = false;

    // Porcentaje mínimo de desplazamiento respecto al radio para salir de la zona muerta (deadzone)
    this.deadzoneRatio = 0.28;

    this.bindEvents();
  }

  bindEvents() {
    // Uso de Pointer Events (unifica Mouse y Touch en navegadores modernos)
    this.zone.addEventListener("pointerdown", (e) => this.handlePointerDown(e));
    window.addEventListener("pointermove", (e) => this.handlePointerMove(e));
    window.addEventListener("pointerup", (e) => this.handlePointerUp(e));
    window.addEventListener("pointercancel", (e) => this.handlePointerUp(e));

    // Seguridad adicional: si la pestaña pierde foco o visibilidad mientras se arrastra, enviar DETENER
    window.addEventListener("blur", () => this.forceStop());
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        this.forceStop();
      }
    });
  }

  setDisabled(isDisabled) {
    this.disabled = Boolean(isDisabled);
    if (this.disabled) {
      this.zone.classList.add("joystick-disabled");
      this.forceStop();
    } else {
      this.zone.classList.remove("joystick-disabled");
    }
  }

  handlePointerDown(event) {
    if (this.disabled) return;
    event.preventDefault();

    this.isDragging = true;
    this.activePointerId = event.pointerId;
    this.thumb.classList.add("dragging");

    try {
      this.zone.setPointerCapture(event.pointerId);
    } catch {
      // Ignorar si el navegador no soporta setPointerCapture en ese dispositivo
    }

    this.updateFromClientCoords(event.clientX, event.clientY);
  }

  handlePointerMove(event) {
    if (!this.isDragging || this.disabled) return;
    if (this.activePointerId !== null && event.pointerId !== this.activePointerId) {
      return;
    }

    this.updateFromClientCoords(event.clientX, event.clientY);
  }

  handlePointerUp(event) {
    if (!this.isDragging) return;
    if (
      event &&
      this.activePointerId !== null &&
      event.pointerId !== undefined &&
      event.pointerId !== this.activePointerId
    ) {
      return;
    }

    this.resetToCenterAndStop();
  }

  /**
   * Calcula posición relativa dentro del círculo, limita el radio máximo
   * y determina la dirección cardinal efectiva.
   */
  updateFromClientCoords(clientX, clientY) {
    const rect = this.zone.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const maxRadius = (rect.width - this.thumb.offsetWidth) / 2;
    const dx = clientX - centerX;
    const dy = clientY - centerY;
    const distance = Math.hypot(dx, dy);

    let clampedX = dx;
    let clampedY = dy;

    if (distance > maxRadius && maxRadius > 0) {
      const ratio = maxRadius / distance;
      clampedX = dx * ratio;
      clampedY = dy * ratio;
    }

    // Mover visualmente el thumb
    this.thumb.style.transform = `translate3d(${clampedX.toFixed(1)}px, ${clampedY.toFixed(1)}px, 0px)`;

    // Determinar si superó la zona neutral (deadzone)
    const normalizedDistance = maxRadius > 0 ? Math.min(distance / maxRadius, 1) : 0;
    if (normalizedDistance < this.deadzoneRatio) {
      this.emitIfDirectionChanged("DETENER");
      return;
    }

    // Ángulo en grados (-180 a 180), donde -90 es arriba (AVANZAR)
    const angleDeg = Math.atan2(dy, dx) * (180 / Math.PI);
    let nextDirection = "DETENER";

    if (angleDeg >= -135 && angleDeg < -45) {
      nextDirection = "AVANZAR";
    } else if (angleDeg >= -45 && angleDeg < 45) {
      nextDirection = "DERECHA";
    } else if (angleDeg >= 45 && angleDeg < 135) {
      nextDirection = "RETROCEDER";
    } else {
      nextDirection = "IZQUIERDA";
    }

    this.emitIfDirectionChanged(nextDirection);
  }

  /**
   * Emite la nueva dirección únicamente si es distinta a la dirección activa actual
   * (Control estricto anti-ráfagas / debouncing de estado).
   */
  emitIfDirectionChanged(nextDirection) {
    if (nextDirection === this.currentDirection) {
      return;
    }
    this.currentDirection = nextDirection;
    this.onDirectionChange(nextDirection);
  }

  /**
   * Retorna inmediatamente el thumb al punto neutral central y emite DETENER con prioridad.
   */
  resetToCenterAndStop() {
    this.isDragging = false;
    this.activePointerId = null;
    this.thumb.classList.remove("dragging");
    this.thumb.style.transform = "translate3d(0px, 0px, 0px)";

    if (this.currentDirection !== "DETENER") {
      this.currentDirection = "DETENER";
      this.onDirectionChange("DETENER");
    }
  }

  /**
   * Fuerza paro inmediato incluso si ya estaba en centro.
   */
  forceStop() {
    this.isDragging = false;
    this.activePointerId = null;
    this.thumb.classList.remove("dragging");
    this.thumb.style.transform = "translate3d(0px, 0px, 0px)";
    this.currentDirection = "DETENER";
    this.onDirectionChange("DETENER");
  }
}
