"""Simulación Monte Carlo por candidato y escenarios "¿y si…?" (docs/calculos_simulacion.md, sección 6)."""
from .escenarios import Escenario, aplicar_escenario
from .explicacion import Explicacion, Factor, ReferenciaMercado, ResumenOpcion, explicar, riesgos
from .montecarlo import EntradaSimulacion, ResultadoSimulacion, preparar_entrada, simular

__all__ = [
    "EntradaSimulacion", "ResultadoSimulacion", "preparar_entrada", "simular",
    "Escenario", "aplicar_escenario",
    "Explicacion", "Factor", "ReferenciaMercado", "ResumenOpcion", "explicar", "riesgos",
]
