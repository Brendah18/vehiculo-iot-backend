-- ==============================================================================
-- MIGRACIÓN INTEGRAL EXAMEN 3.1 & PRÁCTICA 4.3 (SEGURIDAD RBAC + 12 MOVIMIENTOS + DEMO)
-- Base de Datos: Amazon RDS for MySQL (`vehiculo_iot`)
-- Garantías Estrictas:
--   1. CERO DELETE sobre `comandos` y `historial_comandos` (historial 100% intacto).
--   2. Usuarios reales con contraseñas hasheadas (SHA-256) para Login Real:
--      - ADMINISTRADOR: admin@iot.com    / Admin123!
--      - USUARIO:       cliente@iot.com  / Cliente123! (Dueño de id_vehiculo = 1)
--      - INVITADO:      invitado@iot.com / Invitado123!
--   3. Catálogo exacto de los 12 Movimientos del Profesor (01..12) + 13 (DETENER).
--   4. Secuencia DEMO principal ajustada con tiempos seguros (1800ms / 900ms) y paro final.
-- ==============================================================================

USE `vehiculo_iot`;

-- ------------------------------------------------------------------------------
-- 1. ROLES Y USUARIOS REALES CON CONTRASEÑA HASHEADA (SHA2-256)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roles` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(30) NOT NULL UNIQUE,
  `descripcion` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `roles` (`id_rol`, `nombre`, `descripcion`) VALUES
(1, 'ADMINISTRADOR', 'Empresa: Gestión de flota, modelos, clientes, asignaciones y demos (sin operar unidades vendidas)'),
(2, 'USUARIO', 'Comprador: Operación y monitoreo exclusivo de sus vehículos asignados'),
(3, 'INVITADO', 'Prospecto: Prueba temporal exclusiva de 5 minutos (solo ADELANTE, ATRAS y DETENER)')
ON DUPLICATE KEY UPDATE
  `nombre` = VALUES(`nombre`),
  `descripcion` = VALUES(`descripcion`);

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `id_rol` int NOT NULL DEFAULT '2',
  `nombre_completo` varchar(120) NOT NULL,
  `email` varchar(100) NOT NULL UNIQUE,
  `password_hash` varchar(255) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `fecha_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_usuario`),
  KEY `fk_usuario_rol` (`id_rol`),
  CONSTRAINT `fk_usuario_rol` FOREIGN KEY (`id_rol`) REFERENCES `roles` (`id_rol`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insertar o actualizar los 3 perfiles oficiales con hash SHA2-256
INSERT INTO `usuarios` (`id_usuario`, `id_rol`, `nombre_completo`, `email`, `password_hash`, `activo`) VALUES
(1, 1, 'Brenda Hernandez (Admin)',    'admin@iot.com',    SHA2('Admin123!', 256),    1),
(2, 2, 'Carlos Mendoza (Comprador)',  'cliente@iot.com',  SHA2('Cliente123!', 256),  1),
(3, 3, 'Invitado Prueba Temporal',    'invitado@iot.com', SHA2('Invitado123!', 256), 1)
ON DUPLICATE KEY UPDATE
  `id_rol`          = VALUES(`id_rol`),
  `nombre_completo` = VALUES(`nombre_completo`),
  `email`           = VALUES(`email`),
  `password_hash`   = VALUES(`password_hash`),
  `activo`          = 1;

-- Asegurar que id_vehiculo = 1 esté asignado al Comprador (id_usuario = 2) y habilitado para exhibición
UPDATE `vehiculos`
   SET `id_usuario_propietario` = 2,
       `es_exhibicion` = 1,
       `activo` = 1
 WHERE `id_vehiculo` = 1;

-- ------------------------------------------------------------------------------
-- 2. CATÁLOGO EXACTO DE LOS 12 MOVIMIENTOS DEL PROFESOR (+ 13 DETENER)
--    Reubicación temporal sin DELETE para respetar UNIQUE(id_vehiculo, codigo)
--    y UNIQUE(id_vehiculo, nombre) conservando historial_comandos intacto.
-- ------------------------------------------------------------------------------
UPDATE `comandos`
   SET `codigo` = `id_comando` + 1000,
       `nombre` = CONCAT('HIST_CMD_', `id_comando`),
       `activo` = 0
 WHERE `id_vehiculo` = 1;

INSERT INTO `comandos` (`id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`) VALUES
(1,  1, 'ADELANTE',          1,  '01. ADELANTE — desplazamiento físico hacia adelante', 1),
(2,  1, 'ATRAS',             2,  '02. ATRÁS — desplazamiento físico hacia atrás', 1),
(3,  1, 'GIRAR_IZQUIERDA',   3,  '03. GIRAR IZQUIERDA — giro a la izquierda', 1),
(4,  1, 'GIRAR_DERECHA',     4,  '04. GIRAR DERECHA — giro a la derecha', 1),
(5,  1, 'MOVER_IZQUIERDA',   5,  '05. MOVER IZQUIERDA — desplazamiento lateral izquierda', 1),
(6,  1, 'MOVER_DERECHA',     6,  '06. MOVER DERECHA — desplazamiento lateral derecha', 1),
(7,  1, 'SUBIR_BRAZO',       7,  '07. SUBIR BRAZO — elevación del brazo o palanca', 1),
(8,  1, 'BAJAR_BRAZO',       8,  '08. BAJAR BRAZO — descenso del brazo o palanca', 1),
(9,  1, 'LUZ_LED',           9,  '09. LUZ / LED — encendido o apagado real de iluminación', 1),
(10, 1, 'ACTIVAR_SONIDO',    10, '10. ACTIVAR SONIDO — encendido del sonido', 1),
(11, 1, 'DESACTIVAR_SONIDO', 11, '11. DESACTIVAR SONIDO — apagado del sonido', 1),
(12, 1, 'CONTROL_REMOTO',    12, '12. CONTROL REMOTO — encendido o apagado de interfaz electrónica segura', 1),
(13, 1, 'DETENER',           13, '13. DETENER — paro total prioritario inmediato', 1)
ON DUPLICATE KEY UPDATE
  `id_vehiculo` = VALUES(`id_vehiculo`),
  `nombre`      = VALUES(`nombre`),
  `codigo`      = VALUES(`codigo`),
  `descripcion` = VALUES(`descripcion`),
  `activo`      = 1;

-- Actualizar SP sp_obtener_comandos_vehiculo para listar solo comandos activos ordenados por código
DROP PROCEDURE IF EXISTS `sp_obtener_comandos_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_comandos_vehiculo`(IN p_id_vehiculo INT)
BEGIN
    SELECT `id_comando`, `id_vehiculo`, `nombre`, `codigo`, `descripcion`, `activo`
      FROM `comandos`
     WHERE `id_vehiculo` = p_id_vehiculo
       AND `activo` = 1
     ORDER BY `codigo` ASC;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- 3. AJUSTE SEGURO DE LA DEMO PRINCIPAL (id_demo = 1) CON TIEMPOS VISIBLES
-- ------------------------------------------------------------------------------
DELETE FROM `demo_movimientos` WHERE `id_demo` = 1;

INSERT INTO `demo_movimientos` (`id_demo`, `id_comando`, `orden`, `duracion_ms`, `pausa_ms`) VALUES
(1, 1,  1, 1800, 900), -- Paso 1: ADELANTE
(1, 3,  2, 1600, 900), -- Paso 2: GIRAR_IZQUIERDA
(1, 7,  3, 1600, 900), -- Paso 3: SUBIR_BRAZO
(1, 8,  4, 1600, 900), -- Paso 4: BAJAR_BRAZO
(1, 9,  5, 1500, 800), -- Paso 5: LUZ_LED
(1, 2,  6, 1800, 900), -- Paso 6: ATRAS
(1, 13, 7, 1000, 0);   -- Paso 7: DETENER (Paro final seguro)

-- Poner estado actual del vehículo 1 en DETENER (id_comando = 13)
CALL sp_actualizar_estado(1, 13, 1);

-- ------------------------------------------------------------------------------
-- 4. VERIFICACIÓN FINAL
-- ------------------------------------------------------------------------------
SELECT `id_usuario`, `id_rol`, `nombre_completo`, `email`, `activo` FROM `usuarios` ORDER BY `id_usuario`;
CALL sp_obtener_comandos_vehiculo(1);
CALL sp_obtener_movimientos_demo(1);
SELECT COUNT(*) AS `historial_comandos_conservado` FROM `historial_comandos`;
