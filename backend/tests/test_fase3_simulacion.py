"""Fase 3: Monte Carlo, escenarios y explicaciones."""
from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from backend.calculos.confianza import calcular_confianza
from backend.calculos.desempeno import calcular_desempeno
from backend.calculos.historial import construir_historial, severidad_por_servicio
from backend.calculos.priors import calcular_prior
from backend.dominio import CondicionVia
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
        clave="P1", tiempo_prometido_h=26.0, plazo_h=40.0, costo_cop=8_000_000, presupuesto_cop=12_000_000,
        penal_hora_cop=0.0,
        deltas_proveedor=np.array([0.0, 0.1, 0.2, -0.05]), pesos_proveedor=np.array([1.0, 1.0, 1.0, 1.0]),
        deltas_mercado=np.array([0.3, 0.4]), pesos_mercado=np.array([1.0, 1.0]), sigma0=0.2,
        p_evento=0.0, demora_min_h=0.0, demora_max_h=0.0, indice_incidentes=0.05,
        severidades_proveedor=np.array([0.3, 0.6]),
    )
    base.update(kw)
    return EntradaSimulacion(**base)


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
    h = construir_historial(servicios, {}, date(2026, 10, 23), cfg.recencia.vida_media_dias)
    mercado = construir_historial(repo.servicios_historicos(), {}, date(2026, 10, 23), cfg.recencia.vida_media_dias)
    e = preparar_entrada("PROV-09", h, mercado, "R-BUN-BOG", 0.05, 0.2, 26, 40, 1, 1, 0, None, cfg)
    assert e.deltas_proveedor.size == h.n  # W_ruta < 5 → todo su historial


# --- Vía, tiempo e incidentes ----------------------------------------------

def test_sin_evento_no_hay_demora(cfg):
    e = _entrada(deltas_proveedor=np.zeros(1000), pesos_proveedor=np.ones(1000), p_evento=0.0,
                 demora_min_h=5, demora_max_h=10)
    r = simular(e, cfg)
    assert r.abanico_h[95] == pytest.approx(26.0, abs=1.0)


def test_evento_seguro_demora_dentro_del_rango(cfg):
    e = _entrada(deltas_proveedor=np.zeros(1000), pesos_proveedor=np.ones(1000),
                 deltas_mercado=np.zeros(2), p_evento=1.0, demora_min_h=5, demora_max_h=10)
    r = simular(e, cfg)
    assert 26 + 5 <= r.abanico_h[5] and r.abanico_h[95] <= 26 + 10


def test_tiempo_y_llegada_a_tiempo_calculados_a_mano(cfg):
    # Δ siempre 0.5 → T = 26·1.5 = 39 h; plazo 40 → siempre a tiempo; plazo 38 → nunca
    e = _entrada(deltas_proveedor=np.full(5, 0.5), pesos_proveedor=np.ones(5) * 1000,
                 deltas_mercado=np.full(2, 0.5))
    assert simular(e, cfg).prob_a_tiempo == 1.0
    assert simular(replace(e, plazo_h=38.0), cfg).prob_a_tiempo == 0.0


def test_sin_incidentes_en_historial(cfg):
    I0 = cfg.prior.por_defecto.I0
    e = _entrada(indice_incidentes=I0, severidades_proveedor=np.zeros(0))
    r = simular(e, cfg)
    esperado = I0 / cfg.simulacion.severidad_media_sin_historial
    assert r.prob_incidente == pytest.approx(esperado, abs=0.02)


def test_probabilidad_de_incidente_con_historial(cfg):
    e = _entrada(indice_incidentes=0.09, severidades_proveedor=np.array([0.3, 0.6]))
    assert simular(e, cfg).prob_incidente == pytest.approx(0.09 / 0.45, abs=0.03)


# --- Costo y profit --------------------------------------------------------

def test_sin_penal_no_hay_costo_de_retraso(cfg):
    r = simular(_entrada(plazo_h=20.0), cfg)
    assert r.costo_esperado_retraso_cop == 0
    assert r.profit_esperado_cop == 12_000_000 - 8_000_000


def test_costo_de_retraso_crece_con_la_penal(cfg):
    corto = _entrada(plazo_h=20.0)
    bajo = simular(replace(corto, penal_hora_cop=10_000), cfg)
    alto = simular(replace(corto, penal_hora_cop=50_000), cfg)
    assert 0 < bajo.costo_esperado_retraso_cop < alto.costo_esperado_retraso_cop
    assert alto.profit_esperado_cop == pytest.approx(12_000_000 - 8_000_000 - alto.costo_esperado_retraso_cop)
    assert alto.profit_p10_cop <= alto.profit_esperado_cop


def test_resultado_golden(cfg):
    """Caso guardado: si cambia, cambió el algoritmo o la semilla."""
    r = simular(_entrada(p_evento=0.15, demora_min_h=4, demora_max_h=12, penal_hora_cop=20_000, plazo_h=30.0), cfg)
    assert (r.n, r.semilla) == (2000, 42)
    assert r.tiempo_p50_h == pytest.approx(GOLDEN["p50"], abs=1e-6)
    assert r.tiempo_p90_h == pytest.approx(GOLDEN["p90"], abs=1e-6)
    assert r.prob_a_tiempo == pytest.approx(GOLDEN["prob"], abs=1e-9)
    assert r.profit_esperado_cop == pytest.approx(GOLDEN["profit"], abs=1e-3)


# --- Reproducibilidad ------------------------------------------------------

def test_misma_semilla_mismos_resultados(cfg):
    e = _entrada(p_evento=0.2, demora_min_h=2, demora_max_h=8)
    assert simular(e, cfg) == simular(e, cfg)


def test_semilla_distinta_resultados_distintos(cfg):
    e = _entrada(p_evento=0.2, demora_min_h=2, demora_max_h=8)
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
    nueva = aplicar_escenario(e, Escenario(p_evento=1.0, demora_min_h=10, demora_max_h=20))
    assert np.array_equal(e.deltas_proveedor, deltas) and e.p_evento == 0.0
    assert simular(nueva, cfg).tiempo_p90_h > simular(e, cfg).tiempo_p90_h


def test_escenario_cambia_plazo_y_penal(cfg):
    e = aplicar_escenario(_entrada(), Escenario(plazo_h=20, penal_hora_cop=10_000))
    assert (e.plazo_h, e.penal_hora_cop) == (20, 10_000)
    assert simular(e, cfg).prob_a_tiempo == 0.0


@pytest.mark.parametrize("kw", [dict(p_evento=1.5), dict(plazo_h=-1), dict(penal_hora_cop=-5)])
def test_escenario_invalido(kw):
    with pytest.raises(ValueError):
        Escenario(**kw)


def test_escenario_con_rango_de_demora_invertido():
    with pytest.raises(ValueError):
        aplicar_escenario(_entrada(), Escenario(demora_min_h=10, demora_max_h=2))


# --- Explicaciones ---------------------------------------------------------

REF = ReferenciaMercado(prob_a_tiempo=0.85, desempeno=86.25, confianza=60.0, prob_incidente=0.1)


def _resumen(pid, costo, prob, D, C, Wc, inc):
    return ResumenOpcion(pid, costo, prob, D, C, Wc, inc)


def test_explicacion_trazable(cfg):
    ops = [_resumen("A", 9_800_000, 0.87, 89.4, 73.7, 8, 0.05),
           _resumen("B", 9_200_000, 0.70, 82.0, 55.0, 0, 0.12),
           _resumen("C", 11_000_000, 0.95, 92.0, 80.0, 15, 0.02)]
    exp = explicar(ops, REF, cfg)
    claves_validas = {"costo_cop", "prob_a_tiempo", "desempeno", "confianza", "servicios_con_cliente", "prob_incidente"}
    for e in exp.values():
        assert len(e.a_favor) <= cfg.explicacion.max_factores and len(e.en_contra) <= cfg.explicacion.max_factores
        for f in e.a_favor + e.en_contra:
            assert f.clave in claves_validas
            assert f.texto in e.texto
    assert "más económica" in exp["B"].texto
    assert any(f.clave == "costo_cop" for f in exp["C"].en_contra)
    assert all(f.impacto > 0 for f in exp["C"].a_favor)


def test_explicacion_opcion_unica_usa_mercado(cfg):
    exp = explicar([_resumen("A", 9_800_000, 0.95, 92.0, 80.0, 8, 0.02)], REF, cfg)["A"]
    assert all(f.clave != "costo_cop" for f in exp.a_favor + exp.en_contra)
    assert exp.a_favor and exp.a_favor[0].referencia in {REF.prob_a_tiempo, REF.desempeno, REF.confianza,
                                                          REF.prob_incidente, 0.0}


def test_riesgos(cfg):
    cond = CondicionVia(corredor="X", fecha_hora="2026-10-20T08:00:00", p_evento=0.15, demora_min_h=4,
                        demora_max_h=12, descripcion="Bloqueo")
    lista = riesgos(cond, n_efectivo=4, servicios_con_cliente=0, cfg=cfg)
    assert lista[0].startswith("Corredor con 15 % de probabilidad")
    assert len(lista) == 3
    assert riesgos(None, n_efectivo=50, servicios_con_cliente=5, cfg=cfg) == []


# --- Integración con datos sintéticos --------------------------------------

def test_flujo_completo_filtro_calculo_simulacion(cfg, repo, solicitud_base):
    """Recorre filtro → D y C → simulación para cada candidato, sin la capa de API."""
    s = solicitud_base
    resultado = filtrar(s, repo, cfg)
    sev = severidad_por_servicio(repo.incidentes())
    todos = repo.servicios_historicos(hasta=s.fecha_servicio)
    mercado = construir_historial(todos, sev, s.fecha_servicio, cfg.recencia.vida_media_dias)
    corredor = {r.ruta_id for r in repo.rutas() if r.corredor == resultado.ruta.corredor}
    prior = calcular_prior(mercado, resultado.ruta.ruta_id, corredor, cfg)
    cond = repo.condicion_via(resultado.ruta.corredor, s.fecha_servicio)

    resultados = {}
    for c in resultado.candidatos:
        pid = c.proveedor.proveedor_id
        h = construir_historial([x for x in todos if x.proveedor_id == pid], sev, s.fecha_servicio,
                                cfg.recencia.vida_media_dias, cliente_id=s.cliente_id)
        d = calcular_desempeno(h.sumas(), prior, cfg)
        conf = calcular_confianza(h.sumas(), prior, d.puntualidad, cfg)
        e = preparar_entrada(pid, h, mercado, resultado.ruta.ruta_id, conf.indice_incidentes, prior.sigma0,
                             c.opcion.tiempo_prometido_h, s.plazo_h, c.opcion.costo, s.presupuesto_cop,
                             cfg.escenario.penal_hora_cop, cond, cfg)
        resultados[pid] = (d, conf, simular(e, cfg))

    assert set(resultados) == {"PROV-01", "PROV-02", "PROV-03", "PROV-06", "PROV-09"}
    for d, conf, sim in resultados.values():
        assert 0 <= d.valor <= 100 and 0 <= conf.valor <= 100
        assert 0 <= sim.prob_a_tiempo <= 1 and sim.tiempo_p50_h <= sim.tiempo_p90_h
    # El proveedor nuevo (3 servicios) tiene confianza más baja que los veteranos
    assert resultados["PROV-09"][1].valor < min(resultados[p][1].valor for p in ("PROV-01", "PROV-03"))
    # Carga Segura (muy puntual) supera a Montaña Cargo (más incidentes) en confianza
    assert resultados["PROV-03"][1].valor > resultados["PROV-06"][1].valor


GOLDEN = {"p50": 33.8, "p90": 38.9906102673518, "prob": 0.204, "profit": 3906648.6697019013}
