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
from backend.dominio import CondicionVia, Solicitud, Tarifa


def _yaml():
    return yaml.safe_load(RUTA_POR_DEFECTO.read_text(encoding="utf-8"))


# --- Configuración ---------------------------------------------------------

def test_config_contiene_parametros_del_documento(cfg):
    assert cfg.recencia.vida_media_dias == 365
    assert cfg.prior.m == 10
    assert cfg.confianza.k_evidencia == 10
    assert cfg.confianza.alfa_cliente == 2
    assert (cfg.desempeno.peso_puntualidad, cfg.desempeno.peso_magnitud_retraso) == (0.75, 0.25)
    assert (cfg.confianza.peso_consistencia, cfg.confianza.peso_incidentes,
            cfg.confianza.peso_cumplimiento_cliente) == (0.40, 0.40, 0.20)
    assert cfg.confianza.piso_evidencia == 0.4
    assert cfg.confianza.sigma_max == 0.5
    assert (cfg.severidad.leve, cfg.severidad.moderado, cfg.severidad.grave) == (0.3, 0.6, 1.0)
    assert cfg.simulacion.n == 2000
    d = cfg.prior.por_defecto
    assert (d.P0, d.R0, d.sigma0, d.I0) == (0.85, 0.10, 0.20, 0.05)
    assert (cfg.confianza.niveles.alta, cfg.confianza.niveles.media) == (75, 55)
    assert cfg.vehiculos.permitir_tandas is False
    assert cfg.escenario.penal_hora_cop == 0


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


def test_config_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorConfiguracion, match="No existe"):
        cargar_config(tmp_path / "nada.yaml")


# --- Modelos de dominio ----------------------------------------------------

def test_solicitud_desde_diccionario():
    s = Solicitud.model_validate({"cliente_id": "CLI-0001", "origen_id": "BUN", "destino_id": "BOG",
                                  "fecha_servicio": "2026-10-28", "plazo_h": 40, "n_teu": 3,
                                  "presupuesto_cop": 10_000_000})
    assert s.fecha_servicio == date(2026, 10, 28) and s.solicitud_id is None


@pytest.mark.parametrize("campo", ["plazo_h", "n_teu", "toneladas", "presupuesto_cop"])
def test_solicitud_rechaza_negativos(campo):
    datos = {"cliente_id": "C", "origen_id": "A", "destino_id": "B", "fecha_servicio": "2026-10-28",
             "plazo_h": 40, "n_teu": 1, "toneladas": 1, "presupuesto_cop": 1}
    datos[campo] = -1
    with pytest.raises(ValidationError):
        Solicitud.model_validate(datos)


def test_solicitud_sin_carga_es_invalida():
    with pytest.raises(ValidationError, match="n_teu"):
        Solicitud(cliente_id="C", origen_id="A", destino_id="B", fecha_servicio=date(2026, 1, 1),
                  plazo_h=10, presupuesto_cop=1)


def test_tarifa_rechaza_precio_negativo_y_valida_vigencia():
    with pytest.raises(ValidationError):
        Tarifa(tarifa_id="T", proveedor_id="P", ruta_id="R", tipo_vehiculo_id="V", precio_viaje=-5,
               tiempo_prometido_h=10, vigente_desde=date(2025, 1, 1))
    t = Tarifa(tarifa_id="T", proveedor_id="P", ruta_id="R", tipo_vehiculo_id="V", precio_viaje=5,
               tiempo_prometido_h=10, vigente_desde=date(2025, 1, 1), vigente_hasta=date(2025, 12, 31))
    assert t.vigente(date(2025, 6, 1)) and not t.vigente(date(2026, 1, 1))


def test_condicion_via_rango_invalido():
    with pytest.raises(ValidationError):
        CondicionVia(corredor="X", fecha_hora="2026-10-20T08:00:00", p_evento=0.1,
                     demora_min_h=10, demora_max_h=2)


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
    pg = crear_repositorio({"REPOSITORIO": "postgres", "DATABASE_URL": "postgresql://x"})
    assert isinstance(pg, RepositorioPostgres)
    with pytest.raises(NotImplementedError, match="TODO"):
        pg.proveedores()
    with pytest.raises(ValueError):
        crear_repositorio({"REPOSITORIO": "mysql"})
