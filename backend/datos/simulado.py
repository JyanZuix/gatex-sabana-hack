"""Adaptador en memoria que lee archivos JSON.

Mientras no exista la base de datos, sirve los datos sintéticos de
`backend/datos_sinteticos/`. Cada archivo debe declarar `"sintetico": true`
para que ningún dato inventado pase por real (regla 4 del README).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

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

from .memoria import RepositorioEnMemoria

M = TypeVar("M", bound=BaseModel)

CARPETA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "datos_sinteticos"


class ErrorDatos(ValueError):
    """Un archivo de datos falta, no tiene la etiqueta de sintético o tiene registros inválidos."""


class RepositorioSimulado(RepositorioEnMemoria):
    def __init__(self, carpeta: str | Path = CARPETA_POR_DEFECTO):
        self.carpeta = Path(carpeta)
        cobertura = None
        if (self.carpeta / "cobertura_proveedor.json").exists():
            cobertura = self._leer("cobertura_proveedor", Cobertura)
        super().__init__(
            proveedores=self._leer("proveedores", Proveedor),
            clientes=self._leer("clientes", Cliente),
            ubicaciones=self._leer("ubicaciones", Ubicacion),
            rutas=self._leer("rutas", Ruta),
            tipos_vehiculo=self._leer("tipos_vehiculo", TipoVehiculo),
            tarifas=self._leer("tarifas", Tarifa),
            flota=self._leer("vehiculos_proveedor", VehiculoProveedor),
            capacidad=self._leer("capacidad_actual", Capacidad),
            servicios=self._leer("servicios_historicos", ServicioHistorico),
            cobertura=cobertura,
        )

    def _leer(self, nombre: str, modelo: type[M]) -> list[M]:
        ruta = self.carpeta / f"{nombre}.json"
        if not ruta.exists():
            raise ErrorDatos(f"Falta el archivo de datos {ruta}")
        with ruta.open(encoding="utf-8") as f:
            contenido = json.load(f)
        if not isinstance(contenido, dict) or contenido.get("sintetico") is not True:
            raise ErrorDatos(f"{ruta.name} no está etiquetado como sintético (\"sintetico\": true)")
        try:
            return [modelo.model_validate(r) for r in contenido.get("datos", [])]
        except ValidationError as e:
            raise ErrorDatos(f"Registro inválido en {ruta.name}: {e}") from None
