# Backend

Filtro, cálculos y simulación de la Sala de Simulación de Proveedores. Especificación: `../docs/calculos_simulacion.md`. Avance: `../PLAN.md`.

## Puesta en marcha
Desde la raíz del repositorio:

    python3 -m virtualenv .venv        # o python3 -m venv .venv si tu Python trae ensurepip
    .venv/bin/pip install -r backend/requirements.txt
    backend/pruebas.sh                 # corre todas las pruebas

`pruebas.sh` quita `PYTHONPATH` porque ROS, si está instalado, inyecta plugins de pytest que fallan.

## Datos
- `REPOSITORIO=simulado` (por defecto): lee `datos_sinteticos/*.json`. Para regenerarlos: `.venv/bin/python -m backend.datos_sinteticos.generar`.
- `REPOSITORIO=postgres` con `DATABASE_URL`: adaptador pendiente del esquema del subequipo de BD (`datos/postgres.py`).

## Módulos
| Carpeta | Qué hace |
|---|---|
| `config/` | `parametros.yaml` y su cargador tipado. Ningún parámetro vive en el código |
| `dominio.py` | Modelos compartidos (solicitud, proveedor, tarifa, servicio…) |
| `datos/` | Interfaz `Repositorio` y adaptadores |
| `filtro/` | 8 reglas de descarte; agregar una es decorar una función con `@regla` |
| `calculos/` | Recencia, Desempeño, Confianza, vehículos, costo y profit |
| `simulacion/` | Monte Carlo, escenarios "¿y si…?" y explicaciones |
| `api/` | Pendiente (Fase 4) |
