"""Capa de acceso a datos: interfaz `Repositorio` y sus adaptadores."""
from .fabrica import crear_repositorio
from .repositorio import Repositorio
from .simulado import ErrorDatos, RepositorioSimulado

__all__ = ["Repositorio", "RepositorioSimulado", "ErrorDatos", "crear_repositorio"]
