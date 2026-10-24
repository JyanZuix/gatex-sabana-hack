"""Filtro de requisitos mínimos: Candidatos → Cancelados (README 3.2)."""
from .filtro import RutaNoEncontrada, filtrar
from .modelos import Cancelado, Candidato, CasiElegible, ContextoProveedor, Razon, ResultadoFiltro
from .reglas import REGLAS, regla

__all__ = [
    "filtrar", "RutaNoEncontrada", "REGLAS", "regla",
    "Razon", "Candidato", "Cancelado", "CasiElegible", "ContextoProveedor", "ResultadoFiltro",
]
