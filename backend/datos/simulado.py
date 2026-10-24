"""Adaptador en memoria que lee archivos JSON.

Mientras no exista la base de datos, sirve los datos sintéticos de
`backend/datos_sinteticos/`. Cada archivo debe declarar `"sintetico": true`
para que ningún dato inventado pase por real (regla 4 del README).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import BaseModel, ValidationError

from backend.dominio import (
    Capacidad,
    Cliente,
    Cobertura,
    CondicionVia,
    Incidente,
    Proveedor,
    Ruta,
    ServicioHistorico,
    Tarifa,
    TipoVehiculo,
    Ubicacion,
    VehiculoProveedor,
)

from .repositorio import Repositorio

M = TypeVar("M", bound=BaseModel)

CARPETA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "datos_sinteticos"


class ErrorDatos(ValueError):
    """Un archivo de datos falta, no tiene la etiqueta de sintético o tiene registros inválidos."""


class RepositorioSimulado(Repositorio):
    def __init__(self, carpeta: str | Path = CARPETA_POR_DEFECTO):
        self.carpeta = Path(carpeta)
        self._proveedores = self._leer("proveedores", Proveedor)
        self._clientes = self._leer("clientes", Cliente)
        self._ubicaciones = self._leer("ubicaciones", Ubicacion)
        self._rutas = self._leer("rutas", Ruta)
        self._tipos = self._leer("tipos_vehiculo", TipoVehiculo)
        self._tarifas = self._leer("tarifas", Tarifa)
        self._flota = self._leer("vehiculos_proveedor", VehiculoProveedor)
        self._capacidad = self._leer("capacidad_actual", Capacidad)
        self._servicios = self._leer("servicios_historicos", ServicioHistorico)
        self._incidentes = self._leer("incidentes", Incidente)
        self._condiciones = self._leer("condiciones_via", CondicionVia)
        # Si no hay tabla de cobertura, se deduce de las tarifas (docs/decisiones.md).
        if (self.carpeta / "cobertura_proveedor.json").exists():
            self._cobertura = self._leer("cobertura_proveedor", Cobertura)
        else:
            pares = {(t.proveedor_id, t.ruta_id) for t in self._tarifas}
            self._cobertura = [Cobertura(proveedor_id=p, ruta_id=r) for p, r in sorted(pares)]

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

    def proveedores(self) -> list[Proveedor]:
        return list(self._proveedores)

    def clientes(self) -> list[Cliente]:
        return list(self._clientes)

    def ubicaciones(self) -> list[Ubicacion]:
        return list(self._ubicaciones)

    def rutas(self) -> list[Ruta]:
        return list(self._rutas)

    def ruta(self, origen_id: str, destino_id: str) -> Optional[Ruta]:
        return next((r for r in self._rutas if r.origen_id == origen_id and r.destino_id == destino_id), None)

    def tipos_vehiculo(self) -> list[TipoVehiculo]:
        return list(self._tipos)

    def tarifas_vigentes(self, ruta_id: str, fecha: date) -> list[Tarifa]:
        vigentes = [t for t in self._tarifas if t.ruta_id == ruta_id and t.vigente(fecha)]
        # Si dos tarifas se solapan, gana la de vigencia más reciente.
        ultima: dict[tuple[str, str], Tarifa] = {}
        for t in sorted(vigentes, key=lambda t: t.vigente_desde):
            ultima[(t.proveedor_id, t.tipo_vehiculo_id)] = t
        return list(ultima.values())

    def flota(self, fecha: date) -> list[VehiculoProveedor]:
        ultima: dict[tuple[str, str], VehiculoProveedor] = {}
        for v in sorted(self._flota, key=lambda v: v.vigente_desde):
            if v.vigente_desde <= fecha:
                ultima[(v.proveedor_id, v.tipo_vehiculo_id)] = v
        return list(ultima.values())

    def cobertura(self) -> list[Cobertura]:
        return list(self._cobertura)

    def capacidad(self, fecha: date) -> list[Capacidad]:
        return [c for c in self._capacidad if c.fecha == fecha]

    def servicios_historicos(self, hasta: Optional[date] = None) -> list[ServicioHistorico]:
        if hasta is None:
            return list(self._servicios)
        return [s for s in self._servicios if s.fecha_entrega < hasta]

    def incidentes(self) -> list[Incidente]:
        return list(self._incidentes)

    def condicion_via(self, corredor: str, fecha: date) -> Optional[CondicionVia]:
        previas = [c for c in self._condiciones if c.corredor == corredor and c.fecha_hora.date() <= fecha]
        return max(previas, key=lambda c: c.fecha_hora, default=None)
