"""Registro de solicitudes, evaluaciones, escenarios y decisiones.

- El número de cada solicitud lo da el almacén: con PostgreSQL es la secuencia de
  `transporte.solicitud`, así los consecutivos no se reinician con el servidor.
- Al decidir, la solicitud se guarda en el almacén (con PostgreSQL, en `transporte.solicitud`).
- Evaluaciones, escenarios, justificación y snapshot viven en memoria: la base no tiene
  dónde guardarlos. TODO(persistencia): cuando el equipo de BD cree esas columnas o tablas.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from backend.datos import AlmacenEnMemoria, AlmacenSolicitudes, SolicitudYaDecidida
from backend.datos.almacen import SolicitudDecidida
from backend.dominio import Solicitud

from .esquemas import Decision, Evaluacion


@dataclass
class SolicitudRegistrada:
    solicitud: Solicitud
    evaluacion: Evaluacion
    escenarios: dict[str, tuple[Solicitud, Evaluacion]] = field(default_factory=dict)
    n_escenarios: int = 0


class Registro:
    def __init__(self, almacen: Optional[AlmacenSolicitudes] = None):
        self.almacen = almacen or AlmacenEnMemoria()
        self._lock = threading.Lock()
        self._n_decisiones = 0
        self._solicitudes: dict[str, SolicitudRegistrada] = {}
        self._decisiones: dict[str, Decision] = {}
        self._decision_de: dict[str, str] = {}      # solicitud_id → decision_id

    def nuevo_solicitud_id(self) -> str:
        return f"REQ-{self.almacen.reservar_numero():04d}"

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

    def decision_de(self, solicitud_id: str) -> Optional[Decision]:
        decision_id = self._decision_de.get(solicitud_id)
        return None if decision_id is None else self._decisiones[decision_id]

    def registrar_decision(self, crear: Callable[[str], Decision], fila: SolicitudDecidida) -> Decision:
        """Guarda la solicitud en el almacén y, si sale bien, la decisión en memoria.

        `crear` recibe el `decision_id` y arma la decisión. Lanza `SolicitudYaDecidida` si la
        solicitud ya tiene decisión, o `ErrorDatosNoDisponibles` si la base no responde (en ese
        caso no queda nada registrado).
        """
        with self._lock:
            solicitud_id = f"REQ-{fila.numero:04d}"
            previa = self._decision_de.get(solicitud_id)
            if previa is not None:
                raise SolicitudYaDecidida(f"La solicitud {solicitud_id} ya tiene la decisión {previa}")
            self.almacen.registrar(fila)
            self._n_decisiones += 1
            decision = crear(f"DEC-{self._n_decisiones:04d}")
            self._decisiones[decision.decision_id] = decision
            self._decision_de[solicitud_id] = decision.decision_id
            return decision

    def decision(self, decision_id: str) -> Optional[Decision]:
        return self._decisiones.get(decision_id)
