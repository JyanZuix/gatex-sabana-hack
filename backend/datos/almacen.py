"""Escritura de solicitudes decididas (README 3.7 y `docs/decisiones.md`, 2026-10-24).

- Al evaluar, el número de la solicitud se reserva de la secuencia de la base
  (`REQ-0496`…), así no se reinicia cuando se reinicia el servidor. Los números
  reservados que nunca llegan a una decisión quedan como huecos de la secuencia.
- Al decidir, la solicitud se inserta en `transporte.solicitud` y queda pendiente:
  la fila de `transporte.servicio` la crea quien registre la entrega real. La API
  nunca escribe en `servicio` (exige datos reales de entrega y calificación).
- `transporte.solicitud` no tiene columnas para el proveedor elegido, la justificación
  ni el snapshot: esos datos viven en el registro en memoria de la API.
"""
from __future__ import annotations

import re
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional

from backend.dominio import CargaEspecial, Solicitud

from .repositorio import ErrorDatosNoDisponibles

# La base escribe el tipo de carga en femenino y con "general"; la API usa `None` para carga general.
TIPO_CARGA_BD = {None: "general", "refrigerado": "refrigerada", "sobredimensionado": "sobredimensionada",
                 "peligrosa": "peligrosa"}


class SolicitudYaDecidida(ValueError):
    """La solicitud ya tiene una decisión registrada."""


@dataclass(frozen=True)
class SolicitudDecidida:
    """Lo que se guarda en `transporte.solicitud` cuando el funcionario decide."""
    numero: int                          # REQ-0496 → 496
    cliente_id: str                      # CLI-016
    cliente_nombre: str
    ruta_id: str                         # RUTA-02
    tipo_vehiculo_id: str                # vehículo de la opción elegida
    tipo_carga: Optional[CargaEspecial]
    peso_total_kg: int                   # n_contenedores × peso de cada contenedor
    fecha_recogida: datetime
    fecha_entrega_limite: datetime


def numero_solicitud(solicitud_id: str) -> int:
    m = re.fullmatch(r"REQ-(\d+)", solicitud_id)
    if m is None:
        raise ValueError(f"Identificador de solicitud no válido: {solicitud_id}")
    return int(m.group(1))


def solicitud_decidida(solicitud: Solicitud, ruta_id: str, cliente_nombre: str,
                       tipo_vehiculo_id: str) -> SolicitudDecidida:
    """La solicitud no trae hora de recogida: se toma las 00:00 de `fecha_servicio`.
    Así el plazo guardado (`fecha_entrega_limite − fecha_recogida`) es exactamente `plazo_h`."""
    recogida = datetime.combine(solicitud.fecha_servicio, time())
    return SolicitudDecidida(
        numero=numero_solicitud(solicitud.solicitud_id), cliente_id=solicitud.cliente_id,
        cliente_nombre=cliente_nombre, ruta_id=ruta_id, tipo_vehiculo_id=tipo_vehiculo_id,
        tipo_carga=solicitud.tipo_carga, peso_total_kg=round(solicitud.n_contenedores * solicitud.peso_kg),
        fecha_recogida=recogida, fecha_entrega_limite=recogida + timedelta(hours=solicitud.plazo_h),
    )


class AlmacenSolicitudes(ABC):
    @abstractmethod
    def reservar_numero(self) -> int:
        """Número nuevo y único para una solicitud."""

    @abstractmethod
    def registrar(self, s: SolicitudDecidida) -> None:
        """Guarda la solicitud decidida. Lanza `SolicitudYaDecidida` si ese número ya está guardado."""


class AlmacenEnMemoria(AlmacenSolicitudes):
    """Para los datos sintéticos y las pruebas: nada sale del proceso."""

    def __init__(self, ultimo: int = 0):
        self._lock = threading.Lock()
        self._ultimo = ultimo
        self.registradas: dict[int, SolicitudDecidida] = {}

    def reservar_numero(self) -> int:
        with self._lock:
            self._ultimo += 1
            return self._ultimo

    def registrar(self, s: SolicitudDecidida) -> None:
        with self._lock:
            if s.numero in self.registradas:
                raise SolicitudYaDecidida(f"La solicitud REQ-{s.numero:04d} ya está registrada")
            self.registradas[s.numero] = s


def _numero(identificador: str, prefijo: str) -> int:
    m = re.fullmatch(rf"{prefijo}-(\d+)", identificador)
    if m is None:
        raise ErrorDatosNoDisponibles(f"No se puede guardar en la base: '{identificador}' no es un ID {prefijo}-…")
    return int(m.group(1))


def parametros_insert(s: SolicitudDecidida) -> dict:
    """Fila de `transporte.solicitud` con los tipos y valores que exige la base."""
    return {
        "solicitud_id": s.numero, "cliente_id": _numero(s.cliente_id, "CLI"), "cliente": s.cliente_nombre,
        "ruta_id": _numero(s.ruta_id, "RUTA"), "tipo_vehiculo": s.tipo_vehiculo_id,
        "tipo_carga": TIPO_CARGA_BD[s.tipo_carga], "peso_kg": s.peso_total_kg,
        "fecha_recogida": s.fecha_recogida, "fecha_entrega_limite": s.fecha_entrega_limite,
    }


class AlmacenPostgres(AlmacenSolicitudes):
    """Escribe en `<esquema>.solicitud`. Crear el objeto no abre la conexión."""

    def __init__(self, dsn: str, esquema: str = "transporte"):
        if not dsn:
            raise ValueError("Falta la cadena de conexión (variable de entorno DATABASE_URL)")
        self.dsn = dsn
        self.esquema = esquema

    def _conectar(self):
        import psycopg
        return psycopg.connect(self.dsn, connect_timeout=15)

    def reservar_numero(self) -> int:
        import psycopg
        from psycopg import sql
        try:
            with self._conectar() as con:
                return con.execute(sql.SQL("SELECT nextval(pg_get_serial_sequence({}, 'solicitud_id'))").format(
                    sql.Literal(f"{self.esquema}.solicitud"))).fetchone()[0]
        except psycopg.Error as e:
            raise ErrorDatosNoDisponibles(
                f"No se pudo reservar el número de la solicitud en la base ({type(e).__name__})") from e

    def insertar(self, con, s: SolicitudDecidida) -> None:
        """INSERT dentro de una conexión abierta (separado para poder probarlo con ROLLBACK)."""
        from psycopg import sql
        p = parametros_insert(s)
        con.execute(sql.SQL("INSERT INTO {}.solicitud ({}) VALUES ({})").format(
            sql.Identifier(self.esquema), sql.SQL(", ").join(map(sql.Identifier, p)),
            sql.SQL(", ").join(map(sql.Placeholder, p))), p)

    def registrar(self, s: SolicitudDecidida) -> None:
        import psycopg
        try:
            with self._conectar() as con:
                self.insertar(con, s)
        except psycopg.errors.UniqueViolation as e:
            raise SolicitudYaDecidida(f"La solicitud REQ-{s.numero:04d} ya está registrada en la base") from e
        except psycopg.Error as e:
            raise ErrorDatosNoDisponibles(
                f"No se pudo guardar la solicitud en la base ({type(e).__name__}); la decisión no se registró") from e
