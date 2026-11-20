-- ==============================================================================
-- MIGRACIÓN SEGURA E IDEMPOTENTE: CATÁLOGO DE 11 COMANDOS OPERATIVOS (NO.555-104)
-- Base de Datos: Amazon RDS for MySQL (`vehiculo_iot`)
-- Vehículo Destino: `id_vehiculo = 1` (Excavadora IoT)
-- Garantías:
--   1. PROHIBIDO borrar comandos existentes (0 DELETE).
--   2. PROHIBIDO cambiar IDs históricos (1..9 se mantienen intactos).
--   3. PROHIBIDO alterar `historial_comandos` o `demo_movimientos`.
--   4. Respeta UNIQUE KEY `uq_comando_codigo` (id_vehiculo, codigo)
--      y UNIQUE KEY `uq_comando_nombre` (id_vehiculo, nombre).
-- ==============================================================================

USE `vehiculo_iot`;

-- 1. Asegurar que los comandos base (1, 2 y 9) existan (idempotente)
INSERT IGNORE INTO `comandos` (`id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`) VALUES
(1, 1, 'AVANZAR',    1, 'Tracción adelante - Forward', 1),
(2, 1, 'RETROCEDER', 2, 'Tracción atrás - Backward', 1),
(9, 1, 'DETENER',    9, 'Paro total prioritario', 1);

-- 2. Agregar únicamente los comandos faltantes hasta completar los 11 comandos
--    operativos del control físico NO.555-104 para id_vehiculo = 1.
--    Se asignan códigos 10..17 para no colisionar con los códigos históricos 3..8.
INSERT IGNORE INTO `comandos` (`id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`) VALUES
(10, 1, 'IZQUIERDA',  10, 'Giro de oruga izquierda - Turn track left', 1),
(11, 1, 'DERECHA',    11, 'Giro de oruga derecha - Turn track right', 1),
(12, 1, 'CABINA_IZQ', 12, 'Giro de torreta izquierda - Turn turntable left', 1),
(13, 1, 'CABINA_DER', 13, 'Giro de torreta derecha - Turn turntable right', 1),
(14, 1, 'EXCAVAR',    14, 'Acción de excavación con brazo/pala - Dig', 1),
(15, 1, 'LUZ',        15, 'Encender/Apagar luz - Light ON/OFF', 1),
(16, 1, 'SONIDO',     16, 'Encender/Apagar música/sonido - Music ON/OFF', 1),
(17, 1, 'VELOCIDAD',  17, 'Cambio de nivel de velocidad - Speed', 1);

-- 3. Verificación del catálogo de 11 comandos operativos activos para id_vehiculo = 1
SELECT `id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`
  FROM `comandos`
 WHERE `id_vehiculo` = 1
   AND `nombre` IN (
       'AVANZAR', 'RETROCEDER', 'IZQUIERDA', 'DERECHA', 'DETENER',
       'CABINA_IZQ', 'CABINA_DER', 'EXCAVAR', 'LUZ', 'SONIDO', 'VELOCIDAD'
   )
 ORDER BY `codigo` ASC;

-- 4. Confirmar que el historial de comandos permanece 100% intacto
SELECT COUNT(*) AS `total_historial_intacto` FROM `historial_comandos` WHERE `id_vehiculo` = 1;
