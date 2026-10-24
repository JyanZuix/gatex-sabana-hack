"""Orquestación: filtro → Desempeño y Confianza → simulación → explicación.

La API solo traduce HTTP; toda la lógica sale de `filtro/`, `calculos/` y `simulacion/`.
Ordena los candidatos por el puntaje ponderado y marca el Top N sugerido; no elige:
el funcionario decide y justifica (docs/decisiones.md, 2026-10-24).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from backend.calculos.confianza import Confianza, calcular_confianza
from backend.calculos.costos import OpcionVehiculo
from backend.calculos.desempeno import Desempeno, calcular_desempeno
from backend.calculos.historial import Historial, Sumas, construir_historial
from backend.calculos.priors import Prior, calcular_prior
from backend.calculos.profit import calcular_profit, margen_pct
from backend.calculos.puntaje import EntradaPuntaje, ordenar
from backend.config import Config
from backend.datos import Repositorio
from backend.dominio import Solicitud
from backend.filtro import filtrar
from backend.filtro.modelos import Razon
from backend.simulacion import ReferenciaMercado, ResumenOpcion, explicar, preparar_entrada, riesgos, simular

from . import esquemas as e
from . import textos as t

SUMAS_VACIAS = Sumas(W=0, W_a=0, W_r=0, W_c=0, W_ca=0, sigma_obs=0)


def _vehiculos(o: OpcionVehiculo) -> e.Vehiculos:
    return e.Vehiculos(tipo_vehiculo_id=o.tipo_vehiculo_id, tipo=o.nombre, cantidad=o.viajes,
                       contenedores_por_vehiculo=list(o.reparto))


def _razon(r: Razon) -> e.RazonSalida:
    return e.RazonSalida(codigo=r.codigo, mensaje=r.mensaje, requerido=r.requerido, disponible=r.disponible)


def _desempeno(d: Desempeno) -> e.DesempenoSalida:
    return e.DesempenoSalida(valor=round(d.valor, 1), desglose=e.DesgloseDesempeno(
        puntualidad=round(d.puntualidad, 3), magnitud_retraso=round(d.magnitud_retraso, 3)),
        texto=t.texto_desempeno(d))


def _confianza(c: Confianza, n_servicios: int, n_cliente: Optional[int], cfg: Config) -> e.ConfianzaSalida:
    return e.ConfianzaSalida(valor=round(c.valor, 1), nivel=c.nivel, desglose=e.DesgloseConfianza(
        consistencia=round(c.consistencia, 3), cumplimiento_cliente=round(c.cumplimiento_cliente, 3), evidencia=round(c.evidencia, 3)),
        texto=t.texto_confianza(c, n_servicios, n_cliente, cfg))


def _pesos(cfg: Config) -> e.PesosPuntaje:
    p = cfg.puntaje
    return e.PesosPuntaje(profit=p.peso_profit, a_tiempo=p.peso_a_tiempo, desempeno=p.peso_desempeno,
                          confianza=p.peso_confianza, top_n=p.top_n)


def referencia_mercado(prior: Prior, cfg: Config) -> ReferenciaMercado:
    """Un proveedor promedio del segmento, para explicar cuando hay una sola opción."""
    d = calcular_desempeno(SUMAS_VACIAS, prior, cfg)
    q = calcular_confianza(SUMAS_VACIAS, prior, d.puntualidad, cfg).calidad
    return ReferenciaMercado(prob_a_tiempo=prior.P0, desempeno=d.valor, confianza=100 * q)


class ServicioEvaluacion:
    def __init__(self, repo: Repositorio, cfg: Config):
        self.repo = repo
        self.cfg = cfg

    def _mercado(self, hasta: date) -> tuple[list, Historial]:
        todos = self.repo.servicios_historicos(hasta=hasta)
        return todos, construir_historial(todos, hasta, self.cfg.recencia.vida_media_dias)

    def _prior(self, mercado: Historial, ruta_id: str, corredor: Optional[str]) -> Prior:
        rutas = {r.ruta_id for r in self.repo.rutas() if corredor is not None and r.corredor == corredor}
        return calcular_prior(mercado, ruta_id, rutas, self.cfg)

    def _nombres_segmentos(self, nombres: Optional[dict[str, str]] = None) -> tuple[dict[str, str], dict[str, str]]:
        """Nombres legibles de rutas ("Buenaventura → Bogotá") y de tipos de vehículo."""
        nombres = nombres or {u.ubicacion_id: u.nombre for u in self.repo.ubicaciones()}
        rutas = {r.ruta_id: f"{nombres.get(r.origen_id, r.origen_id)} → {nombres.get(r.destino_id, r.destino_id)}"
                 for r in self.repo.rutas()}
        return rutas, {x.tipo_vehiculo_id: x.nombre for x in self.repo.tipos_vehiculo()}

    # ------------------------------------------------------------------
    def evaluar(self, s: Solicitud, escenario_id: Optional[str] = None) -> e.Evaluacion:
        """Lanza `RutaNoEncontrada` si no existe la ruta origen→destino."""
        cfg = self.cfg
        resultado = filtrar(s, self.repo, cfg)
        ruta = resultado.ruta
        nombres = {u.ubicacion_id: u.nombre for u in self.repo.ubicaciones()}
        todos, mercado = self._mercado(s.fecha_servicio)
        prior = self._prior(mercado, ruta.ruta_id, ruta.corredor)

        rutas_txt, tipos_txt = self._nombres_segmentos(nombres)
        relevantes = {("ruta", ruta.ruta_id), ("carga", s.tipo_carga or "general")}
        calculos = {}
        for c in resultado.candidatos:
            pid = c.proveedor.proveedor_id
            propios = [x for x in todos if x.proveedor_id == pid]
            h = construir_historial(propios, s.fecha_servicio, cfg.recencia.vida_media_dias, cliente_id=s.cliente_id)
            sumas = h.sumas()
            d = calcular_desempeno(sumas, prior, cfg)
            conf = calcular_confianza(sumas, prior, d.puntualidad, cfg)
            entrada = preparar_entrada(pid, h, mercado, ruta.ruta_id, prior.sigma0,
                                       c.opcion.tiempo_prometido_h, s.plazo_h, cfg)
            fuertes, flojas = t.fortalezas_y_debilidades(propios, s.fecha_servicio, cfg, rutas_txt, tipos_txt)
            calculos[pid] = (c, h, sumas, d, conf, simular(entrada, cfg), fuertes, flojas)

        resumenes = [ResumenOpcion(pid, c.opcion.costo, sim.prob_a_tiempo, d.valor, conf.valor, int(h.c.sum()))
                     for pid, (c, h, sumas, d, conf, sim, _, _) in calculos.items()]
        explicaciones = explicar(resumenes, referencia_mercado(prior, cfg), cfg)

        entradas = [EntradaPuntaje(pid, c.opcion.costo, calcular_profit(s.presupuesto_cop, c.opcion.costo),
                                   sim.prob_a_tiempo, d.valor, conf.valor)
                    for pid, (c, h, sumas, d, conf, sim, _, _) in calculos.items()]

        candidatos = []
        for puesto, (x, pje) in enumerate(ordenar(entradas, cfg), start=1):
            c, h, sumas, d, conf, sim, fuertes, flojas = calculos[x.proveedor_id]
            margen = margen_pct(x.profit_cop, s.presupuesto_cop)
            n_cliente = int(h.c.sum())
            relevantes_p = relevantes | {("vehiculo", c.opcion.tipo_vehiculo_id)}
            candidatos.append(e.CandidatoSalida(
                proveedor_id=c.proveedor.proveedor_id, nombre=c.proveedor.nombre,
                puesto=puesto, top=puesto <= cfg.puntaje.top_n,
                puntaje=e.PuntajeSalida(valor=round(pje.valor, 1), desglose=e.DesglosePuntaje(
                    profit=round(pje.profit, 1), a_tiempo=round(pje.a_tiempo, 1),
                    desempeno=round(pje.desempeno, 1), confianza=round(pje.confianza, 1))),
                vehiculos=_vehiculos(c.opcion),
                costo_cop=c.opcion.costo,
                profit=e.Profit(cop=round(x.profit_cop), margen_pct=None if margen is None else round(margen, 1)),
                tiempo_h=e.TiempoH(p50=round(sim.tiempo_p50_h, 1), p90=round(sim.tiempo_p90_h, 1),
                                   prob_a_tiempo=round(sim.prob_a_tiempo, 3),
                                   abanico={f"{p:g}": round(v, 1) for p, v in sim.abanico_h.items()},
                                   resumen=t.resumen_tiempo(sim.tiempo_p50_h, sim.tiempo_p90_h, s.plazo_h,
                                                            sim.prob_a_tiempo)),
                capacidad=e.CapacidadSalida(
                    vehiculos_necesarios=c.opcion.viajes, vehiculos_libres=c.opcion.unidades_disponibles,
                    servicios_libres_dia=None if c.capacidad is None else c.capacidad.servicios_disponibles,
                    texto=t.texto_capacidad(c.opcion, c.capacidad, s.fecha_servicio)),
                historial=e.HistorialSalida(servicios=h.n, servicios_con_cliente=n_cliente),
                desempeno=_desempeno(d), confianza=_confianza(conf, h.n, n_cliente, cfg),
                fortalezas=t.para_tarjeta(fuertes, relevantes_p, cfg.ficha.max_en_tarjeta),
                debilidades=t.para_tarjeta(flojas, relevantes_p, cfg.ficha.max_en_tarjeta),
                riesgos=riesgos(h.n, conf, n_cliente, sim.prob_a_tiempo, cfg),
                explicacion=explicaciones[c.proveedor.proveedor_id].texto,
                avisos=list(c.avisos) + list(sim.avisos),
            ))

        return e.Evaluacion(
            solicitud_id=s.solicitud_id, escenario_id=escenario_id,
            ruta=e.RutaSalida(ruta_id=ruta.ruta_id, origen=nombres.get(ruta.origen_id, ruta.origen_id),
                              destino=nombres.get(ruta.destino_id, ruta.destino_id), distancia_km=ruta.distancia_km),
            candidatos=candidatos,
            cancelados=[e.CanceladoSalida(proveedor_id=x.proveedor.proveedor_id, nombre=x.proveedor.nombre,
                                          razones=[_razon(r) for r in x.razones]) for x in resultado.cancelados],
            casi_elegibles=[e.CasiElegibleSalida(proveedor_id=x.proveedor.proveedor_id, nombre=x.proveedor.nombre,
                                                 razon=_razon(x.razon), flexibilizar=x.flexibilizar,
                                                 vehiculos=None if x.opcion is None else _vehiculos(x.opcion))
                            for x in resultado.casi_elegibles],
            sin_candidatos=resultado.sin_candidatos,
            parametros_escenario=e.ParametrosEscenario(
                plazo_h=s.plazo_h, pesos_puntaje=_pesos(cfg),
                semilla=cfg.simulacion.semilla, n_simulaciones=cfg.simulacion.n),
        )

    # ------------------------------------------------------------------
    def ficha(self, proveedor_id: str, hoy: date) -> Optional[e.FichaProveedor]:
        """Historial, tendencia mensual de D, fortalezas y debilidades. `None` si no existe."""
        p = next((x for x in self.repo.proveedores() if x.proveedor_id == proveedor_id), None)
        if p is None:
            return None
        cfg = self.cfg
        H = cfg.recencia.vida_media_dias
        todos, mercado = self._mercado(hoy)
        nacional = self._prior(mercado, "", None)
        propios = [x for x in todos if x.proveedor_id == proveedor_id]
        h = construir_historial(propios, hoy, H)
        d = calcular_desempeno(h.sumas(), nacional, cfg)
        conf = calcular_confianza(h.sumas(), nacional, d.puntualidad, cfg)

        tendencia = []
        for mes in sorted({x.fecha_entrega.strftime("%Y-%m") for x in propios}):
            del_mes = [x for x in propios if x.fecha_entrega.strftime("%Y-%m") == mes]
            fin = max(x.fecha_entrega for x in del_mes)
            hm = construir_historial(del_mes, fin, H)
            tendencia.append(e.PuntoTendencia(mes=mes, servicios=hm.n,
                                              desempeno=round(calcular_desempeno(hm.sumas(), nacional, cfg).valor, 1)))

        fuertes, flojas = t.fortalezas_y_debilidades(propios, hoy, cfg, *self._nombres_segmentos())

        return e.FichaProveedor(
            proveedor_id=p.proveedor_id, nombre=p.nombre, estado=p.estado,
            cargas_especiales=list(p.cargas_especiales), servicios=h.n,
            ultimo_servicio=max((x.fecha_entrega for x in propios), default=None),
            puntualidad_pct=round(100 * float(h.a.mean()), 1) if h.n else None,
            desempeno=_desempeno(d), confianza=_confianza(conf, h.n, None, cfg), tendencia=tendencia,
            fortalezas=[x.texto for x in fuertes], debilidades=[x.texto for x in flojas],
        )
