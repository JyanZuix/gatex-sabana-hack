"""Registro de solicitudes, evaluaciones, escenarios y decisiones.

TODO(persistencia): hoy vive en memoria y se pierde al reiniciar el servidor
(los consecutivos vuelven a REQ-0001). El siguiente paso es guardarlo en las
tablas `solicitudes`, `evaluaciones` y `decisiones` de la base (README, sección 4).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from backend.dominio import Solicitud

from .esquemas import Decision, Evaluacion


@dataclass
class SolicitudRegistrada:
    solicitud: Solicitud
    evaluacion: Evaluacion
    escenarios: dict[str, tuple[Solicitud, Evaluacion]] = field(default_factory=dict)
    n_escenarios: int = 0


class Registro:
    def __init__(self):
        self._lock = threading.Lock()
        self._n_solicitudes = 0
        self._n_decisiones = 0
        self._solicitudes: dict[str, SolicitudRegistrada] = {}
        self._decisiones: dict[str, Decision] = {}

    def nuevo_solicitud_id(self) -> str:
        with self._lock:
            self._n_solicitudes += 1
            return f"REQ-{self._n_solicitudes:04d}"

    def guardar_solicitud(self, solicitud: Solicitud, evaluacion: Evaluacion) -> None:
        with self._lock:
            self._solicitudes[solicitud.solicitud_id] = SolicitudRegistrada(solicitud, evaluacion)

    def solicitud(self, solicitud_id: str) -> Optional[SolicitudRegistrada]:
        return self._solicitudes.get(solicitud_id)

    def nuevo_escenario_id(self, solicitud_id: str) -> str:
        with self._lock:
            registrada = self._solicitudes[solicitud_id]
            registrada.n_escenarios += 1
            return f"{solicitud_id}-E{registrada.n_escenarios}"

    def guardar_escenario(self, solicitud_id: str, escenario_id: str, solicitud: Solicitud,
                          evaluacion: Evaluacion) -> None:
        with self._lock:
            self._solicitudes[solicitud_id].escenarios[escenario_id] = (solicitud, evaluacion)

    def nuevo_decision_id(self) -> str:
        with self._lock:
            self._n_decisiones += 1
            return f"DEC-{self._n_decisiones:04d}"

    def guardar_decision(self, decision: Decision) -> None:
        with self._lock:
            self._decisiones[decision.decision_id] = decision

    def decision(self, decision_id: str) -> Optional[Decision]:
        return self._decisiones.get(decision_id)
