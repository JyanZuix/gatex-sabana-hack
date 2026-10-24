"""Catálogos de solo lectura obtenidos del repositorio existente; no calcula elegibilidad."""
from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING
from backend.dominio import CARGAS_ESPECIALES
if TYPE_CHECKING:
    from backend.datos.repositorio import Repositorio


def construir_catalogos(repo: Repositorio, origen_id: str | None = None, fecha_servicio: date | None = None) -> dict:
    proveedores = repo.proveedores()
    ids_proveedor = {p.proveedor_id for p in proveedores}
    rutas_cubiertas = {c.ruta_id for c in repo.cobertura() if c.proveedor_id in ids_proveedor}
    rutas = [r for r in repo.rutas() if r.ruta_id in rutas_cubiertas]
    nombres = {u.ubicacion_id: u.nombre for u in repo.ubicaciones()}
    origenes = sorted({r.origen_id for r in rutas}, key=lambda i: nombres.get(i, i))
    destinos = sorted({r.destino_id for r in rutas if origen_id is None or r.origen_id == origen_id}, key=lambda i: nombres.get(i, i))
    cargas = {"refrigerado": "Refrigerada", "sobredimensionado": "Sobredimensionada", "peligrosa": "Peligrosa"}
    return {
        "repositorio": type(repo).__name__.removeprefix("Repositorio").lower(),
        "origenes": [{"id": i, "nombre": nombres.get(i, i)} for i in origenes],
        "destinos": [{"id": i, "nombre": nombres.get(i, i)} for i in destinos],
        "rutas": [{"ruta_id": r.ruta_id, "origen_id": r.origen_id, "destino_id": r.destino_id} for r in rutas],
        "clientes": [{"id": c.cliente_id, "nombre": c.nombre} for c in repo.clientes()],
        "tipos_carga": [{"id": None, "nombre": "General"}] + [{"id": c, "nombre": cargas[c]} for c in CARGAS_ESPECIALES],
        # Solo contenedores: turbo y sencillo (cap_teu = 0) quedan obsoletos (docs/decisiones.md, 2026-10-24).
        "tipos_vehiculo": [{"id": t.tipo_vehiculo_id, "nombre": t.nombre} for t in repo.tipos_vehiculo()
                           if getattr(t, "cap_teu", None) != 0],
        "proveedores": [{"proveedor_id": p.proveedor_id, "nombre": p.nombre, "estado": p.estado} for p in proveedores],
        "fecha_servicio": fecha_servicio.isoformat() if fecha_servicio else None,
        "nota": "Opciones del catálogo y cobertura registrada. La capacidad por fecha, flota, póliza y elegibilidad final se verifican en /solicitudes/evaluar.",
    }
