"""Interfaz de acceso a datos.

Filtro, cálculos y simulación solo hablan con esta interfaz. Cambiar de los
datos simulados a PostgreSQL solo exige otro adaptador.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from backend.dominio import (
    Capacidad,
    Cliente,
    Cobertura,
    Proveedor,
    Ruta,
    ServicioHistorico,
    Tarifa,
    TipoVehiculo,
    Ubicacion,
    VehiculoProveedor,
)


class ErrorDatosNoDisponibles(RuntimeError):
    """La fuente de datos (p. ej. la base PostgreSQL) no responde o no se puede leer."""


class Repositorio(ABC):
    def recargar(self) -> None:
        """Descarta lo leído para que la próxima consulta vuelva a la fuente. Por defecto no hace nada."""

    @abstractmethod
    def proveedores(self) -> list[Proveedor]:
        """Todos los proveedores, también los inactivos (el filtro los descarta con su razón)."""

    @abstractmethod
    def clientes(self) -> list[Cliente]: ...

    @abstractmethod
    def ubicaciones(self) -> list[Ubicacion]: ...

    @abstractmethod
    def rutas(self) -> list[Ruta]: ...

    @abstractmethod
    def ruta(self, origen_id: str, destino_id: str) -> Optional[Ruta]:
        """Ruta dirigida origen→destino, o `None` si no existe."""

    @abstractmethod
    def tipos_vehiculo(self) -> list[TipoVehiculo]: ...

    @abstractmethod
    def tarifas_vigentes(self, ruta_id: str, fecha: date) -> list[Tarifa]:
        """Tarifas de todos los proveedores para la ruta, vigentes en la fecha."""

    @abstractmethod
    def flota(self, fecha: date) -> list[VehiculoProveedor]:
        """Por cada (proveedor, tipo de vehículo), el registro más reciente vigente en la fecha."""

    @abstractmethod
    def cobertura(self) -> list[Cobertura]: ...

    @abstractmethod
    def capacidad(self, fecha: date) -> list[Capacidad]:
        """Capacidad de servicio de cada proveedor en la fecha (puede faltar)."""

    @abstractmethod
    def servicios_historicos(self, hasta: Optional[date] = None) -> list[ServicioHistorico]:
        """Servicios completados, opcionalmente solo los entregados antes de `hasta` (backtesting)."""
