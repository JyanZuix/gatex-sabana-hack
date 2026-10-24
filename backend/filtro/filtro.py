"""Orquestador del filtro: evalúa TODAS las reglas sobre cada proveedor."""
from __future__ import annotations

from typing import Iterable, Optional

from backend.calculos.costos import opcion_mas_economica, opciones_vehiculo, tipos_validos
from backend.config import Config
from backend.datos import Repositorio
from backend.dominio import Solicitud

from .modelos import Cancelado, Candidato, CasiElegible, ContextoProveedor, ResultadoFiltro
from .reglas import REGLAS, Regla, que_flexibilizar


class RutaNoEncontrada(LookupError):
    """No existe la ruta dirigida origen→destino de la solicitud."""


def construir_contextos(solicitud: Solicitud, repo: Repositorio, cfg: Config) -> list[ContextoProveedor]:
    ruta = repo.ruta(solicitud.origen_id, solicitud.destino_id)
    if ruta is None:
        raise RutaNoEncontrada(f"No existe la ruta {solicitud.origen_id} → {solicitud.destino_id}")
    nombres = {u.ubicacion_id: u.nombre for u in repo.ubicaciones()}
    validos = tuple(tipos_validos(solicitud, repo.tipos_vehiculo()))
    tarifas = repo.tarifas_vigentes(ruta.ruta_id, solicitud.fecha_servicio)
    flota = repo.flota(solicitud.fecha_servicio)
    cobertura = {(c.proveedor_id, c.ruta_id) for c in repo.cobertura()}
    capacidad = {c.proveedor_id: c for c in repo.capacidad(solicitud.fecha_servicio)}

    contextos = []
    for p in repo.proveedores():
        unidades = {v.tipo_vehiculo_id: v.unidades_disponibles for v in flota if v.proveedor_id == p.proveedor_id}
        opciones = opciones_vehiculo(solicitud, validos, [t for t in tarifas if t.proveedor_id == p.proveedor_id], unidades)
        contextos.append(ContextoProveedor(
            solicitud=solicitud, proveedor=p, ruta=ruta,
            nombres_origen_destino=(nombres.get(ruta.origen_id, ruta.origen_id), nombres.get(ruta.destino_id, ruta.destino_id)),
            tipos_validos=validos, unidades=unidades, opciones=tuple(opciones),
            tiene_cobertura=(p.proveedor_id, ruta.ruta_id) in cobertura,
            capacidad=capacidad.get(p.proveedor_id), cfg=cfg,
        ))
    return contextos


def evaluar_contextos(contextos: Iterable[ContextoProveedor], reglas: Optional[list[Regla]] = None) -> ResultadoFiltro:
    reglas = REGLAS if reglas is None else reglas
    contextos = sorted(contextos, key=lambda c: c.proveedor.proveedor_id)
    if not contextos:
        raise ValueError("No hay proveedores para evaluar")
    candidatos, cancelados = [], []
    contexto_de = {ctx.proveedor.proveedor_id: ctx for ctx in contextos}
    for ctx in contextos:
        razones = [r for regla in reglas for r in regla(ctx)]
        if razones:
            cancelados.append(Cancelado(ctx.proveedor, tuple(razones)))
            continue
        validas = [o for o in ctx.suficientes if o.tiempo_prometido_h <= ctx.solicitud.plazo_h]
        opcion = opcion_mas_economica(validas)
        if opcion is None:  # solo pasa si se quitaron reglas base de la lista
            raise RuntimeError(f"{ctx.proveedor.proveedor_id} pasó el filtro sin una opción de vehículo viable")
        avisos = () if ctx.capacidad is not None else ("Sin dato de capacidad de servicio para la fecha",)
        candidatos.append(Candidato(ctx.proveedor, opcion, avisos))

    casi = ()
    if not candidatos:
        casi = tuple(CasiElegible(c.proveedor, c.razones[0], que_flexibilizar(c.razones[0]),
                                  _opcion_si_flexibiliza(contexto_de[c.proveedor.proveedor_id]))
                     for c in cancelados if len(c.razones) == 1)
    return ResultadoFiltro(ruta=contextos[0].ruta, candidatos=tuple(candidatos),
                           cancelados=tuple(cancelados), casi_elegibles=casi)


def _opcion_si_flexibiliza(ctx: ContextoProveedor):
    """La opción más viable que tiene: con unidades suficientes, luego con alguna unidad, luego solo con tarifa."""
    return opcion_mas_economica(ctx.suficientes or ctx.operables or ctx.opciones)


def filtrar(solicitud: Solicitud, repo: Repositorio, cfg: Config, reglas: Optional[list[Regla]] = None) -> ResultadoFiltro:
    """Evalúa todas las reglas sobre todos los proveedores y separa candidatos de cancelados."""
    return evaluar_contextos(construir_contextos(solicitud, repo, cfg), reglas)
