"""Repositorio sobre listas en memoria.

Lo comparten el adaptador simulado (lee JSON) y el de PostgreSQL (lee tablas):
cada uno arma las listas de modelos de dominio y aquí se resuelven las consultas.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from backend.dominio import (
    Capacidad,
    Cliente,
    Cobertura,
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


class RepositorioEnMemoria(Repositorio):
    def __init__(
        self,
        *,
        proveedores: list[Proveedor],
        clientes: list[Cliente],
        ubicaciones: list[Ubicacion],
        rutas: list[Ruta],
        tipos_vehiculo: list[TipoVehiculo],
        tarifas: list[Tarifa],
        flota: list[VehiculoProveedor],
        capacidad: list[Capacidad],
        servicios: list[ServicioHistorico],
        incidentes: list[Incidente],
        cobertura: Optional[list[Cobertura]] = None,
    ):
        self._proveedores = proveedores
        self._clientes = clientes
        self._ubicaciones = ubicaciones
        self._rutas = rutas
        self._tipos = tipos_vehiculo
        self._tarifas = tarifas
        self._flota = flota
        self._capacidad = capacidad
        self._servicios = servicios
        self._incidentes = incidentes
        # Si no hay tabla de cobertura, se deduce de las tarifas (docs/decisiones.md).
        if cobertura is None:
            pares = {(t.proveedor_id, t.ruta_id) for t in tarifas}
            cobertura = [Cobertura(proveedor_id=p, ruta_id=r) for p, r in sorted(pares)]
        self._cobertura = cobertura

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
