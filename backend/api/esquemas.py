"""Contrato JSON de la API (README, sección 5). Lo consumen la web y las gafas.

Si cambia una clave hay que actualizar el README y avisar a frontend y realidad aumentada.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.dominio import CargaEspecial

Valor = Union[int, float, str, None]


class _Esquema(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Entradas ---------------------------------------------------------------

class SolicitudEntrada(_Esquema):
    """Lo que envía el frontend. `solicitud_id` lo asigna el backend."""
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
    penal_hora_cop: Optional[float] = Field(default=None, ge=0)


class EscenarioEntrada(_Esquema):
    """Supuestos que cambia el funcionario. Nunca cambian el historial."""
    plazo_h: Optional[float] = Field(default=None, gt=0)
    penal_hora_cop: Optional[float] = Field(default=None, ge=0)


class DecisionEntrada(_Esquema):
    solicitud_id: str
    proveedor_id: str
    justificacion: str = Field(min_length=1)
    escenario_id: Optional[str] = None   # si eligió mirando un escenario, el snapshot es ese

    @field_validator("justificacion")
    @classmethod
    def _no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La justificación no puede estar vacía")
        return v.strip()


# --- Evaluación -------------------------------------------------------------

class RutaSalida(_Esquema):
    ruta_id: str
    origen: str
    destino: str
    distancia_km: float


class Vehiculos(_Esquema):
    tipo: str
    cantidad: int


class Profit(_Esquema):
    esperado_cop: int
    p10_cop: int
    margen_pct: Optional[float]


class TiempoH(_Esquema):
    p50: float
    p90: float
    prob_a_tiempo: float
    abanico: dict[str, float]            # percentil → horas, para el gráfico


class DesgloseDesempeno(_Esquema):
    puntualidad: float
    magnitud_retraso: float


class DesempenoSalida(_Esquema):
    valor: float
    desglose: DesgloseDesempeno


class DesgloseConfianza(_Esquema):
    consistencia: float
    incidentes: float
    cumplimiento_cliente: float
    evidencia: float


class ConfianzaSalida(_Esquema):
    valor: float
    nivel: Literal["Alta", "Media", "Baja"]
    desglose: DesgloseConfianza


class CandidatoSalida(_Esquema):
    proveedor_id: str
    nombre: str
    vehiculos: Vehiculos
    costo_cop: int
    profit: Profit
    tiempo_h: TiempoH
    prob_incidente: float
    desempeno: DesempenoSalida
    confianza: ConfianzaSalida
    riesgos: list[str]
    explicacion: str
    avisos: list[str] = []


class RazonSalida(_Esquema):
    codigo: str
    mensaje: str
    requerido: Valor
    disponible: Valor


class CanceladoSalida(_Esquema):
    proveedor_id: str
    nombre: str
    razones: list[RazonSalida]


class CasiElegibleSalida(_Esquema):
    proveedor_id: str
    nombre: str
    razon: RazonSalida
    flexibilizar: str


class ParametrosEscenario(_Esquema):
    plazo_h: float
    penal_hora_cop: float
    semilla: int
    n_simulaciones: int


class Evaluacion(_Esquema):
    solicitud_id: str
    escenario_id: Optional[str] = None
    ruta: RutaSalida
    candidatos: list[CandidatoSalida]
    cancelados: list[CanceladoSalida]
    casi_elegibles: list[CasiElegibleSalida] = []
    sin_candidatos: bool
    parametros_escenario: ParametrosEscenario


# --- Decisiones -------------------------------------------------------------

class Decision(_Esquema):
    decision_id: str
    solicitud_id: str
    escenario_id: Optional[str]
    proveedor_id: str
    nombre: str
    flexibilizado: bool                  # eligió un "casi elegible"
    justificacion: str
    fecha_hora: datetime
    snapshot: Evaluacion                 # exactamente lo que vio el funcionario


# --- Ficha de proveedor -------------------------------------------------------

class PuntoTendencia(_Esquema):
    mes: str                             # AAAA-MM
    servicios: int
    desempeno: float


class FichaProveedor(_Esquema):
    proveedor_id: str
    nombre: str
    estado: str
    cargas_especiales: list[str]
    servicios: int
    ultimo_servicio: Optional[date]
    puntualidad_pct: Optional[float]
    incidentes_pct: Optional[float]
    desempeno: DesempenoSalida
    confianza: ConfianzaSalida
    tendencia: list[PuntoTendencia]
    fortalezas: list[str]
    debilidades: list[str]

# --- Catálogos de solo lectura para frontend / Quest ---------------------------
class OpcionCatalogo(_Esquema):
    id: Optional[str]
    nombre: str

class RutaCatalogo(_Esquema):
    ruta_id: str
    origen_id: str
    destino_id: str

class ProveedorCatalogo(_Esquema):
    proveedor_id: str
    nombre: str
    estado: str

class CatalogosSalida(_Esquema):
    repositorio: str
    origenes: list[OpcionCatalogo]
    destinos: list[OpcionCatalogo]
    rutas: list[RutaCatalogo]
    clientes: list[OpcionCatalogo]
    tipos_carga: list[OpcionCatalogo]
    tipos_vehiculo: list[OpcionCatalogo]
    proveedores: list[ProveedorCatalogo]
    fecha_servicio: Optional[date]
    nota: str
