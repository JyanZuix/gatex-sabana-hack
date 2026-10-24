# Registro de decisiones

Una decisión por fila. Si una decisión cambia, se agrega una fila nueva; no se borra la anterior.

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-23 | Backend en Python 3.10 + FastAPI + pandas/numpy | Simple, rápido de montar y adecuado para cálculo numérico y Monte Carlo |
| 2026-10-23 | Web de respaldo en HTML y JS plano con Chart.js, sin paso de build | Igual que el prototipo VR; nada que compilar en la demo |
| 2026-10-23 | Base de datos: PostgreSQL | La construye el subequipo de BD. El esquema real se lee cuando esté disponible |
| 2026-10-23 | Gafas: Meta Quest 3, con Three.js y WebXR | Es el visor disponible; el prototipo ya usa WebXR |
| 2026-10-23 | `Profit = presupuesto_disponible − costo_proveedor − costo_esperado_retraso` | No hay tarifa de COSCO al cliente. El "ingreso" es el dinero disponible antes del envío; lo que sobra es el profit. **Confirmado** por el equipo el 2026-10-23 |
| 2026-10-23 | `solicitud_id` consecutivo generado por el backend y `cliente_id` propio | Registrar correctamente los pedidos de cada cliente, sin depender del frontend |
| 2026-10-23 | `SIN_CAPACIDAD` y `VEHICULOS_INSUFICIENTES` validan capacidad por TEU y por peso | La capacidad define cuántos vehículos reservar y si el proveedor puede atender la solicitud |
| 2026-10-23 | Viajes en varias tandas: se descartan (configurable) | Valor por defecto del documento de cálculos |
| 2026-10-23 | Esquema de BD, cobertura, tipos de vehículo y de carga: pendientes hasta leer la BD real | Dependen del subequipo de BD |
| 2026-10-23 | Trabajo solo local; cada `git push` requiere permiso explícito | Decisión del equipo hasta tener la primera versión del backend |
| 2026-10-23 | `penal_hora_cop` vale 0 por defecto y el funcionario lo ajusta | Valor por defecto del documento de cálculos; no hay referencia de negocio todavía |
| 2026-10-23 | El backend accede a datos mediante una interfaz de repositorio, con adaptador simulado y adaptador PostgreSQL | Permite avanzar sin la BD del subequipo y conectarla después sin tocar filtro, cálculos ni simulación |
| 2026-10-23 | Datos sintéticos en `backend/datos_sinteticos/`, no en `demo/` | El trabajo de este subequipo es solo backend; `demo/` aún no se crea |
| 2026-10-23 | Carga general solo usa vehículos sin carga especial; carga especial solo vehículos de ese tipo | Regla de compatibilidad de la v1; ajustable cuando se conozcan los tipos reales |
| 2026-10-23 | `SIN_CAPACIDAD` exige `servicios_disponibles ≥ 1` en la fecha; si falta el dato no se descarta, se avisa | No inventar datos; la unidad real de capacidad se confirma con el esquema de BD |
| 2026-10-23 | Si el mercado no tiene historial en la ruta, la simulación usa Δ ~ Normal(0, σ0) y lo avisa | La especificación no cubre el caso. **TODO: confirmar con el equipo** |
