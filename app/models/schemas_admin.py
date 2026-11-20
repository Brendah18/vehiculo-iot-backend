"""
Esquemas Pydantic para la Práctica 4.3: Módulo de Administración, RBAC y Auditoría.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ==========================================
# 0. ESQUEMAS DE AUTENTICACIÓN Y SESIÓN
# ==========================================
class LoginRequest(BaseModel):
    email: str = Field(..., examples=["cliente@iot.com"])
    password: str = Field(..., min_length=4, examples=["Cliente123!"])


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    id_usuario: int
    nombre_completo: str
    email: str
    id_rol: int
    rol: str
    vehiculos_asignados: List[int] = Field(default_factory=lambda: [1])
    expira_en_segundos: Optional[int] = 28800


class AuthMeResponse(BaseModel):
    id_usuario: int
    nombre_completo: str
    email: str
    id_rol: int
    rol: str
    vehiculos_asignados: List[int] = Field(default_factory=list)


# ==========================================
# 1. ESQUEMAS DE MODELOS COMERCIALES
# ==========================================
class ModeloVehiculoCreate(BaseModel):
    nombre: str = Field(..., max_length=80, examples=["Excavadora CAT-IoT 320"])
    fabricante: str = Field("IoT Robotics Corp", max_length=80)
    categoria: str = Field("Excavadora Pesada", max_length=50)
    especificaciones: Optional[str] = Field(None, examples=["Pala 180°, oruga motorizada, ESP32"])


class ModeloVehiculoOut(BaseModel):
    id_modelo: int
    nombre: str
    fabricante: str
    categoria: str
    especificaciones: Optional[str] = None
    activo: bool
    fecha_creacion: Optional[datetime] = None


# ==========================================
# 2. ESQUEMAS DE UNIDADES FÍSICAS (VIN / SERIE)
# ==========================================
class UnidadFisicaCreate(BaseModel):
    nombre: str = Field(..., max_length=80, examples=["Excavadora IoT #2"])
    id_modelo: int = Field(..., examples=[1])
    numero_serie: str = Field(..., max_length=50, examples=["VIN-EXC-2026-002"])
    microcontrolador: str = Field("ESP8266", max_length=50)
    descripcion: Optional[str] = Field(None, max_length=255)
    id_usuario_propietario: Optional[int] = Field(None, examples=[2])
    es_exhibicion: bool = Field(False)


class UnidadFisicaOut(BaseModel):
    id_vehiculo: int
    nombre: str
    numero_serie: Optional[str] = None
    id_modelo: Optional[int] = None
    nombre_modelo: Optional[str] = None
    categoria: Optional[str] = None
    id_propietario: Optional[int] = None
    nombre_propietario: Optional[str] = None
    email_propietario: Optional[str] = None
    microcontrolador: Optional[str] = None
    activo: bool
    es_exhibicion: bool
    conectado: int
    ultimo_estado_fecha: Optional[str] = None
    ultimo_comando: Optional[str] = None


# ==========================================
# 3. ESQUEMAS DE USUARIOS Y ROLES (RBAC)
# ==========================================
class UsuarioCreate(BaseModel):
    nombre_completo: str = Field(..., max_length=120, examples=["Carlos Mendoza"])
    email: str = Field(..., examples=["cliente@iot.com"])
    password: str = Field(..., min_length=4, examples=["Cliente123!"])
    id_rol: int = Field(2, examples=[2])  # 1: ADMIN, 2: USUARIO, 3: INVITADO


class UsuarioOut(BaseModel):
    id_usuario: int
    nombre_completo: str
    email: str
    id_rol: int
    rol_nombre: Optional[str] = "USUARIO"
    activo: bool
    fecha_registro: Optional[datetime] = None


class AsignacionCreate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    id_usuario: int = Field(..., examples=[2])
    tipo_operacion: str = Field("VENTA", examples=["VENTA", "ASIGNACION"])
    notas: Optional[str] = Field(None, max_length=255)


# ==========================================
# 4. ESQUEMAS DE SESIÓN TEMPORAL DE INVITADO
# ==========================================
class SesionInvitadoRequest(BaseModel):
    id_vehiculo: int = Field(1, examples=[1])
    email_invitado: Optional[str] = Field("prospecto@demo.com")
    duracion_minutos: int = Field(5, ge=1, le=15, examples=[5])


class SesionInvitadoOut(BaseModel):
    id_sesion: int
    token_sesion: str
    id_vehiculo: int
    fecha_expiracion: Optional[str] = None
    comandos_permitidos: List[str]
    activa: bool


# ==========================================
# 5. ESQUEMAS DEL EDITOR VISUAL DE DEMOS
# ==========================================
class DemoPasoEditor(BaseModel):
    orden: int = Field(..., ge=1, examples=[1])
    id_comando: int = Field(..., examples=[1])
    duracion_ms: int = Field(..., ge=500, examples=[2500])
    pausa_ms: int = Field(1200, ge=0, examples=[1200])


class DemoEditorCreate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    nombre: str = Field(..., max_length=80, examples=["Secuencia Obra Civil"])
    descripcion: Optional[str] = Field(None, max_length=255)
    id_usuario_creador: Optional[int] = Field(None)
    es_fabrica: bool = Field(False)
    pasos: List[DemoPasoEditor] = Field(..., min_items=1)


# ==========================================
# 6. ESQUEMAS DE AUDITORÍA Y DASHBOARD
# ==========================================
class BitacoraAuditoriaOut(BaseModel):
    id_auditoria: int
    id_usuario: Optional[int] = None
    accion: str
    entidad_afectada: str
    detalle: Optional[str] = None
    direccion_ip: Optional[str] = None
    fecha_hora: Optional[str] = None


class DashboardMetricasOut(BaseModel):
    total_unidades: int
    unidades_vendidas: int
    unidades_stock: int
    total_usuarios: int
    total_modelos: int
    total_comandos_historico: int
