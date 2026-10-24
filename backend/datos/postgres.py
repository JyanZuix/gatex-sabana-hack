"""Adaptador PostgreSQL (esqueleto).

TODO(esquema): implementar las consultas cuando el subequipo de base de
datos entregue el esquema. Cada método debe devolver los mismos modelos de
`backend.dominio` que el adaptador simulado, para que las pruebas sirvan igual.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from .repositorio import Repositorio


class RepositorioPostgres(Repositorio):
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("Falta la cadena de conexión (variable de entorno DATABASE_URL)")
        self.dsn = dsn

    def _pendiente(self, nombre: str):
        raise NotImplementedError(f"TODO(esquema): {nombre} aún no está implementado para PostgreSQL")

    def proveedores(self):
        self._pendiente("proveedores")

    def clientes(self):
        self._pendiente("clientes")

    def ubicaciones(self):
        self._pendiente("ubicaciones")

    def rutas(self):
        self._pendiente("rutas")

    def ruta(self, origen_id: str, destino_id: str):
        self._pendiente("ruta")

    def tipos_vehiculo(self):
        self._pendiente("tipos_vehiculo")

    def tarifas_vigentes(self, ruta_id: str, fecha: date):
        self._pendiente("tarifas_vigentes")

    def flota(self, fecha: date):
        self._pendiente("flota")

    def cobertura(self):
        self._pendiente("cobertura")

    def capacidad(self, fecha: date):
        self._pendiente("capacidad")

    def servicios_historicos(self, hasta: Optional[date] = None):
        self._pendiente("servicios_historicos")

    def incidentes(self):
        self._pendiente("incidentes")

    def condicion_via(self, corredor: str, fecha: date):
        self._pendiente("condicion_via")
