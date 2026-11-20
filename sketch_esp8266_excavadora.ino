/*
 * ==============================================================================
 * EXAMEN PRÁCTICO INTEGRADOR 3.1 - CONTROL FÍSICO EXCAVADORA IoT
 * Placa: NodeMCU 1.0 (ESP-12E / ESP8266)
 * Integración: AWS EC2 + FastAPI + RDS + WSS + WiFiManager + 2x 74HC595 + PC817
 * ==============================================================================
 * BIBLIOTECAS REQUERIDAS EN ARDUINO IDE (Gestor de Bibliotecas):
 *   1. WiFiManager       (by tzapu)
 *   2. WebSockets        (by Markus Sattler)
 *   3. ArduinoJson       (by Benoit Blanchon - v6 o v7)
 * ==============================================================================
 */

#include <ESP8266WiFi.h>
#include <WiFiManager.h>        // Portal cautivo Wi-Fi sin contraseñas fijas
#include <WebSocketsClient.h>   // Cliente WebSocket Seguro (WSS)
#include <ArduinoJson.h>        // Decodificador JSON

// ==============================================================================
// 1. CONFIGURACIÓN DEL SERVIDOR AWS EC2 (vehiculo_iot_api)
// ==============================================================================
const char* WS_HOST          = "52.4.170.82";
const uint16_t WS_PORT       = 8000;
const char* WS_PATH          = "/ws/1?token=ESP8266_DEVICE";
const int   ID_VEHICULO_PROPIO = 1;
const char* AP_PORTAL_NOMBRE = "Excavadora_IoT_Setup";

// ==============================================================================
// 2. PINES SEGUROS DEL NODEMCU -> DOS 74HC595 EN CASCADA
//    (Conectar en el lado DERECHO de tu placa de expansión verde)
// ==============================================================================
#define PIN_CLOCK      D5   // GPIO14 -> Pin 11 (SHCP / SRCLK) de ambos 74HC595
#define PIN_LATCH      D6   // GPIO12 -> Pin 12 (STCP / RCLK)  de ambos 74HC595
#define PIN_DATA       D7   // GPIO13 -> Pin 14 (DS / SER)     del 1er 74HC595

// Botón físico FLASH del NodeMCU (D3 / GPIO0): mantener 5 s a GND para reset Wi-Fi
#define PIN_RESET_WIFI D3   // GPIO0  -> Mantener presionado 5 s para borrar Wi-Fi

// ==============================================================================
// 3. MAPA DE BITS (0..15) DE LOS DOS 74HC595 -> OPTOACOPLADORES PC817
//    Bits 0..7  = Q0..Q7 del 1er 74HC595 (el que recibe PIN_DATA)
//    Bits 8..15 = Q0..Q7 del 2do 74HC595 (conectado en cascada por Q7')
//
//    TIP DE CALIBRACIÓN:
//    En el Monitor Serie escribe T0, T1, T2... hasta T15 para activar 1 segundo
//    cada canal y confirmar qué botón físico del control corresponde a cada bit.
//    Luego ajusta estos números si algún cable quedó en otro canal.
// ==============================================================================
#define BIT_ADELANTE          0   // Q0  (Chip 1) -> 01. ADELANTE
#define BIT_ATRAS             1   // Q1  (Chip 1) -> 02. ATRÁS
#define BIT_GIRAR_IZQUIERDA   2   // Q2  (Chip 1) -> 03. GIRAR IZQUIERDA
#define BIT_GIRAR_DERECHA     3   // Q3  (Chip 1) -> 04. GIRAR DERECHA
#define BIT_MOVER_IZQUIERDA   4   // Q4  (Chip 1) -> 05. MOVER IZQUIERDA
#define BIT_MOVER_DERECHA     5   // Q5  (Chip 1) -> 06. MOVER DERECHA
#define BIT_SUBIR_BRAZO       6   // Q6  (Chip 1) -> 07. SUBIR BRAZO
#define BIT_BAJAR_BRAZO       7   // Q7  (Chip 1) -> 08. BAJAR BRAZO
#define BIT_LUZ_LED           8   // Q0  (Chip 2) -> 09. LUZ / LED
#define BIT_ACTIVAR_SONIDO    9   // Q1  (Chip 2) -> 10. ACTIVAR SONIDO
#define BIT_DESACTIVAR_SONIDO 10  // Q2  (Chip 2) -> 11. DESACTIVAR SONIDO
#define BIT_CONTROL_REMOTO    11  // Q3  (Chip 2) -> 12. CONTROL REMOTO

// Si tus módulos PC817 se activan con señal en BAJO (LOW), cambia esto a true.
// En los módulos verdes HY-M154 estándar normalmente se activan en ALTO (false).
const bool LOGICA_INVERTIDA = false;

// ==============================================================================
// 4. TIEMPOS DE SEGURIDAD (RN09 y RN10)
// ==============================================================================
const unsigned long DURACION_DEFECTO_MS  = 1500; // Duración para movimiento manual
const unsigned long DURACION_AUXILIAR_MS = 600;  // Pulsación para botón de luz/sonido
const unsigned long DURACION_MAXIMA_MS   = 5000; // Límite máximo de seguridad
const unsigned long PAUSA_TRANSICION_MS  = 40;   // Pausa al cambiar dirección incompatible
const unsigned long TIEMPO_RESET_BTN_MS  = 5000; // 5 segundos para resetear Wi-Fi (8.2)

// ==============================================================================
// 5. VARIABLES DE ESTADO GLOBAL
// ==============================================================================
WebSocketsClient webSocket;

uint16_t mascaraActual        = 0x0000;
bool     salidaActiva         = false;
unsigned long tiempoFinAccion = 0;
String   comandoActivo        = "DETENER";

bool     wsConectado          = false;
unsigned long inicioBotonReset = 0;
bool     botonResetPresionado  = false;

// ==============================================================================
// 6. CONTROL DE LOS DOS 74HC595 EN CASCADA
// ==============================================================================
void escribirRegistros595(uint16_t mascara16Bits) {
  uint16_t valorSalida = LOGICA_INVERTIDA ? (~mascara16Bits) : mascara16Bits;

  // Primero sale el byte alto (2do 74HC595, bits 8..15) y luego el byte bajo (1er 74HC595, bits 0..7)
  uint8_t byteAlto = (valorSalida >> 8) & 0xFF;
  uint8_t byteBajo = valorSalida & 0xFF;

  digitalWrite(PIN_LATCH, LOW);
  shiftOut(PIN_DATA, PIN_CLOCK, MSBFIRST, byteAlto);
  shiftOut(PIN_DATA, PIN_CLOCK, MSBFIRST, byteBajo);
  digitalWrite(PIN_LATCH, HIGH);

  mascaraActual = mascara16Bits;
}

// Estado seguro: apaga inmediatamente los 16 canales (RN11)
void liberarSalidas(const char* motivo) {
  escribirRegistros595(0x0000);
  if (salidaActiva) {
    Serial.print(F("[LIBERACION] Salidas en 0x0000 (Estado seguro) | Motivo: "));
    Serial.println(motivo);
  }
  salidaActiva = false;
  tiempoFinAccion = 0;
  comandoActivo = "DETENER";
}

// Activa exclusivamente un bit con exclusión mutua y temporizador de seguridad
void activarCanalSeguro(int bitCanal, const String& nombreCmd, unsigned long duracionMs) {
  if (bitCanal < 0 || bitCanal > 15) {
    Serial.println(F("[ERROR] Bit de canal fuera de rango (0..15). Ignorado."));
    return;
  }

  // RN08 y RN09: Liberar orden previa antes de activar la nueva
  if (salidaActiva) {
    escribirRegistros595(0x0000);
    delay(PAUSA_TRANSICION_MS);
  }

  // RN10: Aplicar límite máximo de tiempo
  if (duracionMs == 0) {
    duracionMs = DURACION_DEFECTO_MS;
  } else if (duracionMs > DURACION_MAXIMA_MS) {
    duracionMs = DURACION_MAXIMA_MS;
  }

  uint16_t nuevaMascara = (uint16_t)(1U << bitCanal);
  escribirRegistros595(nuevaMascara);

  salidaActiva    = true;
  comandoActivo   = nombreCmd;
  tiempoFinAccion = millis() + duracionMs;

  Serial.print(F("[ACTIVACION] Comando: "));
  Serial.print(nombreCmd);
  Serial.print(F(" | Bit 74HC595: Q"));
  Serial.print(bitCanal);
  Serial.print(F(" | Duracion: "));
  Serial.print(duracionMs);
  Serial.println(F(" ms"));
}

// ==============================================================================
// 7. MAPEO DE COMANDOS DEL CATÁLOGO RDS -> CANAL DEL 74HC595
// ==============================================================================
void procesarComando(String cmd, int codigo, unsigned long duracionMs) {
  cmd.trim();
  cmd.toUpperCase();
  cmd.replace(" ", "_");

  // Detención prioritaria inmediata (código 13)
  if (cmd == "DETENER" || cmd == "STOP" || codigo == 13) {
    liberarSalidas("Comando DETENER recibido");
    return;
  }

  // Catálogo oficial de los 12 Movimientos del Profesor (01..12)
  if (cmd == "ADELANTE" || cmd == "AVANZAR" || codigo == 1) {
    activarCanalSeguro(BIT_ADELANTE, "ADELANTE", duracionMs);
  }
  else if (cmd == "ATRAS" || cmd == "ATRÁS" || cmd == "RETROCEDER" || codigo == 2) {
    activarCanalSeguro(BIT_ATRAS, "ATRAS", duracionMs);
  }
  else if (cmd == "GIRAR_IZQUIERDA" || cmd == "IZQUIERDA" || codigo == 3) {
    activarCanalSeguro(BIT_GIRAR_IZQUIERDA, "GIRAR_IZQUIERDA", duracionMs);
  }
  else if (cmd == "GIRAR_DERECHA" || cmd == "DERECHA" || codigo == 4) {
    activarCanalSeguro(BIT_GIRAR_DERECHA, "GIRAR_DERECHA", duracionMs);
  }
  else if (cmd == "MOVER_IZQUIERDA" || cmd == "CABINA_IZQ" || codigo == 5) {
    activarCanalSeguro(BIT_MOVER_IZQUIERDA, "MOVER_IZQUIERDA", duracionMs);
  }
  else if (cmd == "MOVER_DERECHA" || cmd == "CABINA_DER" || codigo == 6) {
    activarCanalSeguro(BIT_MOVER_DERECHA, "MOVER_DERECHA", duracionMs);
  }
  else if (cmd == "SUBIR_BRAZO" || codigo == 7) {
    activarCanalSeguro(BIT_SUBIR_BRAZO, "SUBIR_BRAZO", duracionMs);
  }
  else if (cmd == "BAJAR_BRAZO" || codigo == 8) {
    activarCanalSeguro(BIT_BAJAR_BRAZO, "BAJAR_BRAZO", duracionMs);
  }
  else if (cmd == "LUZ_LED" || cmd == "LUZ" || cmd == "LED" || codigo == 9) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(BIT_LUZ_LED, "LUZ_LED", dur);
  }
  else if (cmd == "ACTIVAR_SONIDO" || cmd == "SONIDO" || cmd == "CLAXON" || codigo == 10) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(BIT_ACTIVAR_SONIDO, "ACTIVAR_SONIDO", dur);
  }
  else if (cmd == "DESACTIVAR_SONIDO" || codigo == 11) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(BIT_DESACTIVAR_SONIDO, "DESACTIVAR_SONIDO", dur);
  }
  else if (cmd == "CONTROL_REMOTO" || codigo == 12) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(BIT_CONTROL_REMOTO, "CONTROL_REMOTO", dur);
  }
  else {
    // RN06: Descartar comandos desconocidos
    Serial.print(F("[IGNORADO] Comando no reconocido: "));
    Serial.println(cmd);
  }
}

// ==============================================================================
// 8. MANEJADOR DE EVENTOS WEBSOCKET SEGURO (WSS)
// ==============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      if (wsConectado) {
        Serial.println(F("[WSS] Desconectado del servidor AWS. Pasando a estado seguro."));
      }
      wsConectado = false;
      // RN11 y RN15: Liberar salidas al perder comunicación
      liberarSalidas("Desconexion WSS");
      break;

    case WStype_CONNECTED:
      wsConectado = true;
      Serial.print(F("[WSS] Conectado exitosamente a wss://"));
      Serial.print(WS_HOST);
      Serial.print(F(":"));
      Serial.print(WS_PORT);
      Serial.println(WS_PATH);
      // Asegurar salidas apagadas al conectar (RN15)
      liberarSalidas("Inicio de sesion WSS");
      break;

    case WStype_TEXT: {
      Serial.print(F("[WSS RX] "));
      Serial.println((char*)payload);

      DynamicJsonDocument doc(1024);
      DeserializationError error = deserializeJson(doc, payload, length);

      if (error) {
        Serial.print(F("[ERROR JSON] Fallo al parsear: "));
        Serial.println(error.c_str());
        return;
      }

      // 1. Validar que el evento sea para nuestro vehículo (RN06)
      int idVehiculoRecibido = -1;
      if (doc.containsKey("estado") && doc["estado"].containsKey("id_vehiculo")) {
        idVehiculoRecibido = doc["estado"]["id_vehiculo"];
      } else if (doc.containsKey("id_vehiculo")) {
        idVehiculoRecibido = doc["id_vehiculo"];
      }

      if (idVehiculoRecibido != -1 && idVehiculoRecibido != ID_VEHICULO_PROPIO) {
        Serial.print(F("[IGNORADO] Evento dirigido a otro vehiculo ID="));
        Serial.println(idVehiculoRecibido);
        return;
      }

      // 2. Revisar el tipo de evento
      String evento = doc["evento"] | "";
      evento.toUpperCase();

      // RN07 y RN15: Ignorar el estado histórico recibido al conectarse/reconectarse
      if (evento == "CONEXION_ESTABLECIDA" || evento == "PING" || evento == "DEMO_INICIADA") {
        Serial.print(F("[INFO] Evento informativo ignorado para actuacion: "));
        Serial.println(evento);
        return;
      }

      // Pausa o fin de DEMO -> liberar salidas inmediatamente
      if (evento == "DEMO_PAUSA" || evento == "DEMO_FINALIZADA") {
        liberarSalidas(evento.c_str());
        return;
      }

      // Evento directo de claxon / sonido
      if (evento == "CLAXON") {
        procesarComando("ACTIVAR_SONIDO", 10, DURACION_AUXILIAR_MS);
        return;
      }

      // 3. Extraer comando, acción, código y duración
      String comando = "";
      int codigo = -1;
      unsigned long duracionMs = 0;

      if (doc.containsKey("estado") && doc["estado"].is<JsonObject>()) {
        JsonObject est = doc["estado"];
        if (est.containsKey("comando") && !est["comando"].isNull()) {
          comando = String((const char*)est["comando"]);
        }
        if (est.containsKey("codigo") && !est["codigo"].isNull()) {
          codigo = est["codigo"].as<int>();
        }
      }

      // Si viene en la raíz (ej. MOVIMIENTO_INDIVIDUAL o DEMO_PASO)
      if (comando.length() == 0 && doc.containsKey("comando") && !doc["comando"].isNull()) {
        comando = String((const char*)doc["comando"]);
      }
      if (comando.length() == 0 && doc.containsKey("accion") && !doc["accion"].isNull()) {
        comando = String((const char*)doc["accion"]);
      }
      if (codigo == -1 && doc.containsKey("codigo") && !doc["codigo"].isNull()) {
        codigo = doc["codigo"].as<int>();
      }
      if (doc.containsKey("duracion_ms") && !doc["duracion_ms"].isNull()) {
        duracionMs = doc["duracion_ms"].as<unsigned long>();
      }

      // 4. Ejecutar el comando físicamente en los 74HC595 -> PC817
      if (comando.length() > 0 || codigo != -1) {
        procesarComando(comando, codigo, duracionMs);
      }
      break;
    }

    case WStype_ERROR:
      Serial.println(F("[WSS ERROR] Error de comunicacion WebSocket."));
      liberarSalidas("Error WSS");
      break;

    default:
      break;
  }
}

// ==============================================================================
// 9. RESTABLECIMIENTO DE WI-FI (8.1 por Serial 'R/r' y 8.2 por GPIO 5 segundos)
// ==============================================================================
void restablecerWiFi(const char* origen) {
  Serial.println();
  Serial.print(F("[WIFI RESET] Borrando credenciales guardadas | Origen: "));
  Serial.println(origen);

  // 8.3: Todas las salidas físicas inactivas durante reinicio/configuración
  liberarSalidas("Reset Wi-Fi");
  webSocket.disconnect();

  WiFiManager wm;
  wm.resetSettings();
  delay(500);
  Serial.println(F("[WIFI RESET] Reiniciando ESP8266 para abrir portal de configuracion..."));
  delay(500);
  ESP.restart();
}

void revisarComandosSerial() {
  if (!Serial.available()) return;

  String entrada = Serial.readStringUntil('\n');
  entrada.trim();
  if (entrada.length() == 0) return;

  // 8.1: Restablecimiento Wi-Fi con 'R' o 'r'
  if (entrada.equalsIgnoreCase("R")) {
    restablecerWiFi("Comando Serial R/r");
    return;
  }

  // Parada de emergencia manual por Serial
  if (entrada.equalsIgnoreCase("S")) {
    liberarSalidas("Parada manual Serial (S)");
    return;
  }

  // Modo prueba/calibración de canales: escribir T0..T15 activa ese bit 1 segundo
  if ((entrada.startsWith("T") || entrada.startsWith("t")) && entrada.length() >= 2) {
    int bitPrueba = entrada.substring(1).toInt();
    if (bitPrueba >= 0 && bitPrueba <= 15) {
      Serial.print(F("[TEST] Probando bit Q"));
      Serial.print(bitPrueba);
      Serial.println(F(" durante 1000 ms..."));
      activarCanalSeguro(bitPrueba, "TEST_Q" + String(bitPrueba), 1000);
    } else {
      Serial.println(F("[TEST] Usa T0 hasta T15 (ejemplo: T0, T1, ..., T9)."));
    }
  }
}

void revisarBotonResetWiFi() {
  // 8.2: GPIO mantenido 5 segundos a GND (Botón FLASH / D3)
  if (digitalRead(PIN_RESET_WIFI) == LOW) {
    if (!botonResetPresionado) {
      botonResetPresionado = true;
      inicioBotonReset = millis();
      Serial.println(F("[WIFI RESET] Boton D3/FLASH presionado... manten 5 segundos para borrar Wi-Fi."));
    } else if (millis() - inicioBotonReset >= TIEMPO_RESET_BTN_MS) {
      restablecerWiFi("GPIO D3/FLASH mantenido 5 segundos a GND");
    }
  } else {
    botonResetPresionado = false;
  }
}

// ==============================================================================
// 10. SETUP (ARRANQUE SEGURO + WIFIMANAGER + WSS)
// ==============================================================================
void setup() {
  // 1. PRIMERO: Configurar pines de 74HC595 y poner todas las salidas en 0 (4.3)
  pinMode(PIN_DATA, OUTPUT);
  pinMode(PIN_CLOCK, OUTPUT);
  pinMode(PIN_LATCH, OUTPUT);
  escribirRegistros595(0x0000); // Estado seguro inmediato al encender

  // Botón de reset Wi-Fi con pull-up interno
  pinMode(PIN_RESET_WIFI, INPUT_PULLUP);

  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println(F("=========================================================="));
  Serial.println(F("  EXCAVADORA IoT - ESP8266 + WiFiManager + WSS + 74HC595  "));
  Serial.println(F("=========================================================="));
  Serial.print(F("ID Dispositivo (Chip ID): ESP8266-"));
  Serial.println(ESP.getChipId(), HEX);
  Serial.print(F("Vehiculo asignado:        ID "));
  Serial.println(ID_VEHICULO_PROPIO);
  Serial.println(F("Salidas 74HC595:          0x0000 (Estado seguro inicial)"));
  Serial.println(F("Comandos Serial:          [R] Reset Wi-Fi | [S] Stop | [T0..T15] Test bit"));

  // 2. Configurar WiFiManager (sin contraseñas fijas en código - 4.1)
  WiFi.mode(WIFI_STA);
  WiFiManager wm;
  wm.setDebugOutput(false); // 5.4: No exhibir contraseñas ni información sensible
  wm.setConfigPortalTimeout(180); // 3 min de espera si se abre el portal

  Serial.print(F("[WIFI] Conectando con red guardada (o portal: "));
  Serial.print(AP_PORTAL_NOMBRE);
  Serial.println(F(")..."));

  if (!wm.autoConnect(AP_PORTAL_NOMBRE)) {
    Serial.println(F("[WIFI] Tiempo agotado en portal. Reiniciando en estado seguro..."));
    escribirRegistros595(0x0000);
    delay(2000);
    ESP.restart();
  }

  // 3. Mostrar datos de conexión Wi-Fi sin contraseña (6.1)
  Serial.println(F("[WIFI] Conexion establecida!"));
  Serial.print(F("  -> Red SSID:  "));
  Serial.println(WiFi.SSID());
  Serial.print(F("  -> IP Local:  "));
  Serial.println(WiFi.localIP());
  Serial.print(F("  -> Senal:     "));
  Serial.print(WiFi.RSSI());
  Serial.println(F(" dBm"));

  // 4. Iniciar WebSocket Seguro (WSS) hacia AWS EC2
  Serial.print(F("[WSS] Conectando a wss://"));
  Serial.print(WS_HOST);
  Serial.print(F(":"));
  Serial.print(WS_PORT);
  Serial.println(WS_PATH);

  webSocket.beginSSL(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
  webSocket.enableHeartbeat(15000, 3000, 2);
}

// ==============================================================================
// 11. LOOP PRINCIPAL (NO BLOQUEANTE)
// ==============================================================================
void loop() {
  // Atender WebSocket
  webSocket.loop();

  // Revisar si se cayó el Wi-Fi -> pasar inmediatamente a estado seguro (7.3 / RN11)
  if (WiFi.status() != WL_CONNECTED) {
    if (salidaActiva) {
      liberarSalidas("Perdida de conexion Wi-Fi");
    }
  }

  // RN10: Liberación automática cuando vence el tiempo de pulsación del PC817
  if (salidaActiva && (long)(millis() - tiempoFinAccion) >= 0) {
    liberarSalidas("Fin de duracion programada");
  }

  // Revisar comandos de Monitor Serie (R/r, S, T0..T15) y botón físico de 5 s
  revisarComandosSerial();
  revisarBotonResetWiFi();
}
