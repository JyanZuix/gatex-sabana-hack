"""Fase 3: Monte Carlo, escenarios y explicaciones."""
from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from backend.calculos.confianza import Confianza, calcular_confianza
from backend.calculos.desempeno import calcular_desempeno
from backend.calculos.historial import construir_historial
from backend.calculos.priors import calcular_prior
from backend.calculos.profit import calcular_profit, margen_pct
from backend.filtro import filtrar
from backend.simulacion import (
    EntradaSimulacion,
    Escenario,
    ReferenciaMercado,
    ResumenOpcion,
    aplicar_escenario,
    explicar,
    preparar_entrada,
    riesgos,
    simular,
)


def _entrada(**kw):
    base = dict(
        clave="P1", tiempo_prometido_h=26.0, plazo_h=40.0,
        deltas_proveedor=np.array([0.0, 0.1, 0.2, -0.05]), pesos_proveedor=np.array([1.0, 1.0, 1.0, 1.0]),
        deltas_mercado=np.array([0.3, 0.4]), pesos_mercado=np.array([1.0, 1.0]), sigma0=0.2,
    )
    base.update(kw)
    return EntradaSimulacion(**base)


# Desviaciones continuas: con pocas desviaciones distintas los percentiles no cambian con la semilla
DELTAS_CONTINUAS = dict(deltas_proveedor=np.random.default_rng(0).normal(0.1, 0.15, 200), pesos_proveedor=np.ones(200))


# --- Desviación de tiempo --------------------------------------------------

def test_con_mucho_historial_se_parece_al_proveedor(cfg):
    e = _entrada(deltas_proveedor=np.full(1000, 0.1), pesos_proveedor=np.ones(1000),
                 deltas_mercado=np.full(10, 0.5), pesos_mercado=np.ones(10))
    r = simular(e, cfg)
    assert r.peso_historial_propio == pytest.approx(1000 / 1010)
    assert r.tiempo_p50_h == pytest.approx(26 * 1.1)


def test_sin_historial_se_parece_al_mercado(cfg):
    e = _entrada(deltas_proveedor=np.zeros(0), pesos_proveedor=np.zeros(0),
                 deltas_mercado=np.full(10, 0.5), pesos_mercado=np.ones(10))
    r = simular(e, cfg)
    assert r.peso_historial_propio == 0
    assert r.tiempo_p50_h == pytest.approx(26 * 1.5)


def test_mercado_vacio_usa_respaldo_y_avisa(cfg):
    e = _entrada(deltas_mercado=np.zeros(0), pesos_mercado=np.zeros(0))
    assert simular(e, cfg).avisos


def test_preparar_entrada_usa_todo_el_historial_si_hay_poco_en_la_ruta(cfg, repo):
    servicios = [s for s in repo.servicios_historicos() if s.proveedor_id == "PROV-09"]
    h = construir_historial(servicios, date(2026, 10, 23), cfg.recencia.vida_media_dias)
    mercado = construir_historial(repo.servicios_historicos(), date(2026, 10, 23), cfg.recencia.vida_media_dias)
    e = preparar_entrada("PROV-09", h, mercado, "R-BUN-BOG", 0.2, 26, 40, cfg)
    assert e.deltas_proveedor.size == h.n  # W_ruta < 5 → todo su historial


# --- Tiempo ----------------------------------------------------------------

def test_tiempo_y_llegada_a_tiempo_calculados_a_mano(cfg):
    # Δ siempre 0.5 → T = 26·1.5 = 39 h; plazo 40 → siempre a tiempo; plazo 38 → nunca
    e = _entrada(deltas_proveedor=np.full(5, 0.5), pesos_proveedor=np.ones(5) * 1000,
                 deltas_mercado=np.full(2, 0.5))
    assert simular(e, cfg).prob_a_tiempo == 1.0
    assert simular(replace(e, plazo_h=38.0), cfg).prob_a_tiempo == 0.0


# --- Profit ----------------------------------------------------------------

def test_profit_es_presupuesto_menos_costo():
    assert calcular_profit(12_000_000, 8_000_000) == 4_000_000
    assert margen_pct(4_000_000, 12_000_000) == pytest.approx(100 / 3)
    assert margen_pct(1, 0) is None


def test_resultado_golden(cfg):
    """Caso guardado: si cambia, cambió el algoritmo o la semilla."""
    r = simular(_entrada(plazo_h=30.0), cfg)
    assert (r.n, r.semilla) == (2000, 42)
    assert r.tiempo_p50_h == pytest.approx(GOLDEN["p50"], abs=1e-6)
    assert r.tiempo_p90_h == pytest.approx(GOLDEN["p90"], abs=1e-6)
    assert r.prob_a_tiempo == pytest.approx(GOLDEN["prob"], abs=1e-9)


# --- Reproducibilidad ------------------------------------------------------

def test_misma_semilla_mismos_resultados(cfg):
    e = _entrada()
    assert simular(e, cfg) == simular(e, cfg)


def test_semilla_distinta_resultados_distintos(cfg):
    # Muchos valores distintos de Δ: con pocos, dos semillas pueden dar los mismos percentiles.
    e = _entrada(deltas_proveedor=np.linspace(-0.2, 0.4, 500), pesos_proveedor=np.ones(500))
    assert simular(e, cfg, semilla=1).abanico_h != simular(e, cfg, semilla=2).abanico_h


def test_resultado_no_depende_del_orden_de_los_candidatos(cfg):
    a, b = _entrada(clave="P1"), _entrada(clave="P2")
    r1 = [simular(a, cfg), simular(b, cfg)]
    r2 = [simular(b, cfg), simular(a, cfg)]
    assert r1[0] == r2[1] and r1[1] == r2[0]


# --- Escenarios ------------------------------------------------------------

def test_escenario_no_toca_el_historial(cfg):
    e = _entrada()
    deltas = e.deltas_proveedor.copy()
    nueva = aplicar_escenario(e, Escenario(plazo_h=20))
    assert np.array_equal(e.deltas_proveedor, deltas) and e.plazo_h == 40.0
    assert simular(nueva, cfg).prob_a_tiempo < simular(e, cfg).prob_a_tiempo


def test_escenario_cambia_plazo(cfg):
    e = aplicar_escenario(_entrada(), Escenario(plazo_h=20))
    assert e.plazo_h == 20
    assert simular(e, cfg).prob_a_tiempo == 0.0


def test_escenario_invalido():
    with pytest.raises(ValueError):
        Escenario(plazo_h=-1)


# --- Explicaciones ---------------------------------------------------------

REF = ReferenciaMercado(prob_a_tiempo=0.85, desempeno=86.25, confianza=60.0)


def _resumen(pid, costo, prob, D, C, Wc):
    return ResumenOpcion(pid, costo, prob, D, C, Wc)


def test_explicacion_trazable(cfg):
    ops = [_resumen("A", 9_800_000, 0.87, 89.4, 66.3, 8),
           _resumen("B", 9_200_000, 0.70, 82.0, 50.0, 0),
           _resumen("C", 11_000_000, 0.95, 92.0, 80.0, 15)]
    exp = explicar(ops, REF, cfg)
    claves_validas = {"costo_cop", "prob_a_tiempo", "desempeno", "confianza", "servicios_con_cliente"}
    for e in exp.values():
        assert len(e.a_favor) <= cfg.explicacion.max_factores and len(e.en_contra) <= cfg.explicacion.max_factores
        for f in e.a_favor + e.en_contra:
            assert f.clave in claves_validas
            assert f.texto in e.texto
    assert "más económica" in exp["B"].texto
    assert any(f.clave == "costo_cop" for f in exp["C"].en_contra)
    assert all(f.impacto > 0 for f in exp["C"].a_favor)


def test_explicacion_opcion_unica_usa_mercado(cfg):
    exp = explicar([_resumen("A", 9_800_000, 0.95, 92.0, 80.0, 8)], REF, cfg)["A"]
    assert all(f.clave != "costo_cop" for f in exp.a_favor + exp.en_contra)
    assert exp.a_favor and exp.a_favor[0].referencia in {REF.prob_a_tiempo, REF.desempeno, REF.confianza, 0.0}


def _conf(valor, nivel, n_efectivo, consistencia):
    return Confianza(valor=valor, nivel=nivel, consistencia=consistencia, cumplimiento_cliente=0.8, evidencia=0.5,
                     calidad=0.6, sigma_ajustada=0.2, n_efectivo=n_efectivo, E=0.3)


def test_riesgos_con_su_dato(cfg):
    lista = riesgos(n_servicios=4, conf=_conf(36.4, "Baja", 4.1, 0.55), servicios_con_cliente=0,
                    prob_a_tiempo=0.62, cfg=cfg)
    assert lista == ["Pocos datos: 4 servicios en su historial", "Nunca ha trabajado con este cliente",
                     "Llega a tiempo solo en el 62 % de las simulaciones (se espera al menos 70 %)",
                     "Confianza baja (36/100): pocos datos y tiempos algo variables"]
    assert all("efectivo" not in r for r in lista)
    # Con mucho historial la confianza baja se explica solo por la variabilidad
    assert riesgos(n_servicios=60, conf=_conf(48, "Baja", 50, 0.2), servicios_con_cliente=5, prob_a_tiempo=0.9,
                   cfg=cfg) == ["Confianza baja (48/100): tiempos muy variables"]
    assert riesgos(n_servicios=60, conf=_conf(70, "Media", 50, 0.8), servicios_con_cliente=5, prob_a_tiempo=0.9,
                   cfg=cfg) == []


# --- Integración con datos sintéticos --------------------------------------

def test_flujo_completo_filtro_calculo_simulacion(cfg, repo, solicitud_base):
    """Recorre filtro → D y C → simulación para cada candidato, sin la capa de API."""
    s = solicitud_base
    resultado = filtrar(s, repo, cfg)
    todos = repo.servicios_historicos(hasta=s.fecha_servicio)
    mercado = construir_historial(todos, s.fecha_servicio, cfg.recencia.vida_media_dias)
    corredor = {r.ruta_id for r in repo.rutas() if r.corredor == resultado.ruta.corredor}
    prior = calcular_prior(mercado, resultado.ruta.ruta_id, corredor, cfg)

    resultados = {}
    for c in resultado.candidatos:
        pid = c.proveedor.proveedor_id
        h = construir_historial([x for x in todos if x.proveedor_id == pid], s.fecha_servicio,
                                cfg.recencia.vida_media_dias, cliente_id=s.cliente_id)
        d = calcular_desempeno(h.sumas(), prior, cfg)
        conf = calcular_confianza(h.sumas(), prior, d.puntualidad, cfg)
        e = preparar_entrada(pid, h, mercado, resultado.ruta.ruta_id, prior.sigma0,
                             c.opcion.tiempo_prometido_h, s.plazo_h, cfg)
        resultados[pid] = (d, conf, simular(e, cfg))

    assert set(resultados) == {"PROV-01", "PROV-02", "PROV-03", "PROV-06", "PROV-09"}
    for d, conf, sim in resultados.values():
        assert 0 <= d.valor <= 100 and 0 <= conf.valor <= 100
        assert 0 <= sim.prob_a_tiempo <= 1 and sim.tiempo_p50_h <= sim.tiempo_p90_h
    # El proveedor nuevo (3 servicios) tiene confianza más baja que los veteranos
    assert resultados["PROV-09"][1].valor < min(resultados[p][1].valor for p in ("PROV-01", "PROV-03"))
    # Carga Segura (tiempos muy consistentes) supera a Montaña Cargo (más dispersa) en confianza
    assert resultados["PROV-03"][1].valor > resultados["PROV-06"][1].valor


# Regenerado el 2026-10-24 al quitar la demora por vía de la simulación. Sin profit desde que se
# eliminó el costo por retraso: el tiempo no cambió porque la secuencia aleatoria es la misma.
GOLDEN = {"p50": 33.8, "p90": 36.4, "prob": 0.2305}
