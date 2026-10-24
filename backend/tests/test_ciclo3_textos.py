"""Ciclo 3: textos llanos de tiempo, capacidad, desempeño, confianza, historial y fortalezas."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.api import textos as t
from backend.api.app import crear_app
from backend.api.registro import Registro
from backend.calculos.confianza import Confianza
from backend.calculos.costos import OpcionVehiculo
from backend.calculos.desempeno import Desempeno
from backend.dominio import Capacidad, ServicioHistorico
from backend.simulacion import ReferenciaMercado, ResumenOpcion, explicar

HOY = date(2026, 10, 28)
OPCION = OpcionVehiculo(tipo_vehiculo_id="tractomula", nombre="Tractomula", viajes=2, unidades_disponibles=5,
                        precio_viaje=4_000_000, tiempo_prometido_h=26, reparto=(2, 2))


def test_resumen_de_tiempo_sin_percentiles():
    r = t.resumen_tiempo(26.2, 40.0, 33, 0.716)
    assert r == ("Normalmente llega en 26,2 h; en un día malo, hasta 40 h. "
                 "Plazo: 33 h → llega a tiempo en el 72 % de los casos simulados.")
    assert "P50" not in r and "P90" not in r


def test_capacidad_con_y_sin_dato():
    con = t.texto_capacidad(OPCION, Capacidad(proveedor_id="P", fecha=HOY, servicios_disponibles=3), HOY)
    assert con == "Necesita 2 vehículos (Tractomula) y tiene 5 libres esta semana · acepta 3 servicios más el 28-oct"
    sin = t.texto_capacidad(OPCION, None, HOY)
    assert "sin dato" in sin and "no se descartó" in sin


def test_desempeno_y_confianza_en_palabras(cfg):
    d = t.texto_desempeno(Desempeno(valor=72.7, puntualidad=0.85, magnitud_retraso=0.08))
    assert d.startswith("73/100: entrega a tiempo el 85 % de sus servicios y su retraso medio es del 8 %")
    c = Confianza(valor=62.6, nivel="Media", consistencia=0.8, cumplimiento_cliente=0.9, evidencia=0.7,
                  calidad=0.8, sigma_ajustada=0.1, n_efectivo=30, E=0.75)
    assert t.texto_confianza(c, 42, 6, cfg) == ("Media (63/100): se basa en 42 servicios (6 con este cliente); "
                                                 "sus tiempos son estables; con este cliente cumple cerca del 90 %.")
    assert "nunca ha trabajado con este cliente" in t.texto_confianza(c, 42, 0, cfg)
    assert "cliente" not in t.texto_confianza(c, 42, None, cfg)  # la ficha no tiene cliente de referencia


def test_explicacion_sin_jerga(cfg):
    ops = [ResumenOpcion("A", 9_800_000, 0.87, 89.4, 66.3, 6), ResumenOpcion("B", 9_200_000, 0.70, 82.0, 50.0, 0)]
    textos = [x.texto for x in explicar(ops, ReferenciaMercado(0.85, 86.25, 60.0), cfg).values()]
    for texto in textos:
        assert "referencia" not in texto and "efectivos" not in texto
    assert "Ha hecho 6 servicios para este cliente (los otros candidatos, 0 en promedio)" in textos[0]
    assert "Nunca ha trabajado con este cliente" in textos[1]


def _servicio(i, ruta="R1", tipo="tractomula", carga="general", a_tiempo=True):
    return ServicioHistorico(servicio_id=f"S{i}", proveedor_id="P", cliente_id="C", ruta_id=ruta,
                             tipo_vehiculo_id=tipo, fecha_entrega=HOY - timedelta(days=i), tiempo_prometido_h=20,
                             tiempo_real_h=22, a_tiempo=a_tiempo, tipo_carga=carga)


def test_fortalezas_y_debilidades_por_carga_con_su_dato(cfg):
    # 10 en carga general (todos a tiempo) y 10 refrigerados (3 a tiempo): promedio 65 %
    propios = [_servicio(i) for i in range(10)]
    propios += [_servicio(10 + i, tipo="refrigerado", carga="refrigerado", a_tiempo=i < 3) for i in range(10)]
    fuertes, flojas = t.fortalezas_y_debilidades(propios, HOY, cfg, {"R1": "Buenaventura → Bogotá"},
                                                 {"tractomula": "Tractomula", "refrigerado": "Refrigerado"})
    textos_f, textos_d = [x.texto for x in fuertes], [x.texto for x in flojas]
    assert "Puntualidad de 100 % en carga general (su promedio: 65 %; 10 servicios)" in textos_f
    assert "Puntualidad de 30 % en carga refrigerada (su promedio: 65 %; 10 servicios)" in textos_d
    # Para una solicitud refrigerada, la debilidad en refrigerada va primero
    assert t.para_tarjeta(flojas, {("carga", "refrigerado")}, 1) == [
        "Puntualidad de 30 % en carga refrigerada (su promedio: 65 %; 10 servicios)"]


def test_segmento_con_pocos_servicios_no_opina(cfg):
    propios = [_servicio(i, ruta="R1") for i in range(10)] + [_servicio(20, ruta="R2", a_tiempo=False)]
    fuertes, flojas = t.fortalezas_y_debilidades(propios, HOY, cfg, {}, {})
    assert all("R2" not in x.texto for x in fuertes + flojas)


@pytest.fixture
def cliente(repo, cfg):
    return TestClient(crear_app(repo=repo, cfg=cfg, registro=Registro()))


def test_tarjeta_trae_capacidad_historial_y_textos(cliente):
    j = cliente.post("/solicitudes/evaluar", json=dict(
        cliente_id="CLI-0001", origen_id="BUN", destino_id="BOG", fecha_servicio="2026-10-28", plazo_h=40,
        n_contenedores=4, peso_kg=10_000, presupuesto_cop=15_000_000)).json()
    for c in j["candidatos"]:
        cap = c["capacidad"]
        assert cap["vehiculos_necesarios"] == c["vehiculos"]["cantidad"] <= cap["vehiculos_libres"]
        assert cap["texto"].startswith(f"Necesita {cap['vehiculos_necesarios']} vehículo")
        assert c["historial"]["servicios"] >= c["historial"]["servicios_con_cliente"] >= 0
        assert c["tiempo_h"]["resumen"].startswith("Normalmente llega en")
        assert c["desempeno"]["texto"] and c["confianza"]["texto"].startswith(c["confianza"]["nivel"])
        assert all("efectivo" not in r for r in c["riesgos"])
        assert "referencia" not in c["explicacion"]
