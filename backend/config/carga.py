"""Lectura y validación de `parametros.yaml`.

Todos los campos son obligatorios: si falta uno, la carga falla con un
mensaje que nombra el parámetro. Así ningún módulo usa un valor implícito.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, model_validator

RUTA_POR_DEFECTO = Path(__file__).with_name("parametros.yaml")


class ErrorConfiguracion(ValueError):
    """La configuración no existe o le falta o sobra algún parámetro."""


def _fraccion(valor):
    """Acepta "2/3" como texto para pesos que no tienen decimal exacto."""
    if isinstance(valor, str) and "/" in valor:
        try:
            return float(Fraction(valor.replace(" ", "")))
        except (ValueError, ZeroDivisionError):
            raise ValueError(f"fracción no válida: '{valor}'") from None
    return valor


Peso = Annotated[float, BeforeValidator(_fraccion), Field(ge=0, le=1)]


class _Seccion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Recencia(_Seccion):
    vida_media_dias: float = Field(gt=0)


class PriorPorDefecto(_Seccion):
    P0: float = Field(ge=0, le=1)
    R0: float = Field(ge=0, le=1)
    sigma0: float = Field(ge=0)


class Prior(_Seccion):
    m: float = Field(gt=0)
    min_servicios_segmento: int = Field(ge=1)
    por_defecto: PriorPorDefecto


class Desempeno(_Seccion):
    peso_puntualidad: Peso
    peso_magnitud_retraso: Peso


class Niveles(_Seccion):
    alta: float
    media: float


class Confianza(_Seccion):
    peso_consistencia: Peso
    peso_cumplimiento_cliente: Peso
    sigma_max: float = Field(gt=0)
    k_evidencia: float = Field(gt=0)
    alfa_cliente: float = Field(ge=0)
    piso_evidencia: float = Field(ge=0, le=1)
    niveles: Niveles


class Simulacion(_Seccion):
    n: int = Field(ge=1)
    semilla: int
    min_servicios_ruta: float = Field(ge=0)
    percentil_tipico: float = Field(ge=0, le=100)
    percentil_mal_caso: float = Field(ge=0, le=100)
    percentil_profit_mal_caso: float = Field(ge=0, le=100)
    percentiles_abanico: tuple[float, ...]


class Escenario(_Seccion):
    penal_hora_cop: float = Field(ge=0)


class Vehiculos(_Seccion):
    permitir_tandas: bool


class Filtro(_Seccion):
    servicios_requeridos: int = Field(ge=0)


class Explicacion(_Seccion):
    max_factores: int = Field(ge=1)
    umbral_impacto: float = Field(ge=0)


class Ficha(_Seccion):
    min_servicios_segmento: int = Field(ge=1)
    umbral_diferencia: float = Field(gt=0, le=1)


class Config(_Seccion):
    recencia: Recencia
    prior: Prior
    desempeno: Desempeno
    confianza: Confianza
    simulacion: Simulacion
    escenario: Escenario
    vehiculos: Vehiculos
    filtro: Filtro
    explicacion: Explicacion
    ficha: Ficha

    @model_validator(mode="after")
    def _pesos_suman_uno(self) -> "Config":
        d = self.desempeno.peso_puntualidad + self.desempeno.peso_magnitud_retraso
        q = self.confianza.peso_consistencia + self.confianza.peso_cumplimiento_cliente
        if abs(d - 1) > 1e-9:
            raise ValueError(f"Los pesos de desempeño deben sumar 1 (suman {d})")
        if abs(q - 1) > 1e-9:
            raise ValueError(f"Los pesos de confianza deben sumar 1 (suman {q})")
        return self


def _describir(error: ValidationError) -> str:
    partes = []
    for e in error.errors():
        nombre = ".".join(str(x) for x in e["loc"]) or "(raíz)"
        if e["type"] == "missing":
            partes.append(f"falta el parámetro '{nombre}'")
        elif e["type"] == "extra_forbidden":
            partes.append(f"parámetro desconocido '{nombre}'")
        else:
            partes.append(f"'{nombre}': {e['msg']}")
    return "; ".join(partes)


def config_desde_dict(datos: dict) -> Config:
    try:
        return Config.model_validate(datos)
    except ValidationError as e:
        raise ErrorConfiguracion(f"Configuración inválida: {_describir(e)}") from None


def cargar_config(ruta: str | Path | None = None) -> Config:
    """Lee `parametros.yaml` (o la ruta indicada) y devuelve la configuración validada."""
    if ruta is None:
        return _cargar_por_defecto()
    return _leer(Path(ruta))


@lru_cache(maxsize=1)
def _cargar_por_defecto() -> Config:
    return _leer(RUTA_POR_DEFECTO)


def _leer(ruta: Path) -> Config:
    if not ruta.exists():
        raise ErrorConfiguracion(f"No existe el archivo de configuración {ruta}")
    with ruta.open(encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}
    return config_desde_dict(datos)
