"""
Router FastAPI para el Módulo de Administración, RBAC y Auditoría (Práctica 4.3).
Rutas:
- /api/auth/login, /api/auth/me
- /api/admin/dashboard
- /api/admin/modelos
- /api/admin/unidades
- /api/admin/usuarios
- /api/admin/asignaciones
- /api/admin/auditoria
- /api/demos/editor/guardar
- /api/invitado/solicitar-prueba
"""
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.models.schemas_admin import (
    AsignacionCreate,
    AuthMeResponse,
    BitacoraAuditoriaOut,
    DashboardMetricasOut,
    DemoEditorCreate,
    LoginRequest,
    ModeloVehiculoCreate,
    ModeloVehiculoOut,
    SesionInvitadoRequest,
    SesionInvitadoOut,
    TokenResponse,
    UnidadFisicaCreate,
    UnidadFisicaOut,
    UsuarioCreate,
    UsuarioOut,
)
from app.repositories.admin_repository import admin_repository

router = APIRouter(tags=["Administración & RBAC (Práctica 4.3)"])


# ------------------------------------------------------------------------------
# 2. DASHBOARD Y MÉTRICAS
# ------------------------------------------------------------------------------
@router.get(
    "/api/admin/dashboard",
    response_model=DashboardMetricasOut,
    summary="Métricas globales del sistema",
)
def dashboard_metricas() -> Dict[str, Any]:
    """Retorna métricas reales consolidadas de Amazon RDS."""
    return admin_repository.obtener_metricas_dashboard()


# ------------------------------------------------------------------------------
# 3. CATÁLOGO DE MODELOS COMERCIALES
# ------------------------------------------------------------------------------
@router.get(
    "/api/admin/modelos",
    response_model=List[ModeloVehiculoOut],
    summary="Listar catálogo de modelos comerciales",
)
def listar_modelos() -> List[Dict[str, Any]]:
    return admin_repository.obtener_modelos()


@router.post(
    "/api/admin/modelos",
    response_model=ModeloVehiculoOut,
    status_code=201,
    summary="Crear nuevo modelo comercial",
)
def crear_modelo(body: ModeloVehiculoCreate) -> Dict[str, Any]:
    return admin_repository.crear_modelo(
        nombre=body.nombre,
        fabricante=body.fabricante,
        categoria=body.categoria,
        especificaciones=body.especificaciones,
    )


# ------------------------------------------------------------------------------
# 4. INVENTARIO DE UNIDADES FÍSICAS (VIN / SERIE)
# ------------------------------------------------------------------------------
@router.get(
    "/api/admin/unidades",
    response_model=List[UnidadFisicaOut],
    summary="Listar inventario de unidades físicas",
)
def listar_unidades() -> List[Dict[str, Any]]:
    return admin_repository.obtener_unidades_completas()


@router.post(
    "/api/admin/unidades",
    status_code=201,
    summary="Registrar nueva unidad física con VIN",
)
def crear_unidad(body: UnidadFisicaCreate) -> Dict[str, Any]:
    return admin_repository.crear_unidad(
        nombre=body.nombre,
        id_modelo=body.id_modelo,
        numero_serie=body.numero_serie,
        microcontrolador=body.microcontrolador,
        descripcion=body.descripcion,
        id_usuario_propietario=body.id_usuario_propietario,
        es_exhibicion=body.es_exhibicion,
    )


# ------------------------------------------------------------------------------
# 5. GESTIÓN DE USUARIOS Y ASIGNACIONES
# ------------------------------------------------------------------------------
@router.get(
    "/api/admin/usuarios",
    response_model=List[UsuarioOut],
    summary="Listar usuarios y roles",
)
def listar_usuarios() -> List[Dict[str, Any]]:
    return admin_repository.obtener_usuarios()


@router.post(
    "/api/admin/usuarios",
    status_code=201,
    summary="Registrar nuevo usuario",
)
def crear_usuario(body: UsuarioCreate) -> Dict[str, Any]:
    return admin_repository.crear_usuario(
        nombre_completo=body.nombre_completo,
        email=body.email,
        password_hash=body.password,
        id_rol=body.id_rol,
    )


@router.post("/api/admin/asignaciones", summary="Asignar vehículo a comprador")
@router.post("/api/admin/asignar", summary="Asignar vehículo a comprador (alias)")
def asignar_unidad_a_usuario(body: AsignacionCreate) -> Dict[str, Any]:
    """Asigna formalmente una unidad a un comprador en Amazon RDS."""
    return admin_repository.asignar_unidad(
        id_vehiculo=body.id_vehiculo,
        id_usuario=body.id_usuario,
        notas=body.notas or body.tipo_operacion,
    )


# ------------------------------------------------------------------------------
# 6. BITÁCORA DE AUDITORÍA
# ------------------------------------------------------------------------------
@router.get(
    "/api/admin/auditoria",
    response_model=List[BitacoraAuditoriaOut],
    summary="Consultar bitácora de auditoría inmutable",
)
def consultar_auditoria(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    return admin_repository.obtener_auditoria(limit=limit, offset=offset)


# ------------------------------------------------------------------------------
# 7. EDITOR DE DEMOS (GUARDADO ATÓMICO)
# ------------------------------------------------------------------------------
@router.post("/api/demos/editor/guardar", status_code=201, summary="Guardar demo desde el Editor")
def guardar_demo_editor(body: DemoEditorCreate) -> Dict[str, Any]:
    """Persiste una demo con sus pasos ordenados en Amazon RDS de forma atómica."""
    pasos_dict = [p.dict() for p in body.pasos]
    return admin_repository.guardar_demo_con_pasos(
        id_vehiculo=body.id_vehiculo,
        nombre=body.nombre,
        descripcion=body.descripcion,
        pasos=pasos_dict,
        id_usuario_creador=body.id_usuario_creador,
        es_fabrica=body.es_fabrica,
    )
