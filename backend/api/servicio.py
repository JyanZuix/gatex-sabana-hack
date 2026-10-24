"""Orquestación: filtro → Desempeño y Confianza → simulación → explicación.

La API solo traduce HTTP; toda la lógica sale de `filtro/`, `calculos/` y `simulacion/`.
No ordena ni elige: devuelve las opciones y el funcionario decide.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from backend.calculos.confianza import Confianza, calcular_confianza
from backend.calculos.costos import OpcionVehiculo
from backend.calculos.desempeno import Desempeno, calcular_desempeno
from backend.calculos.historial import Historial, Sumas, construir_historial
from backend.calculos.priors import Prior, calcular_prior
from backend.config import Config
from backend.datos import Repositorio
from backend.dominio import Solicitud
from backend.filtro import filtrar
from backend.filtro.modelos import Razon
from backend.simulacion import ReferenciaMercado, ResumenOpcion, explicar, preparar_entrada, riesgos, simular

from . import esquemas as e

SUMAS_VACIAS = Sumas(W=0, W_a=0, W_r=0, W_c=0, W_ca=0, sigma_obs=0)


def _vehiculos(o: OpcionVehiculo) -> e.Vehiculos:
    return e.Vehiculos(tipo_vehiculo_id=o.tipo_vehiculo_id, tipo=o.nombre, cantidad=o.viajes,
                       contenedores_por_vehiculo=list(o.reparto))


def _razon(r: Razon) -> e.RazonSalida:
    return e.RazonSalida(codigo=r.codigo, mensaje=r.mensaje, requerido=r.requerido, disponible=r.disponible)


def _desempeno(d: Desempeno) -> e.DesempenoSalida:
    return e.DesempenoSalida(valor=round(d.valor, 1), desglose=e.DesgloseDesempeno(
        puntualidad=round(d.puntualidad, 3), magnitud_retraso=round(d.magnitud_retraso, 3)))


def _confianza(c: Confianza) -> e.ConfianzaSalida:
    return e.ConfianzaSalida(valor=round(c.valor, 1), nivel=c.nivel, desglose=e.DesgloseConfianza(
        consistencia=round(c.consistencia, 3), cumplimiento_cliente=round(c.cumplimiento_cliente, 3), evidencia=round(c.evidencia, 3)))


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

    # ------------------------------------------------------------------
    def evaluar(self, s: Solicitud, escenario_id: Optional[str] = None) -> e.Evaluacion:
        """Lanza `RutaNoEncontrada` si no existe la ruta origen→destino."""
        cfg = self.cfg
        resultado = filtrar(s, self.repo, cfg)
        ruta = resultado.ruta
        nombres = {u.ubicacion_id: u.nombre for u in self.repo.ubicaciones()}
        todos, mercado = self._mercado(s.fecha_servicio)
        prior = self._prior(mercado, ruta.ruta_id, ruta.corredor)
        penal = cfg.escenario.penal_hora_cop if s.penal_hora_cop is None else s.penal_hora_cop

        calculos = []
        for c in resultado.candidatos:
            pid = c.proveedor.proveedor_id
            h = construir_historial([x for x in todos if x.proveedor_id == pid], s.fecha_servicio,
                                    cfg.recencia.vida_media_dias, cliente_id=s.cliente_id)
            sumas = h.sumas()
            d = calcular_desempeno(sumas, prior, cfg)
            conf = calcular_confianza(sumas, prior, d.puntualidad, cfg)
            entrada = preparar_entrada(pid, h, mercado, ruta.ruta_id, prior.sigma0,
                                       c.opcion.tiempo_prometido_h, s.plazo_h, c.opcion.costo,
                                       s.presupuesto_cop, penal, cfg)
            calculos.append((c, sumas, d, conf, simular(entrada, cfg)))

        resumenes = [ResumenOpcion(c.proveedor.proveedor_id, c.opcion.costo, sim.prob_a_tiempo, d.valor,
                                   conf.valor, sumas.W_c)
                     for c, sumas, d, conf, sim in calculos]
        explicaciones = explicar(resumenes, referencia_mercado(prior, cfg), cfg)

        candidatos = []
        for c, sumas, d, conf, sim in calculos:
            lista_riesgos = riesgos(conf.n_efectivo, sumas.W_c, cfg)
            if c.opcion.costo > s.presupuesto_cop:
                lista_riesgos.append("El costo supera el presupuesto")
            candidatos.append(e.CandidatoSalida(
                proveedor_id=c.proveedor.proveedor_id, nombre=c.proveedor.nombre,
                vehiculos=_vehiculos(c.opcion),
                costo_cop=c.opcion.costo,
                profit=e.Profit(esperado_cop=round(sim.profit_esperado_cop), p10_cop=round(sim.profit_p10_cop),
                                margen_pct=None if sim.margen_pct is None else round(sim.margen_pct, 1)),
                tiempo_h=e.TiempoH(p50=round(sim.tiempo_p50_h, 1), p90=round(sim.tiempo_p90_h, 1),
                                   prob_a_tiempo=round(sim.prob_a_tiempo, 3),
                                   abanico={f"{p:g}": round(v, 1) for p, v in sim.abanico_h.items()}),
                desempeno=_desempeno(d), confianza=_confianza(conf),
                riesgos=lista_riesgos, explicacion=explicaciones[c.proveedor.proveedor_id].texto,
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
            parametros_escenario=e.ParametrosEscenario(plazo_h=s.plazo_h, penal_hora_cop=penal,
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

        fortalezas, debilidades = [], []
        if h.n:
            punt = float(h.a.mean())
            nombres = {u.ubicacion_id: u.nombre for u in self.repo.ubicaciones()}
            rutas = {r.ruta_id: f"{nombres.get(r.origen_id, r.origen_id)} → {nombres.get(r.destino_id, r.destino_id)}"
                     for r in self.repo.rutas()}
            tipos = {t.tipo_vehiculo_id: t.nombre for t in self.repo.tipos_vehiculo()}
            segmentos = [(f"la ruta {rutas.get(r, r)}", [x for x in propios if x.ruta_id == r])
                         for r in sorted({x.ruta_id for x in propios})]
            segmentos += [(f"vehículo {tipos.get(t, t)}", [x for x in propios if x.tipo_vehiculo_id == t])
                          for t in sorted({x.tipo_vehiculo_id for x in propios})]
            u = cfg.ficha.umbral_diferencia
            for nombre, servicios in segmentos:
                hs = construir_historial(servicios, hoy, H)
                if hs.n < cfg.ficha.min_servicios_segmento:
                    continue
                p_seg = float(hs.a.mean())
                detalle = f"{hs.n} servicios"
                if p_seg >= punt + u:
                    fortalezas.append(f"Puntualidad de {p_seg:.0%} en {nombre} (su promedio: {punt:.0%}; {detalle})")
                elif p_seg <= punt - u:
                    debilidades.append(f"Puntualidad de {p_seg:.0%} en {nombre} (su promedio: {punt:.0%}; {detalle})")

        return e.FichaProveedor(
            proveedor_id=p.proveedor_id, nombre=p.nombre, estado=p.estado,
            cargas_especiales=list(p.cargas_especiales), servicios=h.n,
            ultimo_servicio=max((x.fecha_entrega for x in propios), default=None),
            puntualidad_pct=round(100 * float(h.a.mean()), 1) if h.n else None,
            desempeno=_desempeno(d), confianza=_confianza(conf), tendencia=tendencia,
            fortalezas=fortalezas, debilidades=debilidades,
        )
