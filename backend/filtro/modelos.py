"""Estructuras de entrada y salida del filtro."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from backend.calculos.costos import OpcionVehiculo
from backend.config import Config
from backend.dominio import Capacidad, Proveedor, Ruta, Solicitud, TipoVehiculo

Valor = Union[int, float, str, None]


@dataclass(frozen=True)
class Razon:
    """Motivo de descarte: código, mensaje legible y el dato que lo causó."""
    codigo: str
    mensaje: str
    requerido: Valor
    disponible: Valor


@dataclass(frozen=True)
class ContextoProveedor:
    """Todo lo que una regla necesita para evaluar a un proveedor."""
    solicitud: Solicitud
    proveedor: Proveedor
    ruta: Ruta
    nombres_origen_destino: tuple[str, str]
    tipos_validos: tuple[TipoVehiculo, ...]
    unidades: dict[str, int]                 # tipo_vehiculo_id → unidades disponibles
    opciones: tuple[OpcionVehiculo, ...]     # tipos válidos con tarifa vigente
    tiene_cobertura: bool
    capacidad: Optional[Capacidad]
    cfg: Config

    @property
    def operables(self) -> tuple[OpcionVehiculo, ...]:
        """Opciones con tarifa y al menos una unidad disponible."""
        return tuple(o for o in self.opciones if o.unidades_disponibles > 0)

    @property
    def suficientes(self) -> tuple[OpcionVehiculo, ...]:
        """Opciones con unidades suficientes para la carga completa."""
        return tuple(o for o in self.opciones if o.suficiente)


@dataclass(frozen=True)
class Candidato:
    proveedor: Proveedor
    opcion: OpcionVehiculo                # vehículo más económico que cumple
    avisos: tuple[str, ...] = ()          # datos faltantes que no descartan pero deben verse
    capacidad: Optional[Capacidad] = None # servicios que acepta en la fecha (None = sin dato)


@dataclass(frozen=True)
class Cancelado:
    proveedor: Proveedor
    razones: tuple[Razon, ...]


@dataclass(frozen=True)
class CasiElegible:
    """Cancelado por el menor número de reglas, con lo que habría que flexibilizar. Decide el funcionario.

    `razon` y `flexibilizar` son la primera condición; `condiciones` las trae todas (incluida la primera).
    """
    proveedor: Proveedor
    razon: Razon
    flexibilizar: str
    # Vehículo más económico que tendría si se flexibiliza (None si no tiene tarifa para ninguno válido).
    opcion: Optional[OpcionVehiculo] = None
    condiciones: tuple[tuple[Razon, str], ...] = ()


@dataclass(frozen=True)
class ResultadoFiltro:
    ruta: Ruta
    candidatos: tuple[Candidato, ...]
    cancelados: tuple[Cancelado, ...]
    casi_elegibles: tuple[CasiElegible, ...] = field(default=())

    @property
    def sin_candidatos(self) -> bool:
        return not self.candidatos
