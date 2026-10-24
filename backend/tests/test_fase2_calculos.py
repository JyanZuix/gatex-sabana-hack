"""Fase 2: recencia, Desempeño, Confianza, costos y profit.

El ejemplo resuelto de docs/calculos_simulacion.md (sección 4) se reproduce con ±0.1.
"""
from datetime import date, timedelta

import numpy as np
import pytest

from backend.calculos.confianza import calcular_confianza, nivel_confianza
from backend.calculos.costos import (
    opcion_mas_economica,
    opciones_vehiculo,
    tipos_validos,
    viajes_necesarios,
)
from backend.calculos.desempeno import calcular_desempeno
from backend.calculos.historial import Sumas, construir_historial, severidad_por_servicio
from backend.calculos.priors import calcular_prior, prior_por_defecto
from backend.calculos.profit import calcular_profit, margen_pct
from backend.calculos.recencia import peso_recencia
from backend.dominio import Incidente, ServicioHistorico, Solicitud, Tarifa, TipoVehiculo

HOY = date(2026, 10, 23)

# Ejemplo de la sección 4
A = Sumas(W=30, W_a=27, W_r=2.4, W_inc=1.5, W_c=8, W_ca=7, sigma_obs=0.15)
B = Sumas(W=4, W_a=4, W_r=0, W_inc=0, W_c=4, W_ca=4, sigma_obs=0.05)


def _servicio(i, dias, real=10.0, prometido=10.0, plazo=11.0, cliente="CLI", ruta="R1", a_tiempo=None):
    return ServicioHistorico(servicio_id=f"S{i}", proveedor_id="P", cliente_id=cliente, ruta_id=ruta,
                             tipo_vehiculo_id="V", fecha_entrega=HOY - timedelta(days=dias),
                             tiempo_prometido_h=prometido, tiempo_real_h=real, plazo_acordado_h=plazo,
                             a_tiempo=a_tiempo)


# --- Recencia --------------------------------------------------------------

def test_peso_recencia(cfg):
    H = cfg.recencia.vida_media_dias
    assert peso_recencia(0, H) == 1.0
    assert peso_recencia(365, H) == pytest.approx(0.5)
    assert peso_recencia(730, H) == pytest.approx(0.25)


def test_incidente_grave_de_24_meses_pesa_un_cuarto(cfg):
    servicios = [_servicio(1, 0), _servicio(2, 730)]
    sev = {"S1": cfg.severidad.grave, "S2": cfg.severidad.grave}
    h = construir_historial(servicios, sev, HOY, cfg.recencia.vida_media_dias)
    assert h.w[1] * h.s[1] == pytest.approx(0.25 * h.w[0] * h.s[0])


# --- Sumas ponderadas ------------------------------------------------------

def test_sumas_ponderadas_a_mano(cfg):
    servicios = [
        _servicio(1, 0, real=12, cliente="CLI"),        # Δ=0.2, tarde (12 > 11)
        _servicio(2, 365, real=9, cliente="OTRO"),      # Δ=-0.1, a tiempo
        _servicio(3, 730, real=10, cliente="CLI"),      # Δ=0, a tiempo
    ]
    incidentes = [Incidente(servicio_id="S1", tipo="leve", severidad=0.3),
                  Incidente(servicio_id="S1", tipo="grave", severidad=1.0)]
    h = construir_historial(servicios, severidad_por_servicio(incidentes), HOY,
                            cfg.recencia.vida_media_dias, cliente_id="CLI")
    s = h.sumas()
    assert s.W == pytest.approx(1.75)
    assert s.W_a == pytest.approx(0.75)
    assert s.W_r == pytest.approx(0.2)
    assert s.W_inc == pytest.approx(1.0)  # máximo de los incidentes, no la suma
    assert s.W_c == pytest.approx(1.25)
    assert s.W_ca == pytest.approx(0.25)
    media = (0.2 - 0.05 + 0) / 1.75
    var = (1 * (0.2 - media) ** 2 + 0.5 * (-0.1 - media) ** 2 + 0.25 * (0 - media) ** 2) / 1.75
    assert s.sigma_obs == pytest.approx(np.sqrt(var))


def test_historial_calcula_a_tiempo_y_omite_sin_datos(cfg):
    servicios = [
        _servicio(1, 0, real=12, plazo=11),                        # a_tiempo se calcula: tarde
        _servicio(2, 0, plazo=None),                               # sin a_tiempo ni plazo → se omite
        _servicio(3, 0, prometido=None),                           # sin prometido y sin respaldo → se omite
    ]
    h = construir_historial(servicios, {}, HOY, cfg.recencia.vida_media_dias)
    assert h.n == 1 and h.a[0] == 0
    assert len(h.omitidos) == 2


def test_historial_usa_tiempo_de_tarifa_como_respaldo(cfg):
    h = construir_historial([_servicio(1, 0, real=12, prometido=None)], {}, HOY,
                            cfg.recencia.vida_media_dias, tiempo_prometido_respaldo=lambda s: 10.0)
    assert h.delta[0] == pytest.approx(0.2)


def test_historial_es_de_solo_lectura(cfg):
    h = construir_historial([_servicio(1, 0)], {}, HOY, cfg.recencia.vida_media_dias)
    with pytest.raises(ValueError):
        h.delta[0] = 5


# --- Priors ----------------------------------------------------------------

def test_prior_cae_al_siguiente_nivel(cfg):
    minimo = cfg.prior.min_servicios_segmento
    pocos_en_ruta = [_servicio(i, 10, ruta="R1") for i in range(3)]
    en_corredor = [_servicio(100 + i, 10, ruta="R2") for i in range(minimo)]
    otros = [_servicio(200 + i, 10, ruta="R9") for i in range(minimo)]
    mercado = construir_historial(pocos_en_ruta + en_corredor + otros, {}, HOY, cfg.recencia.vida_media_dias)
    assert calcular_prior(mercado, "R1", {"R1", "R2"}, cfg).nivel == "corredor"
    assert calcular_prior(mercado, "R1", {"R1"}, cfg).nivel == "nacional"
    vacio = construir_historial([], {}, HOY, cfg.recencia.vida_media_dias)
    assert calcular_prior(vacio, "R1", {"R1"}, cfg).nivel == "por_defecto"


# --- Desempeño y Confianza: ejemplo de la sección 4 -------------------------

@pytest.mark.parametrize("sumas,P,Ret,D", [(A, 0.887, 0.085, 89.4), (B, 0.893, 0.071, 90.2)])
def test_desempeno_ejemplo(cfg, sumas, P, Ret, D):
    d = calcular_desempeno(sumas, prior_por_defecto(cfg), cfg)
    assert d.puntualidad == pytest.approx(P, abs=1e-3)
    assert d.magnitud_retraso == pytest.approx(Ret, abs=1e-3)
    assert d.valor == pytest.approx(D, abs=0.1)


@pytest.mark.parametrize("sumas,sigma_aj,S_desv,I,S_inc,S_cump,Q,n_ef,E,F,C", [
    (A, 0.164, 0.672, 0.050, 0.950, 0.882, 0.825, 46, 0.821, 0.893, 73.7),
    (B, 0.171, 0.658, 0.036, 0.964, 0.923, 0.834, 12, 0.545, 0.727, 60.6),
])
def test_confianza_ejemplo(cfg, sumas, sigma_aj, S_desv, I, S_inc, S_cump, Q, n_ef, E, F, C):
    prior = prior_por_defecto(cfg)
    P = calcular_desempeno(sumas, prior, cfg).puntualidad
    c = calcular_confianza(sumas, prior, P, cfg)
    assert c.sigma_ajustada == pytest.approx(sigma_aj, abs=1e-3)
    assert c.consistencia == pytest.approx(S_desv, abs=1e-3)
    assert c.indice_incidentes == pytest.approx(I, abs=1e-3)
    assert c.incidentes == pytest.approx(S_inc, abs=1e-3)
    assert c.cumplimiento_cliente == pytest.approx(S_cump, abs=1e-3)
    assert c.calidad == pytest.approx(Q, abs=1e-3)
    assert c.n_efectivo == pytest.approx(n_ef)
    assert c.E == pytest.approx(E, abs=1e-3)
    assert c.evidencia == pytest.approx(F, abs=1e-3)
    assert c.valor == pytest.approx(C, abs=0.1)
    assert c.nivel == "Media"


def test_sin_historial_con_cliente_cumplimiento_es_P(cfg):
    s = Sumas(W=20, W_a=18, W_r=1, W_inc=0.5, W_c=0, W_ca=0, sigma_obs=0.1)
    prior = prior_por_defecto(cfg)
    P = calcular_desempeno(s, prior, cfg).puntualidad
    assert calcular_confianza(s, prior, P, cfg).cumplimiento_cliente == pytest.approx(P)


def test_proveedor_sin_historial(cfg):
    prior = prior_por_defecto(cfg)
    vacio = Sumas(W=0, W_a=0, W_r=0, W_inc=0, W_c=0, W_ca=0, sigma_obs=0)
    d = calcular_desempeno(vacio, prior, cfg)
    assert d.valor == pytest.approx(100 * (0.75 * prior.P0 + 0.25 * (1 - prior.R0)))
    Q0 = 0.4 * (1 - prior.sigma0 / 0.5) + 0.4 * (1 - prior.I0) + 0.2 * prior.P0
    c = calcular_confianza(vacio, prior, d.puntualidad, cfg)
    assert c.valor == pytest.approx(100 * Q0 * 0.4)
    assert c.valor > 0  # confianza baja pero real: oportunidad de entrar


@pytest.mark.parametrize("valor,nivel", [(80, "Alta"), (75, "Alta"), (74.9, "Media"), (55, "Media"), (54.9, "Baja")])
def test_niveles_de_confianza(cfg, valor, nivel):
    assert nivel_confianza(valor, cfg) == nivel


# --- Costos y vehículos ----------------------------------------------------

PLAT = TipoVehiculo(tipo_vehiculo_id="PLAT", nombre="Plataforma 2 TEU", cap_teu=2, cap_toneladas=34)
SENC = TipoVehiculo(tipo_vehiculo_id="SENC", nombre="Sencillo 1 TEU", cap_teu=1, cap_toneladas=17)
REFRI = TipoVehiculo(tipo_vehiculo_id="REFRI", nombre="Refrigerado", cap_teu=2, cap_toneladas=30, carga_especial="refrigerado")
CAMA = TipoVehiculo(tipo_vehiculo_id="CAMA", nombre="Cama baja", cap_teu=0, cap_toneladas=45, carga_especial="sobredimensionado")


def _solicitud(**kw):
    base = dict(cliente_id="C", origen_id="A", destino_id="B", fecha_servicio=HOY, plazo_h=40, presupuesto_cop=1)
    base.update(kw)
    return Solicitud(**base)


def _tarifa(tipo, precio, horas=20):
    return Tarifa(tarifa_id=f"T-{tipo}", proveedor_id="P", ruta_id="R", tipo_vehiculo_id=tipo,
                  precio_viaje=precio, tiempo_prometido_h=horas, vigente_desde=date(2025, 1, 1))


def test_viajes_3_teu_con_plataforma_2_teu():
    assert viajes_necesarios(3, 0, PLAT) == 2


def test_viajes_manda_el_peso_si_exige_mas():
    assert viajes_necesarios(2, 70, PLAT) == 3  # 1 por TEU, 3 por peso


def test_viajes_tipo_sin_capacidad_teu_no_sirve():
    assert viajes_necesarios(1, 0, CAMA) is None


def test_tipos_validos_segun_carga():
    todos = [PLAT, SENC, REFRI, CAMA]
    assert {t.tipo_vehiculo_id for t in tipos_validos(_solicitud(n_teu=2), todos)} == {"PLAT", "SENC"}
    assert [t.tipo_vehiculo_id for t in tipos_validos(_solicitud(n_teu=2, tipo_carga="refrigerado"), todos)] == ["REFRI"]
    assert [t.tipo_vehiculo_id for t in tipos_validos(_solicitud(toneladas=40, tipo_carga="sobredimensionado"), todos)] == ["CAMA"]
    assert [t.tipo_vehiculo_id for t in tipos_validos(_solicitud(n_teu=2, tipo_vehiculo_id="SENC"), todos)] == ["SENC"]


def test_costo_elige_vehiculo_mas_economico():
    s = _solicitud(n_teu=3)
    opciones = opciones_vehiculo(s, [PLAT, SENC], [_tarifa("PLAT", 4_000_000), _tarifa("SENC", 2_500_000)],
                                 {"PLAT": 5, "SENC": 5})
    por_tipo = {o.tipo_vehiculo_id: o for o in opciones}
    assert (por_tipo["PLAT"].viajes, por_tipo["PLAT"].costo) == (2, 8_000_000)
    assert (por_tipo["SENC"].viajes, por_tipo["SENC"].costo) == (3, 7_500_000)
    assert opcion_mas_economica(opciones).tipo_vehiculo_id == "SENC"


def test_sin_tarifa_no_es_opcion():
    assert opciones_vehiculo(_solicitud(n_teu=1), [PLAT], [], {"PLAT": 3}) == []


# --- Profit ----------------------------------------------------------------

def test_profit_y_margen():
    p = calcular_profit(12_000_000, 9_800_000, 0)
    assert p == 2_200_000
    assert margen_pct(p, 12_000_000) == pytest.approx(18.33, abs=0.01)


def test_profit_negativo_no_se_oculta():
    p = calcular_profit(9_000_000, 9_800_000, 500_000)
    assert p == -1_300_000 and margen_pct(p, 9_000_000) < 0


def test_margen_sin_presupuesto():
    assert margen_pct(-5, 0) is None
