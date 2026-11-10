-- ==============================================================================
-- PRÁCTICA 2.4: BASE DE DATOS IoT EN AWS (AMAZON RDS FOR MYSQL)
-- Script de Verificación, Poblado mediante Stored Procedures y Validación
-- Conexión destino en VS Code (Database Client - cweijan): RDS-IoT
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- SECCIÓN A: VERIFICACIÓN PREVIA DE ESTRUCTURA MIGRADA (6 TABLAS Y 19 SPs)
-- ------------------------------------------------------------------------------
USE vehiculo_iot;

-- 1. Confirmar que las 6 tablas existen en el esquema remoto
SHOW TABLES;

-- 2. Confirmar que los 19 Stored Procedures fueron importados correctamente
SHOW PROCEDURE STATUS WHERE Db = 'vehiculo_iot';

-- 3. Confirmar que las 6 tablas están inicialmente vacías (0 registros)
SELECT 'vehiculos' AS tabla, COUNT(*) AS total_registros FROM vehiculos
UNION ALL
SELECT 'comandos', COUNT(*) FROM comandos
UNION ALL
SELECT 'estado_vehiculo', COUNT(*) FROM estado_vehiculo
UNION ALL
SELECT 'historial_comandos', COUNT(*) FROM historial_comandos
UNION ALL
SELECT 'demos', COUNT(*) FROM demos
UNION ALL
SELECT 'demo_movimientos', COUNT(*) FROM demo_movimientos;


-- ------------------------------------------------------------------------------
-- SECCIÓN B: POBLADO DE DATOS EN RDS EXCLUSIVAMENTE MEDIANTE STORED PROCEDURES
-- ------------------------------------------------------------------------------
USE vehiculo_iot;

-- 1. Crear vehículo principal (ID = 1)
CALL sp_crear_vehiculo('Excavadora IoT', 'Modelo X', 'Vehículo de construcción controlado por ESP8266', 'ESP8266');

-- 2. Registrar catálogo de 9 comandos para el vehículo 1
CALL sp_crear_comando(1,'AVANZAR',1,'Mover el vehículo hacia adelante');
CALL sp_crear_comando(1,'RETROCEDER',2,'Mover el vehículo hacia atrás');
CALL sp_crear_comando(1,'GIRAR_IZQUIERDA',3,'Giro hacia la izquierda');
CALL sp_crear_comando(1,'GIRAR_DERECHA',4,'Giro hacia la derecha');
CALL sp_crear_comando(1,'SUBIR_BRAZO',5,'Elevar el brazo');
CALL sp_crear_comando(1,'BAJAR_BRAZO',6,'Descender el brazo');
CALL sp_crear_comando(1,'ABRIR_PALA',7,'Abrir la pala');
CALL sp_crear_comando(1,'CERRAR_PALA',8,'Cerrar la pala');
CALL sp_crear_comando(1,'DETENER',9,'Detener cualquier movimiento');

-- 3. Actualizar el estado operativo inicial del vehículo 1 (Comando 9 = DETENER, En línea = 1)
CALL sp_actualizar_estado(1,9,1);

-- 4. Registrar eventos de prueba en el historial de comandos con origen 'VSCODE-RDS'
CALL sp_registrar_historial(1,1,'VSCODE-RDS');
CALL sp_registrar_historial(1,3,'VSCODE-RDS');
CALL sp_registrar_historial(1,5,'VSCODE-RDS');
CALL sp_registrar_historial(1,7,'VSCODE-RDS');
CALL sp_registrar_historial(1,9,'VSCODE-RDS');

-- 5. Crear secuencia de demostración principal (Demo ID = 1)
CALL sp_crear_demo(1, 'Demo principal', 'Secuencia automática de movimientos del vehículo');

-- 6. Agregar los 8 movimientos secuenciales a la Demo 1
CALL sp_agregar_movimiento_demo(1,1,1,2000,400);
CALL sp_agregar_movimiento_demo(1,3,2,1000,300);
CALL sp_agregar_movimiento_demo(1,5,3,1500,300);
CALL sp_agregar_movimiento_demo(1,7,4,900,250);
CALL sp_agregar_movimiento_demo(1,8,5,900,250);
CALL sp_agregar_movimiento_demo(1,6,6,1500,300);
CALL sp_agregar_movimiento_demo(1,2,7,2000,400);
CALL sp_agregar_movimiento_demo(1,9,8,500,0);


-- ------------------------------------------------------------------------------
-- SECCIÓN C: CONSULTAS DE COMPROBACIÓN Y EVIDENCIA FINAL EN RDS
-- ------------------------------------------------------------------------------
CALL sp_obtener_vehiculos();
CALL sp_obtener_comandos_vehiculo(1);
CALL sp_obtener_estado(1);
CALL sp_obtener_historial(1);
CALL sp_obtener_demos(1);
CALL sp_obtener_movimientos_demo(1);
