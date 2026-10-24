"""Modelos de dominio compartidos por filtro, cálculos y simulación.

Reflejan las tablas de `docs/calculos_simulacion.md` (secciones 5.2 y 7).
TODO(esquema): ajustar nombres y tipos cuando esté disponible el esquema
PostgreSQL del subequipo de base de datos.
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Modelo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# Tipos de carga especial. `None` significa carga general.
CARGAS_ESPECIALES = ("refrigerado", "sobredimensionado", "peligrosa")
CargaEspecial = Literal["refrigerado", "sobredimensionado", "peligrosa"]


class Ubicacion(_Modelo):
    ubicacion_id: str
    nombre: str
    tipo: Literal["puerto", "ciudad", "bodega_cliente"]
    lat: Optional[float] = None
    lon: Optional[float] = None


class Ruta(_Modelo):
    """Trayecto dirigido A→B con distancia fija."""
    ruta_id: str
    origen_id: str
    destino_id: str
    distancia_km: float = Field(gt=0)
    corredor: str


class Cliente(_Modelo):
    cliente_id: str
    nombre: str


class TipoVehiculo(_Modelo):
    tipo_vehiculo_id: str
    nombre: str
    cap_teu: int = Field(ge=0)
    cap_toneladas: float = Field(ge=0)
    cap_m3: Optional[float] = Field(default=None, ge=0)
    carga_especial: Optional[CargaEspecial] = None


class Proveedor(_Modelo):
    proveedor_id: str
    nombre: str
    estado: Literal["activo", "suspendido", "inactivo"] = "activo"
    poliza_vigente_hasta: Optional[date] = None
    cargas_especiales: tuple[CargaEspecial, ...] = ()


class Tarifa(_Modelo):
    """Precio fijo por viaje: proveedor + ruta + tipo de vehículo."""
    tarifa_id: str
    proveedor_id: str
    ruta_id: str
    tipo_vehiculo_id: str
    precio_viaje: int = Field(gt=0)
    moneda: Literal["COP"] = "COP"
    # TODO(esquema): la especificación lo deja como opcional; la v1 lo exige
    # porque es el insumo del filtro de plazo y de la simulación.
    tiempo_prometido_h: float = Field(gt=0)
    vigente_desde: date
    vigente_hasta: Optional[date] = None

    def vigente(self, fecha: date) -> bool:
        return self.vigente_desde <= fecha and (self.vigente_hasta is None or fecha <= self.vigente_hasta)


class VehiculoProveedor(_Modelo):
    proveedor_id: str
    tipo_vehiculo_id: str
    unidades_disponibles: int = Field(ge=0)
    vigente_desde: date


class Cobertura(_Modelo):
    proveedor_id: str
    ruta_id: str


class Capacidad(_Modelo):
    """Capacidad de servicio del proveedor en una fecha."""
    proveedor_id: str
    fecha: date
    servicios_disponibles: int = Field(ge=0)


class ServicioHistorico(_Modelo):
    servicio_id: str
    proveedor_id: str
    cliente_id: str
    ruta_id: str
    tipo_vehiculo_id: str
    fecha_entrega: date
    tiempo_prometido_h: Optional[float] = Field(default=None, gt=0)
    tiempo_real_h: float = Field(gt=0)
    plazo_acordado_h: Optional[float] = Field(default=None, gt=0)
    a_tiempo: Optional[bool] = None


class Incidente(_Modelo):
    servicio_id: str
    tipo: str
    severidad: float = Field(ge=0, le=1)


class Solicitud(_Modelo):
    """Pedido de transporte A→B.

    `solicitud_id` lo asigna el backend (consecutivo); el cliente no lo envía.
    TODO(esquema): campos definitivos cuando se conecten frontend, gafas y BD.
    """
    solicitud_id: Optional[str] = None
    cliente_id: str
    origen_id: str
    destino_id: str
    fecha_servicio: date
    plazo_h: float = Field(gt=0)
    n_teu: int = Field(default=0, ge=0)
    toneladas: float = Field(default=0, ge=0)
    tipo_carga: Optional[CargaEspecial] = None
    tipo_vehiculo_id: Optional[str] = None
    presupuesto_cop: int = Field(ge=0)
    # None → se usa `escenario.penal_hora_cop` de la configuración.
    penal_hora_cop: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _con_carga(self) -> "Solicitud":
        if self.n_teu == 0 and self.toneladas == 0:
            raise ValueError("La solicitud debe indicar contenedores (n_teu) o toneladas")
        return self
