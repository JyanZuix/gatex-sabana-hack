from datetime import date

import pytest

from backend.config import cargar_config
from backend.datos import RepositorioSimulado
from backend.dominio import Solicitud


@pytest.fixture(scope="session")
def cfg():
    return cargar_config()


@pytest.fixture(scope="session")
def repo():
    return RepositorioSimulado()


@pytest.fixture
def solicitud_base():
    """Buenaventura → Bogotá, 4 TEU, plazo 40 h (datos sintéticos)."""
    return Solicitud(cliente_id="CLI-0001", origen_id="BUN", destino_id="BOG",
                     fecha_servicio=date(2026, 10, 28), plazo_h=40, n_teu=4,
                     presupuesto_cop=15_000_000)
