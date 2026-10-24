"""Elige el adaptador de datos según la variable de entorno REPOSITORIO."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Optional

from dotenv import load_dotenv

from .almacen import AlmacenEnMemoria, AlmacenPostgres, AlmacenSolicitudes
from .repositorio import Repositorio

# `.env` en la raíz del repositorio (no se sube: está en .gitignore). Ver `.env.example`.
ARCHIVO_ENV = Path(__file__).resolve().parents[2] / ".env"


def _entorno(entorno: Optional[Mapping[str, str]]) -> Mapping[str, str]:
    if entorno is None:
        load_dotenv(ARCHIVO_ENV)  # no reemplaza variables ya definidas en la terminal
        return os.environ
    return entorno


def crear_almacen(entorno: Optional[Mapping[str, str]] = None) -> AlmacenSolicitudes:
    """Dónde se guardan las solicitudes decididas: la base con `REPOSITORIO=postgres`, si no en memoria."""
    entorno = _entorno(entorno)
    if entorno.get("REPOSITORIO", "simulado").strip().lower() == "postgres":
        return AlmacenPostgres(entorno.get("DATABASE_URL", ""))
    return AlmacenEnMemoria()


def crear_repositorio(entorno: Optional[Mapping[str, str]] = None) -> Repositorio:
    """`REPOSITORIO=simulado` (por defecto) o `REPOSITORIO=postgres` con `DATABASE_URL`.

    Sin `entorno`, lee las variables del sistema y completa las que falten con `.env`.
    """
    entorno = _entorno(entorno)
    tipo = entorno.get("REPOSITORIO", "simulado").strip().lower()
    if tipo == "simulado":
        from .simulado import CARPETA_POR_DEFECTO, RepositorioSimulado
        return RepositorioSimulado(entorno.get("DATOS_SIMULADOS", CARPETA_POR_DEFECTO))
    if tipo == "postgres":
        from .postgres import RepositorioPostgres
        return RepositorioPostgres(entorno.get("DATABASE_URL", ""))
    raise ValueError(f"REPOSITORIO desconocido: '{tipo}' (use 'simulado' o 'postgres')")
