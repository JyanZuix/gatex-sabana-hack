"""Peso por recencia (sección 1.2): w = 0.5 ^ (t / H)."""
from __future__ import annotations

import numpy as np


def peso_recencia(antiguedad_dias, vida_media_dias: float):
    """Peso de un servicio según su antigüedad en días. Acepta escalares o arreglos."""
    t = np.maximum(np.asarray(antiguedad_dias, dtype=float), 0.0)
    w = 0.5 ** (t / vida_media_dias)
    return float(w) if w.ndim == 0 else w
