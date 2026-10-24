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
from datetime import date, datetime, time, timedelta
from typing import Optional

from backend.dominio import CargaEspecial, Solicitud

from .repositorio import ErrorDatosNoDisponibles

# La base escribe el tipo de carga en femenino y con "general"; la API usa `None` para carga general.
TIPO_CARGA_BD = {None: "general", "refrigerado": "refrigerada", "sobredimensionado": "sobredimensionada",
                 "peligrosa": "peligrosa"}


class SolicitudYaDecidida(ValueError):
    """La solicitud ya tiene una decisión registrada."""


class SolicitudNoEncontrada(LookupError):
    """La solicitud no existe en la base (se guarda al decidir)."""


class ViajeYaCerrado(ValueError):
    """La solicitud ya tiene registrado su servicio."""


class CierreInvalido(ValueError):
    """Los datos del cierre no son coherentes con la solicitud (p. ej. entrega antes de la recogida)."""


@dataclass(frozen=True)
class CierreViaje:
    """Resultado real de un viaje, tal como lo registra quien lo cierra."""
    numero_solicitud: int
    proveedor_numero: int                    # PROV-07 → 7
    fecha_entrega_real: datetime
    precio_cop: int
    incidente: str
    calificacion: int


@dataclass(frozen=True)
class ServicioRegistrado:
    servicio_id: int
    numero_solicitud: int
    proveedor_numero: int
    precio_cop: int
    fecha_servicio: date
    fecha_entrega_real: datetime
    transito_real_h: int
    a_tiempo: bool
    incidente: str
    calificacion: int
    plazo_h: float                           # fecha_entrega_limite − fecha_recogida


def resultado_del_viaje(recogida: datetime, limite: datetime, c: CierreViaje) -> dict:
    """Calcula lo que la base exige de `servicio` a partir de las fechas de la solicitud.

    - `transito_real_h`: horas enteras desde la recogida hasta la entrega real (mínimo 1).
    - `a_tiempo`: la entrega real no supera `fecha_entrega_limite` (comentario de `servicio.a_tiempo`).
    - `fecha_servicio`: el día de la recogida, como en los servicios existentes.
    """
    if c.fecha_entrega_real <= recogida:
        raise CierreInvalido(f"La entrega real ({c.fecha_entrega_real:%Y-%m-%d %H:%M}) debe ser posterior a la "
                             f"recogida de la solicitud ({recogida:%Y-%m-%d %H:%M})")
    horas = (c.fecha_entrega_real - recogida).total_seconds() / 3600
    return {"transito_real_h": max(1, int(horas + 0.5)), "a_tiempo": c.fecha_entrega_real <= limite,
            "fecha_servicio": recogida.date(), "plazo_h": (limite - recogida).total_seconds() / 3600}


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

    @abstractmethod
    def cerrar_viaje(self, c: CierreViaje) -> ServicioRegistrado:
        """Registra el resultado real del viaje en `servicio`. Lanza `SolicitudNoEncontrada`, `ViajeYaCerrado`
        o `CierreInvalido`. Es lo que alimenta el historial con el que se calculan D y C."""


class AlmacenEnMemoria(AlmacenSolicitudes):
    """Para los datos sintéticos y las pruebas: nada sale del proceso."""

    def __init__(self, ultimo: int = 0):
        self._lock = threading.Lock()
        self._ultimo = ultimo
        self.registradas: dict[int, SolicitudDecidida] = {}
        self.servicios: dict[int, ServicioRegistrado] = {}

    def reservar_numero(self) -> int:
        with self._lock:
            self._ultimo += 1
            return self._ultimo

    def registrar(self, s: SolicitudDecidida) -> None:
        with self._lock:
            if s.numero in self.registradas:
                raise SolicitudYaDecidida(f"La solicitud REQ-{s.numero:04d} ya está registrada")
            self.registradas[s.numero] = s

    def cerrar_viaje(self, c: CierreViaje) -> ServicioRegistrado:
        with self._lock:
            s = self.registradas.get(c.numero_solicitud)
            if s is None:
                raise SolicitudNoEncontrada(f"No existe la solicitud REQ-{c.numero_solicitud:04d}")
            if c.numero_solicitud in self.servicios:
                raise ViajeYaCerrado(f"La solicitud REQ-{c.numero_solicitud:04d} ya tiene su servicio registrado")
            r = resultado_del_viaje(s.fecha_recogida, s.fecha_entrega_limite, c)
            registrado = ServicioRegistrado(
                servicio_id=len(self.servicios) + 1, numero_solicitud=c.numero_solicitud,
                proveedor_numero=c.proveedor_numero, precio_cop=c.precio_cop, fecha_entrega_real=c.fecha_entrega_real,
                incidente=c.incidente, calificacion=c.calificacion, **r)
            self.servicios[c.numero_solicitud] = registrado
            return registrado


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

    def cerrar(self, con, c: CierreViaje) -> ServicioRegistrado:
        """Lee la solicitud, valida y inserta en `servicio` dentro de la transacción de `con`."""
        from psycopg import sql
        t = lambda nombre: sql.Identifier(self.esquema, nombre)
        fila = con.execute(sql.SQL("SELECT fecha_recogida, fecha_entrega_limite FROM {} WHERE solicitud_id = %s "
                                   "FOR UPDATE").format(t("solicitud")), (c.numero_solicitud,)).fetchone()
        if fila is None:
            raise SolicitudNoEncontrada(f"No existe la solicitud REQ-{c.numero_solicitud:04d} en la base")
        if con.execute(sql.SQL("SELECT 1 FROM {} WHERE solicitud_id = %s").format(t("servicio")),
                       (c.numero_solicitud,)).fetchone():
            raise ViajeYaCerrado(f"La solicitud REQ-{c.numero_solicitud:04d} ya tiene su servicio registrado")
        r = resultado_del_viaje(fila[0], fila[1], c)
        servicio_id = con.execute(sql.SQL(
            "INSERT INTO {} (solicitud_id, proveedor_id, precio_cop, fecha_servicio, fecha_entrega_real, "
            "transito_real_h, a_tiempo, incidente, calificacion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING servicio_id").format(t("servicio")),
            (c.numero_solicitud, c.proveedor_numero, c.precio_cop, r["fecha_servicio"], c.fecha_entrega_real,
             r["transito_real_h"], r["a_tiempo"], c.incidente, c.calificacion)).fetchone()[0]
        return ServicioRegistrado(
            servicio_id=servicio_id, numero_solicitud=c.numero_solicitud, proveedor_numero=c.proveedor_numero,
            precio_cop=c.precio_cop, fecha_entrega_real=c.fecha_entrega_real, incidente=c.incidente,
            calificacion=c.calificacion, **r)

    def cerrar_viaje(self, c: CierreViaje) -> ServicioRegistrado:
        import psycopg
        try:
            with self._conectar() as con:
                return self.cerrar(con, c)
        except psycopg.errors.UniqueViolation as e:
            raise ViajeYaCerrado(f"La solicitud REQ-{c.numero_solicitud:04d} ya tiene su servicio registrado") from e
        except psycopg.errors.ForeignKeyViolation as e:
            raise CierreInvalido(f"El proveedor PROV-{c.proveedor_numero:02d} no existe en la base") from e
        except psycopg.Error as e:
            raise ErrorDatosNoDisponibles(
                f"No se pudo registrar el viaje en la base ({type(e).__name__}); el servicio no se guardó") from e

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
