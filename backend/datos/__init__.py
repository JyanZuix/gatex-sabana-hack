"""Capa de acceso a datos: interfaz `Repositorio` y sus adaptadores."""
from .almacen import AlmacenEnMemoria, AlmacenPostgres, AlmacenSolicitudes, SolicitudYaDecidida
from .fabrica import crear_almacen, crear_repositorio
from .repositorio import ErrorDatosNoDisponibles, Repositorio
from .simulado import ErrorDatos, RepositorioSimulado

__all__ = ["Repositorio", "ErrorDatosNoDisponibles", "crear_almacen", "AlmacenSolicitudes", "AlmacenEnMemoria",
           "AlmacenPostgres", "SolicitudYaDecidida", "RepositorioSimulado", "ErrorDatos", "crear_repositorio"]
