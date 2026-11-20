-- ==============================================================================
-- PRÁCTICA 4.3: SCRIPT DE REVERSIÓN LIMPIA (DOWN / ROLLBACK)
-- Base de Datos: Amazon RDS MySQL (`vehiculo_iot`)
-- Propósito: Deshacer las adiciones de la Práctica 4.3 en entornos de prueba
-- Garantía: No toca ni elimina historial_comandos, comandos ni estado_vehiculo
-- ==============================================================================

USE `vehiculo_iot`;

-- 1. Eliminar procedimientos almacenados agregados
DROP PROCEDURE IF EXISTS `sp_crear_sesion_invitado`;
DROP PROCEDURE IF EXISTS `sp_admin_asignar_unidad`;
DROP PROCEDURE IF EXISTS `sp_admin_obtener_unidades_completas`;
DROP PROCEDURE IF EXISTS `sp_admin_dashboard_metricas`;

-- 2. Eliminar tablas agregadas en orden referencial inverso
DROP TABLE IF EXISTS `sesiones_invitado`;
DROP TABLE IF EXISTS `bitacora_auditoria`;
DROP TABLE IF EXISTS `asignaciones_vehiculo`;
DROP TABLE IF EXISTS `usuarios`;
DROP TABLE IF EXISTS `roles`;
DROP TABLE IF EXISTS `modelos_vehiculo`;

-- 3. Restaurar columnas agregadas a la tabla vehiculos (Opcional si se requiere limpiar columnas)
-- ALTER TABLE `vehiculos` DROP COLUMN `es_exhibicion`;
-- ALTER TABLE `vehiculos` DROP COLUMN `id_usuario_propietario`;
-- ALTER TABLE `vehiculos` DROP COLUMN `numero_serie`;
-- ALTER TABLE `vehiculos` DROP COLUMN `id_modelo`;

-- 4. Validar que la base original sigue completa
SELECT 'historial_comandos' AS tabla_intacta, COUNT(*) AS total FROM historial_comandos;
