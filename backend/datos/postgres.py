"""Adaptador PostgreSQL para el esquema `transporte` (Supabase).

Lee las tablas una vez, en la primera consulta, y las convierte a los mismos
modelos de `backend.dominio` que el adaptador simulado.

Tablas que lee: proveedor, flota, capacidad_actual, ruta, tarifa, solicitud, servicio,
tipo_vehiculo (catálogo con `cap_teu` y `cap_kg`) y cliente.

Lo que la base no guarda sale de `mapeo_postgres.yaml` (provisional) o se deduce así:
- IDs: `PROV-01`, `RUTA-02`, `TAR-003`, `SRV-0004`, `CLI-001`. Las ubicaciones usan su nombre
  y los tipos de vehículo su clave (`tractomula`).
- Corredor de una ruta: los dos extremos, puerto primero (Buenaventura–Bogotá vale para ambos sentidos).
- Cobertura: rutas en las que el proveedor tiene tarifa.
- Tarifas y flota vigentes desde la vinculación del proveedor.
- Servicio: plazo = `fecha_entrega_limite − fecha_recogida`; tiempo prometido = el de la tarifa.

Compatibilidad: si la base aún no tiene la tabla `cliente` o la columna `solicitud.cliente_id`,
los clientes se identifican por el texto de `solicitud.cliente`, como en la versión anterior.
El desempeño nunca se lee de la base: se calcula del historial (`servicio`). La columna
`servicio.calificacion` no se usa.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Callable, Mapping, Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.config import Config, cargar_config
from backend.dominio import (
    CARGAS_ESPECIALES,
    Capacidad,
    CargaEspecial,
    Cliente,
    Proveedor,
    Ruta,
    ServicioHistorico,
    Tarifa,
    TipoVehiculo,
    Ubicacion,
    VehiculoProveedor,
)

from .memoria import RepositorioEnMemoria
from .repositorio import ErrorDatosNoDisponibles, Repositorio

TABLAS = ("proveedor", "flota", "capacidad_actual", "ruta", "tarifa", "solicitud", "servicio", "tipo_vehiculo")
TABLAS_OPCIONALES = ("cliente",)   # compatibilidad: sin ella se usa el texto `solicitud.cliente`
RUTA_MAPEO = Path(__file__).with_name("mapeo_postgres.yaml")

Fila = Mapping[str, object]
LectorTablas = Callable[[], Mapping[str, list[Fila]]]


class ErrorMapeo(ValueError):
    """`mapeo_postgres.yaml` falta o es inválido, o la base no tiene lo que el backend necesita."""


class Mapeo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    esquema: str
    puertos: tuple[str, ...]


@lru_cache(maxsize=1)
def cargar_mapeo(ruta: Path = RUTA_MAPEO) -> Mapeo:
    if not ruta.exists():
        raise ErrorMapeo(f"No existe el archivo de mapeo {ruta}")
    with ruta.open(encoding="utf-8") as f:
        try:
            return Mapeo.model_validate(yaml.safe_load(f) or {})
        except ValidationError as e:
            raise ErrorMapeo(f"Mapeo inválido en {ruta.name}: {e}") from None


def id_proveedor(n: int) -> str:
    return f"PROV-{n:02d}"


def id_ruta(n: int) -> str:
    return f"RUTA-{n:02d}"


def id_cliente(n: int) -> str:
    return f"CLI-{n:03d}"


def _horas(desde: datetime, hasta: datetime) -> float:
    return (hasta - desde).total_seconds() / 3600


def _carga_especial(valor: Optional[str], tipo: str) -> Optional[CargaEspecial]:
    if valor is None:
        return None
    if valor not in CARGAS_ESPECIALES:
        raise ErrorMapeo(f"tipo_vehiculo '{tipo}': carga_especial '{valor}' desconocida; "
                         f"use {list(CARGAS_ESPECIALES)} o NULL")
    return valor  # type: ignore[return-value]


class RepositorioPostgres(Repositorio):
    def __init__(self, dsn: str, mapeo: Optional[Mapeo] = None, cfg: Optional[Config] = None,
                 leer_tablas: Optional[LectorTablas] = None):
        """`leer_tablas` reemplaza la lectura de PostgreSQL (para pruebas)."""
        if not dsn:
            raise ValueError("Falta la cadena de conexión (variable de entorno DATABASE_URL)")
        self.dsn = dsn
        self.mapeo = mapeo or cargar_mapeo()
        self.cfg = cfg or cargar_config()
        self._leer_tablas = leer_tablas or self._leer_de_postgres
        self._memoria: Optional[RepositorioEnMemoria] = None

    def _leer_de_postgres(self) -> dict[str, list[Fila]]:
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row

        try:
            return self._consultar(psycopg, sql, dict_row)
        except psycopg.Error as e:
            # El mensaje de psycopg puede incluir el host; nunca la contraseña.
            raise ErrorDatosNoDisponibles(
                f"No se pudo leer la base de datos ({type(e).__name__}). Intente de nuevo en unos segundos.") from e

    def _consultar(self, psycopg, sql, dict_row) -> dict[str, list[Fila]]:
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15) as con:
            existentes = {f["table_name"] for f in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                (self.mapeo.esquema,)).fetchall()}
            return {
                t: con.execute(sql.SQL("SELECT * FROM {}.{}").format(
                    sql.Identifier(self.mapeo.esquema), sql.Identifier(t))).fetchall()
                for t in TABLAS + TABLAS_OPCIONALES if t in existentes
            }

    def recargar(self) -> None:
        """Descarta lo leído; la próxima consulta vuelve a leer la base."""
        self._memoria = None

    def _datos(self) -> RepositorioEnMemoria:
        if self._memoria is None:
            self._memoria = self._convertir(self._leer_tablas())
        return self._memoria

    # ------------------------------------------------------------------
    # Conversión de filas a modelos de dominio
    # ------------------------------------------------------------------
    def _convertir(self, t: Mapping[str, list[Fila]]) -> RepositorioEnMemoria:
        faltan = [n for n in TABLAS if n not in t]
        if faltan:
            raise ErrorMapeo(f"Faltan las tablas {faltan} en el esquema {self.mapeo.esquema}")
        m = self.mapeo

        tipos = [TipoVehiculo(tipo_vehiculo_id=f["tipo_vehiculo"], nombre=f["nombre"], cap_teu=f["cap_teu"],
                              cap_kg=f["cap_kg"], carga_especial=_carga_especial(f["carga_especial"], f["tipo_vehiculo"]))
                 for f in t["tipo_vehiculo"]]
        carga_de_tipo = {x.tipo_vehiculo_id: x.carga_especial for x in tipos}
        en_uso = {f["tipo_vehiculo"] for n in ("flota", "tarifa", "solicitud") for f in t[n]}
        sin_catalogo = sorted(en_uso - set(carga_de_tipo))
        if sin_catalogo:
            raise ErrorMapeo(f"Tipos de vehículo sin fila en {m.esquema}.tipo_vehiculo: {sin_catalogo}")

        vinculacion = {f["proveedor_id"]: f["fecha_vinculacion"] for f in t["proveedor"]}
        con_flota: dict[int, set[str]] = {}
        for f in t["flota"]:
            if f["cantidad"] > 0:
                con_flota.setdefault(f["proveedor_id"], set()).add(f["tipo_vehiculo"])

        proveedores = []
        for f in t["proveedor"]:
            cargas: list[CargaEspecial] = []
            if f["apto_carga_peligrosa"]:
                cargas.append("peligrosa")
            if f["apto_refrigerada"]:
                cargas.append("refrigerado")
            # La base no marca quién lleva sobredimensionada: se deduce de tener ese vehículo.
            if any(carga_de_tipo[v] == "sobredimensionado" for v in con_flota.get(f["proveedor_id"], ())):
                cargas.append("sobredimensionado")
            proveedores.append(Proveedor(
                proveedor_id=id_proveedor(f["proveedor_id"]), nombre=f["nombre"],
                estado="activo" if f["activo"] else "inactivo", cargas_especiales=tuple(cargas)))

        lugares = sorted({f[k] for f in t["ruta"] for k in ("origen", "destino")})
        ubicaciones = [Ubicacion(ubicacion_id=n, nombre=n, tipo="puerto" if n in m.puertos else "ciudad")
                       for n in lugares]

        rutas = []
        for f in t["ruta"]:
            a, b = f["origen"], f["destino"]
            if b in m.puertos and a not in m.puertos:
                a, b = b, a
            rutas.append(Ruta(ruta_id=id_ruta(f["ruta_id"]), origen_id=f["origen"], destino_id=f["destino"],
                              distancia_km=f["distancia_km"], corredor=f"{a}–{b}"))

        tarifas = [Tarifa(
            tarifa_id=f"TAR-{f['tarifa_id']:03d}", proveedor_id=id_proveedor(f["proveedor_id"]),
            ruta_id=id_ruta(f["ruta_id"]), tipo_vehiculo_id=f["tipo_vehiculo"], precio_viaje=f["precio_cop"],
            tiempo_prometido_h=f["transito_estimado_h"], vigente_desde=vinculacion[f["proveedor_id"]],
        ) for f in t["tarifa"]]

        flota = [VehiculoProveedor(
            proveedor_id=id_proveedor(f["proveedor_id"]), tipo_vehiculo_id=f["tipo_vehiculo"],
            unidades_disponibles=f["disponibles_semana"], vigente_desde=vinculacion[f["proveedor_id"]],
        ) for f in t["flota"]]

        capacidad = [Capacidad(proveedor_id=id_proveedor(f["proveedor_id"]), fecha=f["fecha"],
                               servicios_disponibles=f["servicios_disponibles"]) for f in t["capacidad_actual"]]

        clientes, cliente_de = self._clientes(t)

        solicitudes = {f["solicitud_id"]: f for f in t["solicitud"]}
        prometido = {(f["proveedor_id"], f["ruta_id"], f["tipo_vehiculo"]): f["transito_estimado_h"]
                     for f in t["tarifa"]}
        servicios = []
        for f in t["servicio"]:
            so = solicitudes[f["solicitud_id"]]
            servicios.append(ServicioHistorico(
                servicio_id=f"SRV-{f['servicio_id']:04d}", proveedor_id=id_proveedor(f["proveedor_id"]),
                cliente_id=cliente_de(so), ruta_id=id_ruta(so["ruta_id"]), tipo_vehiculo_id=so["tipo_vehiculo"],
                fecha_entrega=f["fecha_entrega_real"].date(),
                tiempo_prometido_h=prometido.get((f["proveedor_id"], so["ruta_id"], so["tipo_vehiculo"])),
                tiempo_real_h=f["transito_real_h"],
                plazo_acordado_h=_horas(so["fecha_recogida"], so["fecha_entrega_limite"]),
                a_tiempo=f["a_tiempo"],
            ))

        return RepositorioEnMemoria(
            proveedores=proveedores, clientes=clientes, ubicaciones=ubicaciones, rutas=rutas,
            tipos_vehiculo=tipos, tarifas=tarifas, flota=flota, capacidad=capacidad, servicios=servicios,
        )

    @staticmethod
    def _clientes(t: Mapping[str, list[Fila]]) -> tuple[list[Cliente], Callable[[Fila], str]]:
        """Catálogo de clientes y cómo obtener el `cliente_id` de una solicitud."""
        con_columna = all("cliente_id" in f for f in t["solicitud"])
        if "cliente" in t and con_columna:
            clientes = [Cliente(cliente_id=id_cliente(f["cliente_id"]), nombre=f["nombre"])
                        for f in sorted(t["cliente"], key=lambda f: f["cliente_id"])]
            existentes = {f["cliente_id"] for f in t["cliente"]}
            sin_cliente = sorted({f["cliente_id"] for f in t["solicitud"]} - existentes)
            if sin_cliente:
                raise ErrorMapeo(f"Solicitudes con cliente_id sin fila en la tabla cliente: {sin_cliente}")
            return clientes, lambda so: id_cliente(so["cliente_id"])
        # Compatibilidad con la base anterior: el cliente es el texto de `solicitud.cliente`.
        clientes = [Cliente(cliente_id=n, nombre=n) for n in sorted({f["cliente"] for f in t["solicitud"]})]
        return clientes, lambda so: so["cliente"]

    # ------------------------------------------------------------------
    # Interfaz Repositorio
    # ------------------------------------------------------------------
    def proveedores(self):
        return self._datos().proveedores()

    def clientes(self):
        return self._datos().clientes()

    def ubicaciones(self):
        return self._datos().ubicaciones()

    def rutas(self):
        return self._datos().rutas()

    def ruta(self, origen_id, destino_id):
        return self._datos().ruta(origen_id, destino_id)

    def tipos_vehiculo(self):
        return self._datos().tipos_vehiculo()

    def tarifas_vigentes(self, ruta_id, fecha):
        return self._datos().tarifas_vigentes(ruta_id, fecha)

    def flota(self, fecha):
        return self._datos().flota(fecha)

    def cobertura(self):
        return self._datos().cobertura()

    def capacidad(self, fecha):
        return self._datos().capacidad(fecha)

    def servicios_historicos(self, hasta=None):
        return self._datos().servicios_historicos(hasta)
