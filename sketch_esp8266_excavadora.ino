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
uint8_t PIN_CLOCK = D5;   // GPIO14 -> Pin 11 (SHCP / SRCLK) de ambos 74HC595
uint8_t PIN_LATCH = D6;   // GPIO12 -> Pin 12 (STCP / RCLK)  de ambos 74HC595
uint8_t PIN_DATA  = D7;   // GPIO13 -> Pin 14 (DS / SER)     del 1er 74HC595

// Botón físico FLASH del NodeMCU (D3 / GPIO0): mantener 5 s a GND para reset Wi-Fi
#define PIN_RESET_WIFI D3   // GPIO0  -> Mantener presionado 5 s para borrar Wi-Fi

// ==============================================================================
// 3. TABLA DE MAPEO DE CANALES FÍSICOS (0..11) -> OPTOACOPLADORES PC817
//    Bits 0..7  = Q0..Q7 del 1er 74HC595 (el que recibe PIN_DATA)
//    Bits 8..15 = Q0..Q7 del 2do 74HC595 (conectado en cascada por Q7')
//
//    CALIBRACIÓN RÁPIDA EN 10 SEGUNDOS:
//    En el Monitor Serie escribe: TEST_CANALES (o ALL)
//    Anota qué movimiento físico hace la excavadora en cada canal X (0..11)
//    y actualiza el número correspondiente aquí abajo sin tocar el resto del código.
// ==============================================================================
int CANAL_ADELANTE          = 3;   // T3  -> ADELANTE (Dirección OK)
int CANAL_ATRAS             = 2;   // T2  -> ATRÁS (Dirección OK)
int CANAL_GIRAR_IZQUIERDA   = 4;   // T4  -> GIRAR IZQUIERDA (Dirección OK)
int CANAL_GIRAR_DERECHA     = 1;   // T1  -> GIRAR DERECHA (Dirección OK)
int CANAL_MOVER_IZQUIERDA   = 12;  // T12 -> VOLTEAR IZQUIERDA (en lugar de 11 que iba recto atrás)
int CANAL_MOVER_DERECHA     = 7;   // T7  -> MOVER DERECHA (en lugar de 10 que iba recto enfrente)
int CANAL_SUBIR_BRAZO       = 8;   // T8  -> SUBIR BRAZO (confirmado)
int CANAL_BAJAR_BRAZO       = 9;   // T9  -> BAJAR BRAZO (confirmado)
int CANAL_LUZ_LED           = 14;  // T14 -> LUZ LED
int CANAL_ACTIVAR_SONIDO    = 15;  // T15 -> ACTIVAR SONIDO (confirmado)
int CANAL_DESACTIVAR_SONIDO = 15;  // T15 -> DESACTIVAR SONIDO (mismo botón)
int CANAL_CONTROL_REMOTO    = 11;  // T11 -> VELOCIDAD (sin activar la DEMO física del 13)

// Si tus módulos PC817 se activan con señal en BAJO (LOW), cambia esto a true.
// En los módulos verdes HY-M154 estándar normalmente se activan en ALTO (false).
const bool LOGICA_INVERTIDA = false;

// ==============================================================================
// 4. TIEMPOS DE SEGURIDAD (RN09 y RN10)
// ==============================================================================
const unsigned long DURACION_DEFECTO_MS  = 1200; // Duración máx. si no llega DETENER al soltar (evita que se pase de largo)
const unsigned long DURACION_BRAZO_MS    = 3200; // Mayor tiempo y recorrido continuo para subir/bajar brazo
const unsigned long DURACION_AUXILIAR_MS = 850;  // Pulso de 850 ms para que Luz LED, Sonido y Velocidad sí procesen en el carrito
const unsigned long DURACION_MAXIMA_MS   = 5000; // Límite máximo de seguridad
const unsigned long PAUSA_TRANSICION_MS  = 220;  // 220 ms en neutro para que el control RF suelte el botón anterior en la DEMO
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
void procesarComando(String cmd, int idNum, unsigned long duracionMs) {
  cmd.trim();
  cmd.toUpperCase();
  cmd.replace(" ", "_");

  // 1. Detención prioritaria inmediata (DETENER / id 13 o 0)
  if (cmd == "DETENER" || cmd == "STOP" || (cmd.length() == 0 && (idNum == 13 || idNum == 0))) {
    liberarSalidas("Comando DETENER recibido");
    return;
  }

  // 2. Mapeo 1 a 1 por código en TEXTO EXACTO (prioritario) o id_comando numérico (respaldo)
  if (cmd == "ADELANTE" || (cmd.length() == 0 && idNum == 1)) {
    activarCanalSeguro(CANAL_ADELANTE, "ADELANTE", duracionMs);
  }
  else if (cmd == "ATRAS" || cmd == "ATRÁS" || (cmd.length() == 0 && idNum == 2)) {
    activarCanalSeguro(CANAL_ATRAS, "ATRAS", duracionMs);
  }
  else if (cmd == "GIRAR_IZQUIERDA" || (cmd.length() == 0 && idNum == 3)) {
    activarCanalSeguro(CANAL_GIRAR_IZQUIERDA, "GIRAR_IZQUIERDA", duracionMs);
  }
  else if (cmd == "GIRAR_DERECHA" || (cmd.length() == 0 && idNum == 4)) {
    activarCanalSeguro(CANAL_GIRAR_DERECHA, "GIRAR_DERECHA", duracionMs);
  }
  else if (cmd == "MOVER_IZQUIERDA" || (cmd.length() == 0 && idNum == 5)) {
    activarCanalSeguro(CANAL_MOVER_IZQUIERDA, "MOVER_IZQUIERDA", duracionMs);
  }
  else if (cmd == "MOVER_DERECHA" || (cmd.length() == 0 && idNum == 6)) {
    activarCanalSeguro(CANAL_MOVER_DERECHA, "MOVER_DERECHA", duracionMs);
  }
  else if (cmd == "SUBIR_BRAZO" || (cmd.length() == 0 && idNum == 7)) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_BRAZO_MS;
    activarCanalSeguro(CANAL_SUBIR_BRAZO, "SUBIR_BRAZO", dur);
  }
  else if (cmd == "BAJAR_BRAZO" || (cmd.length() == 0 && idNum == 8)) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_BRAZO_MS;
    activarCanalSeguro(CANAL_BAJAR_BRAZO, "BAJAR_BRAZO", dur);
  }
  else if (cmd == "LUZ_LED" || (cmd.length() == 0 && idNum == 9)) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(CANAL_LUZ_LED, "LUZ_LED", dur);
  }
  else if (cmd == "ACTIVAR_SONIDO" || (cmd.length() == 0 && idNum == 10)) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(CANAL_ACTIVAR_SONIDO, "ACTIVAR_SONIDO", dur);
  }
  else if (cmd == "DESACTIVAR_SONIDO" || (cmd.length() == 0 && idNum == 11)) {
    unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
    activarCanalSeguro(CANAL_DESACTIVAR_SONIDO, "DESACTIVAR_SONIDO", dur);
  }
  else if (cmd == "CONTROL_REMOTO" || (cmd.length() == 0 && idNum == 12)) {
    if (CANAL_CONTROL_REMOTO >= 0 && CANAL_CONTROL_REMOTO <= 15) {
      unsigned long dur = (duracionMs > 0) ? duracionMs : DURACION_AUXILIAR_MS;
      activarCanalSeguro(CANAL_CONTROL_REMOTO, "CONTROL_REMOTO", dur);
    } else {
      liberarSalidas("CONTROL_REMOTO (sin DEMO fisica)");
    }
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
      digitalWrite(LED_BUILTIN, HIGH); // Apagar LED azul (activo en LOW)
      if (wsConectado) {
        Serial.println(F("[WSS] Desconectado del servidor AWS. Pasando a estado seguro."));
      }
      wsConectado = false;
      // RN11 y RN15: Liberar salidas al perder comunicación
      liberarSalidas("Desconexion WSS");
      break;

    case WStype_CONNECTED:
      wsConectado = true;
      digitalWrite(LED_BUILTIN, LOW); // Encender LED azul fijo = conectado a AWS WSS
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
      if (doc.containsKey("codigo") && !doc["codigo"].isNull()) {
        if (doc["codigo"].is<const char*>()) {
          if (comando.length() == 0) comando = String((const char*)doc["codigo"]);
        } else if (codigo == -1) {
          codigo = doc["codigo"].as<int>();
        }
      }
      if (codigo == -1 && doc.containsKey("id_comando") && !doc["id_comando"].isNull()) {
        codigo = doc["id_comando"].as<int>();
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

  // Cambiar combinación de pines CLK/LATCH/DATA en vivo sin recompilar: C1..C6
  if ((entrada.startsWith("C") || entrada.startsWith("c")) && entrada.length() == 2) {
    int cNum = entrada.substring(1).toInt();
    const uint8_t combos[6][3] = {
      {D5, D6, D7}, {D5, D7, D6},
      {D6, D5, D7}, {D6, D7, D5},
      {D7, D5, D6}, {D7, D6, D5}
    };
    const char* nombres[6] = {
      "Combo 1: CLK=D5, LATCH=D6, DATA=D7",
      "Combo 2: CLK=D5, LATCH=D7, DATA=D6",
      "Combo 3: CLK=D6, LATCH=D5, DATA=D7",
      "Combo 4: CLK=D6, LATCH=D7, DATA=D5",
      "Combo 5: CLK=D7, LATCH=D5, DATA=D6",
      "Combo 6: CLK=D7, LATCH=D6, DATA=D5"
    };
    if (cNum >= 1 && cNum <= 6) {
      PIN_CLOCK = combos[cNum - 1][0];
      PIN_LATCH = combos[cNum - 1][1];
      PIN_DATA  = combos[cNum - 1][2];
      pinMode(PIN_CLOCK, OUTPUT);
      pinMode(PIN_LATCH, OUTPUT);
      pinMode(PIN_DATA, OUTPUT);
      escribirRegistros595(0x0000);
      Serial.print(F("[PINES] Activo -> "));
      Serial.println(nombres[cNum - 1]);
      Serial.println(F("Ahora escribe TEST_CANALES para probar del 0 al 11 uno por uno."));
    }
    return;
  }

  // Modo diagnóstico de pines D5/D6/D7: prueba las 6 combinaciones de CLK/LATCH/DATA con 0xFFFF
  if (entrada.equalsIgnoreCase("TEST_PINES")) {
    const uint8_t combos[6][3] = {
      {D5, D6, D7}, {D5, D7, D6},
      {D6, D5, D7}, {D6, D7, D5},
      {D7, D5, D6}, {D7, D6, D5}
    };
    const char* nombres[6] = {
      "Combo 1: CLK=D5, LATCH=D6, DATA=D7",
      "Combo 2: CLK=D5, LATCH=D7, DATA=D6",
      "Combo 3: CLK=D6, LATCH=D5, DATA=D7",
      "Combo 4: CLK=D6, LATCH=D7, DATA=D5",
      "Combo 5: CLK=D7, LATCH=D5, DATA=D6",
      "Combo 6: CLK=D7, LATCH=D6, DATA=D5"
    };
    Serial.println(F("[TEST_PINES] Probando las 6 combinaciones en D5/D6/D7 (todos los focos ON)..."));
    for (int i = 0; i < 6; i++) {
      uint8_t c = combos[i][0], l = combos[i][1], d = combos[i][2];
      pinMode(c, OUTPUT);
      pinMode(l, OUTPUT);
      pinMode(d, OUTPUT);
      Serial.println(nombres[i]);
      digitalWrite(l, LOW);
      shiftOut(d, c, MSBFIRST, 0xFF);
      shiftOut(d, c, MSBFIRST, 0xFF);
      digitalWrite(l, HIGH);
      delay(1500);
      digitalWrite(l, LOW);
      shiftOut(d, c, MSBFIRST, 0x00);
      shiftOut(d, c, MSBFIRST, 0x00);
      digitalWrite(l, HIGH);
      delay(300);
    }
    pinMode(PIN_CLOCK, OUTPUT);
    pinMode(PIN_LATCH, OUTPUT);
    pinMode(PIN_DATA, OUTPUT);
    escribirRegistros595(0x0000);
    Serial.println(F("[TEST_PINES] Fin. Dime en que numero de Combo se prendieron los focos verdes."));
    return;
  }

  // Modo prueba rápida de todos los canales 0..15 (~13 segundos total)
  if (entrada.equalsIgnoreCase("TEST_CANALES") || entrada.equalsIgnoreCase("ALL")) {
    Serial.println(F("[TEST_CANALES] Apagando salidas e iniciando barrido canal 0 -> 15..."));
    liberarSalidas("Inicio TEST_CANALES");
    for (int b = 0; b <= 15; b++) {
      Serial.print(F("Activando canal physical "));
      Serial.println(b);
      escribirRegistros595((uint16_t)(1U << b));
      delay(650);
      escribirRegistros595(0x0000);
      delay(200);
    }
    Serial.println(F("[TEST_CANALES] Barrido completo. Todas las salidas en 0x0000."));
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

  // Botón de reset Wi-Fi con pull-up interno y LED de estado WSS
  pinMode(PIN_RESET_WIFI, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH); // Apagado hasta conectar WSS

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
  Serial.println(F("Comandos Serial:          [C1..C6] | [TEST_CANALES] | [T0..T15] | [S] | [R]"));

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
