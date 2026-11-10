"""
Esquemas Pydantic (POO) para las 21 APIs y las reglas de negocio (Movimientos y DEMO).
"""
from typing import Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. ESQUEMAS DE VEHÍCULOS
# ==========================================
class VehiculoCreate(BaseModel):
    nombre: str = Field(..., max_length=80, examples=["Excavadora IoT"])
    modelo: Optional[str] = Field(None, max_length=80, examples=["Modelo X"])
    descripcion: Optional[str] = Field(
        None, max_length=255, examples=["Vehículo de construcción controlado por ESP8266"]
    )
    microcontrolador: Optional[str] = Field(None, max_length=50, examples=["ESP8266"])


class VehiculoUpdate(BaseModel):
    nombre: str = Field(..., max_length=80, examples=["Excavadora IoT Pro"])
    modelo: Optional[str] = Field(None, max_length=80, examples=["Modelo X2"])
    descripcion: Optional[str] = Field(None, max_length=255)
    microcontrolador: Optional[str] = Field(None, max_length=50, examples=["ESP8266"])
    activo: bool = Field(True)


# ==========================================
# 2. ESQUEMAS DE COMANDOS
# ==========================================
class ComandoCreate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    nombre: str = Field(..., max_length=60, examples=["AVANZAR"])
    codigo: int = Field(..., examples=[1])
    descripcion: Optional[str] = Field(
        None, max_length=255, examples=["Mover el vehículo hacia adelante"]
    )


class ComandoUpdate(BaseModel):
    nombre: str = Field(..., max_length=60, examples=["AVANZAR"])
    codigo: int = Field(..., examples=[1])
    descripcion: Optional[str] = Field(None, max_length=255)
    activo: bool = Field(True)


# ==========================================
# 3. ESQUEMAS DE ESTADO E HISTORIAL
# ==========================================
class EstadoUpdate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    id_comando: Optional[int] = Field(None, examples=[9])
    conectado: bool = Field(True)


class HistorialCreate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    id_comando: int = Field(..., examples=[1])
    origen: str = Field("MANUAL", max_length=30, examples=["API-REST"])


# ==========================================
# 4. ESQUEMAS DE DEMOS Y MOVIMIENTOS DEMO
# ==========================================
class DemoCreate(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    nombre: str = Field(..., max_length=80, examples=["Demo principal"])
    descripcion: Optional[str] = Field(
        None, max_length=255, examples=["Secuencia automática de movimientos del vehículo"]
    )


class DemoUpdate(BaseModel):
    nombre: str = Field(..., max_length=80, examples=["Demo principal"])
    descripcion: Optional[str] = Field(None, max_length=255)
    activo: bool = Field(True)


class MovimientoDemoCreate(BaseModel):
    id_demo: int = Field(..., examples=[1])
    id_comando: int = Field(..., examples=[1])
    orden: int = Field(..., examples=[1])
    duracion_ms: int = Field(..., ge=0, examples=[2000])
    pausa_ms: int = Field(0, ge=0, examples=[400])


class MovimientoDemoUpdate(BaseModel):
    id_comando: int = Field(..., examples=[1])
    orden: int = Field(..., examples=[1])
    duracion_ms: int = Field(..., ge=0, examples=[2000])
    pausa_ms: int = Field(0, ge=0, examples=[400])


# ==========================================
# 5. ESQUEMAS DE REGLAS DE NEGOCIO (CONTROL IoT)
# ==========================================
class EjecutarMovimientoRequest(BaseModel):
    id_vehiculo: int = Field(..., examples=[1])
    id_comando: int = Field(..., examples=[1])
    origen: str = Field("WEB-CONTROL", max_length=30, examples=["WEB-CONTROL"])
