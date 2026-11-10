-- Active: 1792306971153@@instancia-rds-iot.cdwcf741lvnq.us-east-1.rds.amazonaws.com@3306@vehiculo_iot
-- ==============================================================================
-- FASE 1: SCRIPT COMPLETO DE 21 STORED PROCEDURES Y ESTRUCTURA (MYSQL / RDS)
-- Base de datos: vehiculo_iot
-- Nota: Sin cláusulas DEFINER para compatibilidad total con Amazon RDS
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS `vehiculo_iot`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE `vehiculo_iot`;

-- ==============================================================================
-- 1. ESTRUCTURA DE LAS 6 TABLAS (SI NO EXISTEN)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `vehiculos` (
  `id_vehiculo` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(80) NOT NULL,
  `modelo` varchar(80) DEFAULT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `microcontrolador` varchar(50) DEFAULT NULL,
  `fecha_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_vehiculo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `comandos` (
  `id_comando` int NOT NULL AUTO_INCREMENT,
  `id_vehiculo` int NOT NULL,
  `nombre` varchar(60) NOT NULL,
  `codigo` int NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_comando`),
  UNIQUE KEY `uq_comando_codigo` (`id_vehiculo`,`codigo`),
  UNIQUE KEY `uq_comando_nombre` (`id_vehiculo`,`nombre`),
  CONSTRAINT `fk_comando_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `estado_vehiculo` (
  `id_estado` int NOT NULL AUTO_INCREMENT,
  `id_vehiculo` int NOT NULL,
  `id_comando` int DEFAULT NULL,
  `fecha_actualizacion` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `conectado` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id_estado`),
  UNIQUE KEY `id_vehiculo` (`id_vehiculo`),
  KEY `fk_estado_comando` (`id_comando`),
  CONSTRAINT `fk_estado_comando` FOREIGN KEY (`id_comando`) REFERENCES `comandos` (`id_comando`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_estado_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `historial_comandos` (
  `id_historial` bigint NOT NULL AUTO_INCREMENT,
  `id_vehiculo` int NOT NULL,
  `id_comando` int DEFAULT NULL,
  `fecha_hora` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `origen` varchar(30) NOT NULL DEFAULT 'MANUAL',
  PRIMARY KEY (`id_historial`),
  KEY `fk_historial_vehiculo` (`id_vehiculo`),
  KEY `fk_historial_comando` (`id_comando`),
  CONSTRAINT `fk_historial_comando` FOREIGN KEY (`id_comando`) REFERENCES `comandos` (`id_comando`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_historial_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `demos` (
  `id_demo` int NOT NULL AUTO_INCREMENT,
  `id_vehiculo` int NOT NULL,
  `nombre` varchar(80) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id_demo`),
  KEY `fk_demo_vehiculo` (`id_vehiculo`),
  CONSTRAINT `fk_demo_vehiculo` FOREIGN KEY (`id_vehiculo`) REFERENCES `vehiculos` (`id_vehiculo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `demo_movimientos` (
  `id_demo_movimiento` int NOT NULL AUTO_INCREMENT,
  `id_demo` int NOT NULL,
  `id_comando` int NOT NULL,
  `orden` int NOT NULL,
  `duracion_ms` int unsigned NOT NULL,
  `pausa_ms` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id_demo_movimiento`),
  UNIQUE KEY `uq_demo_orden` (`id_demo`,`orden`),
  KEY `fk_mov_comando` (`id_comando`),
  CONSTRAINT `fk_mov_comando` FOREIGN KEY (`id_comando`) REFERENCES `comandos` (`id_comando`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_mov_demo` FOREIGN KEY (`id_demo`) REFERENCES `demos` (`id_demo`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ==============================================================================
-- 2. LOS 21 STORED PROCEDURES (SIN DEFINER PARA AMAZON RDS)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- GRUPO A: VEHÍCULOS (5 SPs)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_crear_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_crear_vehiculo`(
    IN p_nombre VARCHAR(80),
    IN p_modelo VARCHAR(80),
    IN p_descripcion VARCHAR(255),
    IN p_microcontrolador VARCHAR(50)
)
BEGIN
    INSERT INTO vehiculos(nombre, modelo, descripcion, microcontrolador)
    VALUES(p_nombre, p_modelo, p_descripcion, p_microcontrolador);
    SELECT LAST_INSERT_ID() AS id_vehiculo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_vehiculos`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_vehiculos`()
BEGIN
    SELECT * FROM vehiculos ORDER BY id_vehiculo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_vehiculo`(IN p_id_vehiculo INT)
BEGIN
    SELECT * FROM vehiculos WHERE id_vehiculo = p_id_vehiculo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_actualizar_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_actualizar_vehiculo`(
    IN p_id_vehiculo INT,
    IN p_nombre VARCHAR(80),
    IN p_modelo VARCHAR(80),
    IN p_descripcion VARCHAR(255),
    IN p_microcontrolador VARCHAR(50),
    IN p_activo BOOLEAN
)
BEGIN
    UPDATE vehiculos
       SET nombre=p_nombre, modelo=p_modelo, descripcion=p_descripcion,
           microcontrolador=p_microcontrolador, activo=p_activo
     WHERE id_vehiculo=p_id_vehiculo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_eliminar_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_eliminar_vehiculo`(IN p_id_vehiculo INT)
BEGIN
    DELETE FROM vehiculos WHERE id_vehiculo=p_id_vehiculo;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- GRUPO B: COMANDOS (5 SPs) -> Incluye sp_obtener_comando (#20)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_crear_comando`;
DELIMITER ;;
CREATE PROCEDURE `sp_crear_comando`(
    IN p_id_vehiculo INT,
    IN p_nombre VARCHAR(60),
    IN p_codigo INT,
    IN p_descripcion VARCHAR(255)
)
BEGIN
    INSERT INTO comandos(id_vehiculo,nombre,codigo,descripcion)
    VALUES(p_id_vehiculo,p_nombre,p_codigo,p_descripcion);
    SELECT LAST_INSERT_ID() AS id_comando;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_comandos_vehiculo`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_comandos_vehiculo`(IN p_id_vehiculo INT)
BEGIN
    SELECT * FROM comandos
     WHERE id_vehiculo=p_id_vehiculo
     ORDER BY codigo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_comando`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_comando`(IN p_id_comando INT)
BEGIN
    SELECT * FROM comandos WHERE id_comando = p_id_comando;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_actualizar_comando`;
DELIMITER ;;
CREATE PROCEDURE `sp_actualizar_comando`(
    IN p_id_comando INT,
    IN p_nombre VARCHAR(60),
    IN p_codigo INT,
    IN p_descripcion VARCHAR(255),
    IN p_activo BOOLEAN
)
BEGIN
    UPDATE comandos
       SET nombre=p_nombre, codigo=p_codigo,
           descripcion=p_descripcion, activo=p_activo
     WHERE id_comando=p_id_comando;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_eliminar_comando`;
DELIMITER ;;
CREATE PROCEDURE `sp_eliminar_comando`(IN p_id_comando INT)
BEGIN
    DELETE FROM comandos WHERE id_comando=p_id_comando;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- GRUPO C: ESTADO DEL VEHÍCULO (2 SPs)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_actualizar_estado`;
DELIMITER ;;
CREATE PROCEDURE `sp_actualizar_estado`(
    IN p_id_vehiculo INT,
    IN p_id_comando INT,
    IN p_conectado BOOLEAN
)
BEGIN
    INSERT INTO estado_vehiculo(id_vehiculo,id_comando,conectado)
    VALUES(p_id_vehiculo,p_id_comando,p_conectado)
    ON DUPLICATE KEY UPDATE
      id_comando=VALUES(id_comando),
      conectado=VALUES(conectado),
      fecha_actualizacion=CURRENT_TIMESTAMP;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_estado`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_estado`(IN p_id_vehiculo INT)
BEGIN
    SELECT e.id_vehiculo, v.nombre AS vehiculo,
           e.id_comando, c.nombre AS comando, c.codigo,
           e.conectado, e.fecha_actualizacion
      FROM estado_vehiculo e
      JOIN vehiculos v ON v.id_vehiculo=e.id_vehiculo
 LEFT JOIN comandos c ON c.id_comando=e.id_comando
     WHERE e.id_vehiculo=p_id_vehiculo;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- GRUPO D: HISTORIAL DE COMANDOS (2 SPs)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_registrar_historial`;
DELIMITER ;;
CREATE PROCEDURE `sp_registrar_historial`(
    IN p_id_vehiculo INT,
    IN p_id_comando INT,
    IN p_origen VARCHAR(30)
)
BEGIN
    INSERT INTO historial_comandos(id_vehiculo,id_comando,origen)
    VALUES(p_id_vehiculo,p_id_comando,p_origen);
    SELECT LAST_INSERT_ID() AS id_historial;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_historial`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_historial`(IN p_id_vehiculo INT)
BEGIN
    SELECT h.id_historial, h.id_vehiculo, h.id_comando,
           c.nombre AS comando, c.codigo,
           h.fecha_hora, h.origen
      FROM historial_comandos h
 LEFT JOIN comandos c ON c.id_comando=h.id_comando
     WHERE h.id_vehiculo=p_id_vehiculo
     ORDER BY h.fecha_hora DESC, h.id_historial DESC;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- GRUPO E: DEMOS (5 SPs) -> Incluye sp_obtener_demo (#21)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_crear_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_crear_demo`(
    IN p_id_vehiculo INT,
    IN p_nombre VARCHAR(80),
    IN p_descripcion VARCHAR(255)
)
BEGIN
    INSERT INTO demos(id_vehiculo,nombre,descripcion)
    VALUES(p_id_vehiculo,p_nombre,p_descripcion);
    SELECT LAST_INSERT_ID() AS id_demo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_demos`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_demos`(IN p_id_vehiculo INT)
BEGIN
    SELECT * FROM demos
     WHERE id_vehiculo=p_id_vehiculo
     ORDER BY id_demo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_demo`(IN p_id_demo INT)
BEGIN
    SELECT * FROM demos WHERE id_demo = p_id_demo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_actualizar_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_actualizar_demo`(
    IN p_id_demo INT,
    IN p_nombre VARCHAR(80),
    IN p_descripcion VARCHAR(255),
    IN p_activo BOOLEAN
)
BEGIN
    UPDATE demos
       SET nombre=p_nombre, descripcion=p_descripcion, activo=p_activo
     WHERE id_demo=p_id_demo;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_eliminar_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_eliminar_demo`(IN p_id_demo INT)
BEGIN
    DELETE FROM demos WHERE id_demo=p_id_demo;
END ;;
DELIMITER ;

-- ------------------------------------------------------------------------------
-- GRUPO F: MOVIMIENTOS DE DEMO (4 SPs)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_agregar_movimiento_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_agregar_movimiento_demo`(
    IN p_id_demo INT,
    IN p_id_comando INT,
    IN p_orden INT,
    IN p_duracion_ms INT,
    IN p_pausa_ms INT
)
BEGIN
    INSERT INTO demo_movimientos
      (id_demo,id_comando,orden,duracion_ms,pausa_ms)
    VALUES
      (p_id_demo,p_id_comando,p_orden,p_duracion_ms,p_pausa_ms);
    SELECT LAST_INSERT_ID() AS id_demo_movimiento;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_obtener_movimientos_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_obtener_movimientos_demo`(IN p_id_demo INT)
BEGIN
    SELECT dm.id_demo_movimiento, dm.id_demo, dm.orden,
           dm.id_comando, c.nombre AS comando, c.codigo,
           dm.duracion_ms, dm.pausa_ms
      FROM demo_movimientos dm
      JOIN comandos c ON c.id_comando=dm.id_comando
     WHERE dm.id_demo=p_id_demo
     ORDER BY dm.orden;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_actualizar_movimiento_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_actualizar_movimiento_demo`(
    IN p_id_demo_movimiento INT,
    IN p_id_comando INT,
    IN p_orden INT,
    IN p_duracion_ms INT,
    IN p_pausa_ms INT
)
BEGIN
    UPDATE demo_movimientos
       SET id_comando=p_id_comando, orden=p_orden,
           duracion_ms=p_duracion_ms, pausa_ms=p_pausa_ms
     WHERE id_demo_movimiento=p_id_demo_movimiento;
END ;;
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_eliminar_movimiento_demo`;
DELIMITER ;;
CREATE PROCEDURE `sp_eliminar_movimiento_demo`(IN p_id_demo_movimiento INT)
BEGIN
    DELETE FROM demo_movimientos
     WHERE id_demo_movimiento=p_id_demo_movimiento;
END ;;
DELIMITER ;
