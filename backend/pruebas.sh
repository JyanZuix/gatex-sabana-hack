#!/usr/bin/env bash
# Corre las pruebas del backend. Se quita PYTHONPATH porque ROS (si está instalado)
# inyecta plugins de pytest que fallan en el entorno virtual.
set -euo pipefail
cd "$(dirname "$0")/.."
env -u PYTHONPATH .venv/bin/pytest backend "$@"
