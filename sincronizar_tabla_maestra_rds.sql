-- ==============================================================================
-- SINCRONIZACIÓN MAESTRA 1 A 1 DE COMANDOS (AMAZON RDS MYSQL)
-- Vehículo: id_vehiculo = 1 (Excavadora IoT)
-- Garantiza mapeo idéntico en RDS, FastAPI, WebSocket, Frontend y Arduino (.ino)
-- Sin DELETE sobre historial_comandos ni pérdida de registros históricos.
-- ==============================================================================

USE `vehiculo_iot`;

-- 1. Reubicar temporalmente códigos/nombres previos en id_vehiculo = 1 para evitar colisiones UNIQUE
UPDATE `comandos`
   SET `codigo` = `id_comando` + 2000,
       `nombre` = CONCAT('LEGACY_CMD_', `id_comando`),
       `activo` = 0
 WHERE `id_vehiculo` = 1;

-- 2. Insertar o actualizar la Tabla Maestra Única (IDs 1..13 exactos)
INSERT INTO `comandos` (`id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`) VALUES
(1,  1, 'ADELANTE',          1,  'Desplazamiento físico hacia adelante', 1),
(2,  1, 'ATRAS',             2,  'Desplazamiento físico hacia atrás', 1),
(3,  1, 'GIRAR_IZQUIERDA',   3,  'Giro a la izquierda', 1),
(4,  1, 'GIRAR_DERECHA',     4,  'Giro a la derecha', 1),
(5,  1, 'MOVER_IZQUIERDA',   5,  'Desplazamiento lateral izquierda / giro cabina izq.', 1),
(6,  1, 'MOVER_DERECHA',     6,  'Desplazamiento lateral derecha / giro cabina der.', 1),
(7,  1, 'SUBIR_BRAZO',       7,  'Elevación del brazo/garra', 1),
(8,  1, 'BAJAR_BRAZO',       8,  'Descenso del brazo/garra', 1),
(9,  1, 'LUZ_LED',           9,  'Encendido o apagado real de iluminación LED', 1),
(10, 1, 'ACTIVAR_SONIDO',    10, 'Encendido del sonido/buzzer', 1),
(11, 1, 'DESACTIVAR_SONIDO', 11, 'Apagado del sonido/buzzer', 1),
(12, 1, 'CONTROL_REMOTO',    12, 'Encendido o apagado de control remoto', 1),
(13, 1, 'DETENER',           13, 'Paro total inmediato de todos los motores/actuadores', 1)
ON DUPLICATE KEY UPDATE
  `id_vehiculo` = VALUES(`id_vehiculo`),
  `nombre`      = VALUES(`nombre`),
  `codigo`      = VALUES(`codigo`),
  `descripcion` = VALUES(`descripcion`),
  `activo`      = 1;

-- 3. Verificar alineación exacta 1 a 1
SELECT `id_comando`, `codigo`, `nombre`, `descripcion`, `activo`
  FROM `comandos`
 WHERE `id_vehiculo` = 1 AND `activo` = 1
 ORDER BY `id_comando` ASC;
