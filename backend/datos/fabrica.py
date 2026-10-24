"""Elige el adaptador de datos según la variable de entorno REPOSITORIO."""
from __future__ import annotations

import os
from typing import Mapping, Optional

from .repositorio import Repositorio


def crear_repositorio(entorno: Optional[Mapping[str, str]] = None) -> Repositorio:
    """`REPOSITORIO=simulado` (por defecto) o `REPOSITORIO=postgres` con `DATABASE_URL`."""
    entorno = os.environ if entorno is None else entorno
    tipo = entorno.get("REPOSITORIO", "simulado").strip().lower()
    if tipo == "simulado":
        from .simulado import CARPETA_POR_DEFECTO, RepositorioSimulado
        return RepositorioSimulado(entorno.get("DATOS_SIMULADOS", CARPETA_POR_DEFECTO))
    if tipo == "postgres":
        from .postgres import RepositorioPostgres
        return RepositorioPostgres(entorno.get("DATABASE_URL", ""))
    raise ValueError(f"REPOSITORIO desconocido: '{tipo}' (use 'simulado' o 'postgres')")
