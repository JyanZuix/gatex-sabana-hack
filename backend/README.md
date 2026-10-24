# Backend

Filtro, cálculos, simulación y API de la Sala de Simulación de Proveedores. Especificación: `../docs/calculos_simulacion.md`. Contrato de la API: `../README.md`, sección 5. Avance: `../PLAN.md`.

## Puesta en marcha
Requiere **Python 3.12.7**. Desde la raíz del repositorio:

    uv venv .venv --python 3.12.7       # o: python3.12 -m venv .venv
    uv pip install --python .venv/bin/python -r backend/requirements.txt
    cp .env.example .env               # y completar DATABASE_URL (nunca en .env.example)
    backend/pruebas.sh                 # corre todas las pruebas
    .venv/bin/uvicorn backend.api.app:app --reload    # API en http://localhost:8000/docs

`pruebas.sh` quita `PYTHONPATH` porque ROS, si está instalado, inyecta plugins de pytest que fallan.
Las pruebas no se conectan a la base: usan los datos sintéticos y filas de ejemplo.

## Datos
- `REPOSITORIO=postgres` con `DATABASE_URL` (Supabase → Connect → Session pooler): lee el esquema `transporte` (`datos/postgres.py`). Las tablas se leen una vez, en la primera consulta; para ver cambios de la base hay que reiniciar el servidor. Si la base no responde, la API devuelve 503.
- Escritura (`datos/almacen.py`): al evaluar se reserva el número de la secuencia de `transporte.solicitud`; al decidir se inserta la solicitud; al cerrar el viaje (`POST /solicitudes/{id}/cierre`) se inserta su fila en `servicio` y el repositorio se recarga, así D y C usan el viaje nuevo sin reiniciar. Con `REPOSITORIO=simulado` todo queda en memoria.
- Caché: lo leído de PostgreSQL se vuelve a leer cada `datos.refresco_cache_s` segundos (300) o tras cada escritura. Si un refresco falla se siguen usando los datos anteriores.
- Prueba contra Supabase sin dejar datos (transacción con ROLLBACK): `PRUEBAS_BD=1 backend/pruebas.sh -k supabase`.
- **La contraseña va solo en `.env`.** `tests/test_sin_credenciales.py` falla si aparece en cualquier otro archivo.
- `REPOSITORIO=simulado` (por defecto si no hay `.env`): lee `datos_sinteticos/*.json`. Para regenerarlos: `.venv/bin/python -m backend.datos_sinteticos.generar`.

## Módulos
| Carpeta | Qué hace |
|---|---|
| `config/` | `parametros.yaml` y su cargador tipado. Ningún parámetro vive en el código |
| `dominio.py` | Modelos compartidos (solicitud, proveedor, tarifa, servicio…) |
| `datos/` | Interfaz `Repositorio` y adaptadores (simulado y PostgreSQL) |
| `filtro/` | 8 reglas de descarte; agregar una es decorar una función con `@regla` |
| `calculos/` | Recencia, Desempeño, Confianza, vehículos y reparto de contenedores, costo y profit |
| `simulacion/` | Monte Carlo, escenarios "¿y si…?" (plazo y penalidad) y explicaciones |
| `api/` | Endpoints FastAPI; `api/ejemplos/` guarda respuestas reales para frontend y gafas |
