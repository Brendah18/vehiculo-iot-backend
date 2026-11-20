-- ==============================================================================
-- PRÁCTICA 4.3: MIGRACIÓN DDL Y PROCEDIMIENTOS DE ADMINISTRACIÓN (RBAC & IOT)
-- Base de Datos: Amazon RDS MySQL (`vehiculo_iot`)
-- Garantía: No elimina ni altera el historial existente en `historial_comandos`
-- Compatibilidad: Sin cláusulas DEFINER para compatibilidad total con Amazon RDS
-- ==============================================================================

USE `vehiculo_iot`;

-- ------------------------------------------------------------------------------
-- 1. TABLA DE ROLES DEL SISTEMA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `roles` (
  `id_rol` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(30) NOT NULL UNIQUE,
  `descripcion` varchar(150) DEFAULT NULL,
  PRIMARY KEY (`id_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO `roles` (`id_rol`, `nombre`, `descripcion`) VALUES
(1, 'ADMINISTRADOR', 'Empresa: Gestión completa de inventario, flota, modelos, ventas y demos'),
(2, 'USUARIO', 'Comprador: Operación y monitoreo exclusivo de sus vehículos asignados'),
(3, 'INVITADO', 'Prospecto: Prueba limitada temporal con comandos restringidos');

-- ------------------------------------------------------------------------------
-- 2. TABLA DE USUARIOS DEL SISTEMA (RBAC)
-- ------------------------------------------------------------------------------
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

INSERT IGNORE INTO `usuarios` (`id_usuario`, `id_rol`, `nombre_completo`, `email`, `password_hash`) VALUES
(1, 1, 'Brenda Hernandez (Admin)', 'admin@vehiculoiot.com', 'admin_hash_2026'),
(2, 2, 'Carlos Mendoza (Comprador)', 'carlos@cliente.com', 'user_hash_2026'),
(3, 3, 'Invitado Demo Temporal', 'prospecto@demo.com', 'guest_hash_2026');

-- ------------------------------------------------------------------------------
-- 3. TABLA DE MODELOS COMERCIALES (CATÁLOGO DE PRODUCTOS)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `modelos_vehiculo` (
  `id_modelo` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(80) NOT NULL UNIQUE,
  `fabricante` varchar(80) NOT NULL DEFAULT 'IoT Robotics Corp',
  `categoria` varchar(50) NOT NULL DEFAULT 'Excavadora Pesada',
  `especificaciones` text DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  `fecha_creacion` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_modelo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO `modelos_vehiculo` (`id_modelo`, `nombre`, `categoria`, `especificaciones`) VALUES
(1, 'Excavadora CAT-IoT 320', 'Excavadora Hidráulica', 'Oruga de alta tracción, pala articulada 180°, sensor ultrasónico'),
(2, 'Minicargador Bobcat S70 IoT', 'Maquinaria Compacta', 'Radio de giro cero, pala de carga rápida, doble motorreductor');

-- ------------------------------------------------------------------------------
-- 4. ADICIÓN SEGURA DE COLUMNAS A LA TABLA `vehiculos` (UNIDADES FÍSICAS)
-- ------------------------------------------------------------------------------
SET @dbname = DATABASE();
SET @tablename = 'vehiculos';

-- Columna id_modelo
SET @colname = 'id_modelo';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @colname) > 0,
  'SELECT 1',
  'ALTER TABLE `vehiculos` ADD COLUMN `id_modelo` int DEFAULT 1 AFTER `modelo`'
));
PREPARE stmtAlter1 FROM @preparedStatement;
EXECUTE stmtAlter1;
DEALLOCATE PREPARE stmtAlter1;

-- Columna numero_serie (VIN / Serie Único)
SET @colname = 'numero_serie';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @colname) > 0,
  'SELECT 1',
  'ALTER TABLE `vehiculos` ADD COLUMN `numero_serie` varchar(50) DEFAULT NULL AFTER `id_modelo`'
));
PREPARE stmtAlter2 FROM @preparedStatement;
EXECUTE stmtAlter2;
DEALLOCATE PREPARE stmtAlter2;

-- Columna id_usuario_propietario
SET @colname = 'id_usuario_propietario';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @colname) > 0,
  'SELECT 1',
  'ALTER TABLE `vehiculos` ADD COLUMN `id_usuario_propietario` int DEFAULT 2 AFTER `numero_serie`'
));
PREPARE stmtAlter3 FROM @preparedStatement;
EXECUTE stmtAlter3;
DEALLOCATE PREPARE stmtAlter3;

-- Columna es_exhibicion (Flag para pruebas públicas de invitados)
SET @colname = 'es_exhibicion';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @colname) > 0,
  'SELECT 1',
  'ALTER TABLE `vehiculos` ADD COLUMN `es_exhibicion` tinyint(1) NOT NULL DEFAULT 1 AFTER `id_usuario_propietario`'
));
PREPARE stmtAlter4 FROM @preparedStatement;
EXECUTE stmtAlter4;
DEALLOCATE PREPARE stmtAlter4;

-- Asignar valores iniciales de identificación al Vehículo 1 existente
UPDATE `vehiculos` 
   SET `id_modelo` = 1,
       `numero_serie` = IFNULL(`numero_serie`, 'VIN-EXC-2026-001'),
       `id_usuario_propietario` = 2,
       `es_exhibicion` = 1
 WHERE `id_vehiculo` = 1;

-- ------------------------------------------------------------------------------
-- 5. TABLA DE HISTORIAL DE ASIGNACIONES (VENTAS / ASIGNACIONES A CLIENTES)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `asignaciones_vehiculo` (
  `id_asignacion` int NOT NULL AUTO_INCREMENT,
  `id_vehiculo` int NOT NULL,
  `id_usuario` int NOT NULL,
  `tipo_operacion` varchar(30) NOT NULL DEFAULT 'VENTA',
  `fecha_asignacion` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `notas` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id_asignacion`),
  KEY `fk_asig_vehiculo` (`id_vehiculo`),
  KEY `fk_asig_usuario` (`id_usuario`),
  CONSTRAINT `fk_asig_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON UPDATE CASCADE,
  CONSTRAINT `fk_asig_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO `asignaciones_vehiculo` (`id_asignacion`, `id_vehiculo`, `id_usuario`, `tipo_operacion`, `notas`) VALUES
(1, 1, 2, 'VENTA', 'Asignación inicial al Comprador Carlos Mendoza');

-- ------------------------------------------------------------------------------
-- 6. TABLA DE SESIONES TEMPORALES DE INVITADOS (PRUEBA DE 5 MINUTOS)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sesiones_invitado` (
  `id_sesion` int NOT NULL AUTO_INCREMENT,
  `token_sesion` varchar(64) NOT NULL UNIQUE,
  `id_vehiculo` int NOT NULL,
  `email_invitado` varchar(100) DEFAULT NULL,
  `fecha_inicio` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_expiracion` timestamp NULL,
  `activa` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_sesion`),
  KEY `fk_sesion_vehiculo` (`id_vehiculo`),
  CONSTRAINT `fk_sesion_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ------------------------------------------------------------------------------
-- 7. TABLA DE BITÁCORA DE AUDITORÍA (SEGURIDAD Y TRAZABILIDAD)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `bitacora_auditoria` (
  `id_auditoria` bigint NOT NULL AUTO_INCREMENT,
  `id_usuario` int DEFAULT NULL,
  `accion` varchar(60) NOT NULL,
  `entidad_afectada` varchar(60) NOT NULL,
  `detalle` text DEFAULT NULL,
  `direccion_ip` varchar(45) DEFAULT NULL,
  `fecha_hora` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_auditoria`),
  KEY `fk_audit_usuario` (`id_usuario`),
  CONSTRAINT `fk_audit_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO `bitacora_auditoria` (`id_usuario`, `accion`, `entidad_afectada`, `detalle`, `direccion_ip`) VALUES
(1, 'MIGRACION_INICIAL', 'SISTEMA', 'Migración segura a Práctica 4.3 completada sin alterar historial_comandos', '127.0.0.1');

-- ------------------------------------------------------------------------------
-- 8. AJUSTE DE TIEMPOS DE DEMO (PARA QUE VAYA MÁS LENTO Y SEA VISIBLE)
-- Aumentamos los tiempos en demo_movimientos a un rango cómodo (2500ms y pausas de 1200ms)
-- ------------------------------------------------------------------------------
UPDATE `demo_movimientos`
   SET `duracion_ms` = CASE 
         WHEN `duracion_ms` < 2000 THEN 2500
         ELSE `duracion_ms`
       END,
       `pausa_ms` = CASE
         WHEN `pausa_ms` < 1000 THEN 1200
         ELSE `pausa_ms`
       END
 WHERE `id_demo` = 1;

-- ------------------------------------------------------------------------------
-- 9. STORED PROCEDURES DE ADMINISTRACIÓN (SIN CLAUSULA DEFINER)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_admin_dashboard_metricas`;
DELIMITER ;;
CREATE PROCEDURE `sp_admin_dashboard_metricas`()
BEGIN
    SELECT 
        (SELECT COUNT(*) FROM vehiculos WHERE activo = 1) AS total_unidades,
        (SELECT COUNT(*) FROM vehiculos WHERE id_usuario_propietario IS NOT NULL AND activo = 1) AS unidades_vendidas,
        (SELECT COUNT(*) FROM vehiculos WHERE id_usuario_propietario IS NULL AND activo = 1) AS unidades_stock,
        (SELECT COUNT(*) FROM usuarios WHERE activo = 1) AS total_usuarios,
        (SELECT COUNT(*) FROM modelos_vehiculo WHERE activo = 1) AS total_modelos,
        (SELECT COUNT(*) FROM historial_comandos) AS total_comandos_historico;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_admin_obtener_unidades_completas`;
DELIMITER ;;
CREATE PROCEDURE `sp_admin_obtener_unidades_completas`()
BEGIN
    SELECT 
        v.id_vehiculo,
        v.nombre,
        v.numero_serie,
        v.microcontrolador,
        v.activo,
        v.es_exhibicion,
        m.id_modelo,
        m.nombre AS nombre_modelo,
        m.categoria,
        u.id_usuario AS id_propietario,
        u.nombre_completo AS nombre_propietario,
        u.email AS email_propietario,
        ev.conectado,
        ev.fecha_actualizacion AS ultimo_estado_fecha,
        c.nombre AS ultimo_comando
    FROM vehiculos v
    LEFT JOIN modelos_vehiculo m ON m.id_modelo = v.id_modelo
    LEFT JOIN usuarios u ON u.id_usuario = v.id_usuario_propietario
    LEFT JOIN estado_vehiculo ev ON ev.id_vehiculo = v.id_vehiculo
    LEFT JOIN comandos c ON c.id_comando = ev.id_comando
    ORDER BY v.id_vehiculo ASC;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_admin_asignar_unidad`;
DELIMITER ;;
CREATE PROCEDURE `sp_admin_asignar_unidad`(
    IN p_id_vehiculo INT,
    IN p_id_usuario INT,
    IN p_notas VARCHAR(255)
)
BEGIN
    UPDATE vehiculos 
       SET id_usuario_propietario = p_id_usuario 
     WHERE id_vehiculo = p_id_vehiculo;
     
    INSERT INTO asignaciones_vehiculo (id_vehiculo, id_usuario, tipo_operacion, notas)
    VALUES (p_id_vehiculo, p_id_usuario, 'ASIGNACION', p_notas);
    
    INSERT INTO bitacora_auditoria (id_usuario, accion, entidad_afectada, detalle)
    VALUES (p_id_usuario, 'ASIGNACION_UNIDAD', 'vehiculos', CONCAT('Unidad ', p_id_vehiculo, ' asignada a usuario ', p_id_usuario));
    
    SELECT p_id_vehiculo AS id_vehiculo, p_id_usuario AS id_usuario, 'ASIGNADO_EXITOSAMENTE' AS status;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_crear_sesion_invitado`;
DELIMITER ;;
CREATE PROCEDURE `sp_crear_sesion_invitado`(
    IN p_token VARCHAR(64),
    IN p_id_vehiculo INT,
    IN p_email VARCHAR(100),
    IN p_duracion_minutos INT
)
BEGIN
    INSERT INTO sesiones_invitado (token_sesion, id_vehiculo, email_invitado, fecha_expiracion, activa)
    VALUES (p_token, p_id_vehiculo, p_email, DATE_ADD(NOW(), INTERVAL p_duracion_minutos MINUTE), 1);
    
    SELECT LAST_INSERT_ID() AS id_sesion, p_token AS token_sesion, DATE_ADD(NOW(), INTERVAL p_duracion_minutos MINUTE) AS fecha_expiracion;
END ;;
DELIMITER ;

-- ==============================================================================
-- VALIDACIÓN FINAL DE SEGURIDAD (CONSERVACIÓN DE HISTORIAL DE PRÁCTICAS 4.1/4.2)
-- ==============================================================================
SELECT 'historial_comandos' AS tabla_intacta, COUNT(*) AS registros_conservados FROM historial_comandos;
