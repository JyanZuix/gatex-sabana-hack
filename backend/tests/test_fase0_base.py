"""Fase 0: configuración, modelos de dominio y capa de datos."""
import json
import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from backend.config import ErrorConfiguracion, cargar_config
from backend.config.carga import RUTA_POR_DEFECTO, config_desde_dict
from backend.datos import ErrorDatos, RepositorioSimulado, crear_repositorio
from backend.datos.postgres import RepositorioPostgres
from backend.datos.simulado import CARPETA_POR_DEFECTO
from backend.dominio import Solicitud, Tarifa


def _yaml():
    return yaml.safe_load(RUTA_POR_DEFECTO.read_text(encoding="utf-8"))


# --- Configuración ---------------------------------------------------------

def test_config_contiene_parametros_del_documento(cfg):
    assert cfg.recencia.vida_media_dias == 365
    assert cfg.prior.m == 10
    assert cfg.confianza.k_evidencia == 10
    assert cfg.confianza.alfa_cliente == 2
    assert (cfg.desempeno.peso_puntualidad, cfg.desempeno.peso_magnitud_retraso) == (0.75, 0.25)
    assert cfg.confianza.peso_consistencia == pytest.approx(2 / 3)
    assert cfg.confianza.peso_cumplimiento_cliente == pytest.approx(1 / 3)
    assert cfg.confianza.piso_evidencia == 0.4
    assert cfg.confianza.sigma_max == 0.5
    assert cfg.simulacion.n == 2000
    d = cfg.prior.por_defecto
    assert (d.P0, d.R0, d.sigma0) == (0.85, 0.10, 0.20)
    assert (cfg.confianza.niveles.alta, cfg.confianza.niveles.media) == (75, 55)
    assert cfg.vehiculos.permitir_tandas is False
    assert not hasattr(cfg, "escenario")  # el costo por retraso se eliminó


def test_config_falta_parametro_lo_nombra():
    datos = _yaml()
    del datos["confianza"]["alfa_cliente"]
    with pytest.raises(ErrorConfiguracion, match="confianza.alfa_cliente"):
        config_desde_dict(datos)


def test_config_parametro_desconocido():
    datos = _yaml()
    datos["simulacion"]["iteraciones"] = 5
    with pytest.raises(ErrorConfiguracion, match="simulacion.iteraciones"):
        config_desde_dict(datos)


def test_config_pesos_deben_sumar_uno():
    datos = _yaml()
    datos["desempeno"]["peso_puntualidad"] = 0.8
    with pytest.raises(ErrorConfiguracion, match="sumar 1"):
        config_desde_dict(datos)


def test_config_pesos_del_puntaje_deben_sumar_uno():
    datos = _yaml()
    p = datos["puntaje"]
    assert (p["peso_profit"], p["peso_a_tiempo"], p["peso_desempeno"], p["peso_confianza"], p["top_n"]) == (
        0.40, 0.30, 0.15, 0.15, 4)
    p["peso_profit"] = 0.5
    with pytest.raises(ErrorConfiguracion, match="puntaje deben sumar 1"):
        config_desde_dict(datos)


def test_config_acepta_fracciones_y_rechaza_las_invalidas():
    datos = _yaml()
    datos["confianza"]["peso_consistencia"] = "1/2"
    datos["confianza"]["peso_cumplimiento_cliente"] = "1/2"
    assert config_desde_dict(datos).confianza.peso_consistencia == 0.5
    datos["confianza"]["peso_consistencia"] = "1/0"
    with pytest.raises(ErrorConfiguracion, match="peso_consistencia"):
        config_desde_dict(datos)


def test_config_sin_parametros_de_incidentes():
    datos = _yaml()
    assert "severidad" not in datos and "I0" not in datos["prior"]["por_defecto"]
    datos["confianza"]["peso_incidentes"] = 0.4
    with pytest.raises(ErrorConfiguracion, match="peso_incidentes"):
        config_desde_dict(datos)


def test_config_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorConfiguracion, match="No existe"):
        cargar_config(tmp_path / "nada.yaml")


# --- Modelos de dominio ----------------------------------------------------

def test_solicitud_desde_diccionario():
    s = Solicitud.model_validate({"cliente_id": "CLI-0001", "origen_id": "BUN", "destino_id": "BOG",
                                  "fecha_servicio": "2026-10-28", "plazo_h": 40, "n_contenedores": 3,
                                  "peso_kg": 12_000, "presupuesto_cop": 10_000_000})
    assert s.fecha_servicio == date(2026, 10, 28) and s.solicitud_id is None
    assert (s.n_contenedores, s.peso_kg) == (3, 12_000)


@pytest.mark.parametrize("campo", ["plazo_h", "n_contenedores", "peso_kg", "presupuesto_cop"])
def test_solicitud_rechaza_negativos(campo):
    datos = {"cliente_id": "C", "origen_id": "A", "destino_id": "B", "fecha_servicio": "2026-10-28",
             "plazo_h": 40, "n_contenedores": 1, "peso_kg": 1, "presupuesto_cop": 1}
    datos[campo] = -1
    with pytest.raises(ValidationError):
        Solicitud.model_validate(datos)


@pytest.mark.parametrize("cambios,campo", [({"n_contenedores": 0}, "n_contenedores"), ({"peso_kg": 0}, "peso_kg"),
                                            ({"n_contenedores": None}, "n_contenedores"), ({"peso_kg": None}, "peso_kg")])
def test_solicitud_sin_contenedores_o_sin_peso_es_invalida(cambios, campo):
    """No existe carga sin contenedores: n_contenedores ≥ 1 y peso_kg > 0 son obligatorios."""
    datos = dict(cliente_id="C", origen_id="A", destino_id="B", fecha_servicio=date(2026, 1, 1),
                 plazo_h=10, n_contenedores=1, peso_kg=1_000, presupuesto_cop=1)
    datos.update(cambios)
    datos = {k: v for k, v in datos.items() if v is not None}
    with pytest.raises(ValidationError, match=campo):
        Solicitud(**datos)


def test_solicitud_ya_no_acepta_teu_ni_toneladas():
    with pytest.raises(ValidationError, match="n_teu"):
        Solicitud(cliente_id="C", origen_id="A", destino_id="B", fecha_servicio=date(2026, 1, 1),
                  plazo_h=10, n_contenedores=1, peso_kg=1_000, n_teu=1, presupuesto_cop=1)


def test_tarifa_rechaza_precio_negativo_y_valida_vigencia():
    with pytest.raises(ValidationError):
        Tarifa(tarifa_id="T", proveedor_id="P", ruta_id="R", tipo_vehiculo_id="V", precio_viaje=-5,
               tiempo_prometido_h=10, vigente_desde=date(2025, 1, 1))
    t = Tarifa(tarifa_id="T", proveedor_id="P", ruta_id="R", tipo_vehiculo_id="V", precio_viaje=5,
               tiempo_prometido_h=10, vigente_desde=date(2025, 1, 1), vigente_hasta=date(2025, 12, 31))
    assert t.vigente(date(2025, 6, 1)) and not t.vigente(date(2026, 1, 1))


# --- Capa de datos ---------------------------------------------------------

def test_repositorio_simulado_carga_datos(repo):
    assert len(repo.proveedores()) == 10
    assert len(repo.servicios_historicos()) > 200
    assert repo.ruta("BUN", "BOG").distancia_km == 515
    assert repo.ruta("BOG", "BUN").ruta_id != repo.ruta("BUN", "BOG").ruta_id  # rutas dirigidas
    assert repo.ruta("BUN", "MED") is None


def test_repositorio_tarifas_vigentes_respeta_fechas(repo):
    antes = {t.tarifa_id for t in repo.tarifas_vigentes("R-BOG-BUN", date(2026, 3, 1))}
    despues = {t.tarifa_id for t in repo.tarifas_vigentes("R-BOG-BUN", date(2026, 10, 28))}
    vencida = "TAR-PROV-06-R-BOG-BUN-TV-PLAT40-2025"
    assert vencida in antes and vencida not in despues


def test_repositorio_historial_hasta_fecha(repo):
    corte = date(2025, 1, 1)
    assert all(s.fecha_entrega < corte for s in repo.servicios_historicos(hasta=corte))


def test_todos_los_archivos_estan_etiquetados_como_sinteticos():
    for archivo in CARPETA_POR_DEFECTO.glob("*.json"):
        assert json.loads(archivo.read_text(encoding="utf-8"))["sintetico"] is True, archivo.name


def test_repositorio_rechaza_datos_sin_etiqueta(tmp_path):
    carpeta = tmp_path / "datos"
    shutil.copytree(CARPETA_POR_DEFECTO, carpeta)
    archivo = carpeta / "proveedores.json"
    contenido = json.loads(archivo.read_text(encoding="utf-8"))
    del contenido["sintetico"]
    archivo.write_text(json.dumps(contenido), encoding="utf-8")
    with pytest.raises(ErrorDatos, match="sintético"):
        RepositorioSimulado(carpeta)


def test_fabrica_elige_adaptador():
    assert isinstance(crear_repositorio({"REPOSITORIO": "simulado"}), RepositorioSimulado)
    # Crear el adaptador no abre la conexión: la base se lee en la primera consulta.
    pg = crear_repositorio({"REPOSITORIO": "postgres", "DATABASE_URL": "postgresql://x"})
    assert isinstance(pg, RepositorioPostgres)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        crear_repositorio({"REPOSITORIO": "postgres"})
    with pytest.raises(ValueError):
        crear_repositorio({"REPOSITORIO": "mysql"})


def test_fabrica_lee_env_sin_pisar_la_terminal(tmp_path, monkeypatch):
    import os
    from backend.datos import fabrica
    monkeypatch.setattr(os, "environ", dict(os.environ))  # load_dotenv escribe aquí; no afecta otras pruebas
    archivo = tmp_path / ".env"
    archivo.write_text("REPOSITORIO=postgres\nDATABASE_URL=postgresql://desde-env\n", encoding="utf-8")
    monkeypatch.setattr(fabrica, "ARCHIVO_ENV", archivo)
    monkeypatch.delenv("REPOSITORIO", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://desde-terminal")
    repo = crear_repositorio()
    assert isinstance(repo, RepositorioPostgres)
    assert repo.dsn == "postgresql://desde-terminal"
