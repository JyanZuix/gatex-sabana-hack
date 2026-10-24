"""Carga tipada de los parámetros de `parametros.yaml`."""
from .carga import (
    Config,
    ErrorConfiguracion,
    cargar_config,
)

__all__ = ["Config", "ErrorConfiguracion", "cargar_config"]
