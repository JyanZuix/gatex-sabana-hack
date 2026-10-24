# Corrección CORS — para el equipo que ejecuta el backend

El backend está ejecutándose en el computador de un compañero. Esta entrega NO se instala en Netlify. No se accedió ni se modificó ese computador, su servidor o su base de datos.

## Qué corrige

El código revisado ya usaba CORSMiddleware, con `CORS_ORIGENES=*` como valor predeterminado. Por ello no se puede afirmar que falte habilitar CORS en todas las respuestas.

Se corrigió la ubicación del middleware: ahora envuelve toda la aplicación publicada, incluidas las respuestas 500 generadas por errores internos. Un error 500 sin cabeceras CORS puede mostrarse al usuario como un bloqueo CORS en vez del error real del backend. El cambio sigue la recomendación oficial de Starlette: https://starlette.dev/middleware/#corsmiddleware-global-enforcement

También se validan los orígenes configurados y se normalizan las barras finales y puertos predeterminados. `https://sitio.netlify.app/` se convierte en el origen correcto `https://sitio.netlify.app`. Una ruta como `/index.html` debe retirarse de la variable; una configuración inválida se informa al iniciar, en vez de ignorarse silenciosamente.

No se añadieron credenciales, cookies, proxys públicos ni `mode: no-cors`. Se conserva la política existente de métodos y cabeceras, y el valor predeterminado `*`; no se modifica una configuración activa sin que el operador la revise.

## Aplicación en el computador del compañero

Descomprimir esta carpeta y revisar `CAMBIOS.patch`.

Desde PowerShell, ejecutar con la ruta REAL del repositorio del compañero:

```powershell
.\Aplicar.ps1 -Proyecto 'C:\ruta\real\gatex-sabana-hack'
```

El script verifica que `app.py` coincida exactamente con la versión revisada, hace copia de seguridad y copia únicamente:

- `backend/api/app.py`
- `backend/api/cors.py` (nuevo)

Si el archivo cambió o ya existe cors.py, el script se detiene sin reemplazar archivos. En ese caso, integrar manualmente los cambios de `CAMBIOS.patch` sobre la versión nueva y añadir cors.py. No sustituir el código nuevo de los compañeros por una versión antigua.

En la terminal que ejecutará el backend, si desean una lista explícita de orígenes:

```powershell
$env:CORS_ORIGENES='https://shimmering-mousse-135327.netlify.app'
```

Debe ser el dominio donde está PUBLICADO el frontend, no `app.netlify.com`, no la dirección del túnel del backend y no una dirección con `/index.html`. Si publicaron en otro dominio, usar ese. Varios dominios se separan por comas. No mezclar `*` y dominios.

Detener y reiniciar el proceso del backend con su entorno Python, credenciales y comando habituales. El comando del proyecto sirve la aplicación `backend.api.app:app`; conservar esa entrada para que se use la envoltura externa de CORS. No usar `crear_app --factory` para esta entrega. No hace falta reiniciar el túnel si permanece conectado al mismo puerto.

Si el backend corre bajo WSL/Linux, configurar CORS_ORIGENES en la terminal o servicio de Linux y aplicar los dos archivos allí: una variable definida en PowerShell no configura automáticamente un proceso Linux ya existente.

## Comprobar después del reinicio

En la carpeta de esta entrega:

```powershell
.\Comprobar-CORS.ps1
```

Usa la dirección del túnel que el usuario confirmó y el último dominio conocido de Netlify. Si cambiaron:

```powershell
.\Comprobar-CORS.ps1 -Api 'https://tunel-real.trycloudflare.com' -Origen 'https://sitio-real.netlify.app'
```

Hace solo GET /salud y OPTIONS /solicitudes/evaluar. No envía POST ni guarda datos. Deben verse respuestas correctas con `CORSValido: True`; el preflight debe permitir POST y content-type. Esto comprueba las cabeceras, pero aún hay que probar el fetch real desde el navegador.

Si el túnel devuelve un error de Cloudflare, de conexión o DNS, CORS de FastAPI no puede añadir cabeceras a una respuesta que no produjo el backend. Verificar en el equipo del compañero primero `http://localhost:8000/salud` y después la URL pública del túnel. Una respuesta 500/503 legible requiere corregir su causa en el backend; habilitar CORS no repara la base de datos ni el túnel.

## Qué se comprobó aquí

- Pasaron cinco pruebas de configuración: orígenes Netlify, barras/puertos, lista de orígenes, rechazo de valores inválidos, conservación del asterisco y presencia de la envoltura global.
- Pasó la validación de sintaxis Python y se comparó la lógica de `crear_app`: las rutas y reglas de negocio siguen idénticas salvo retirar la instalación interna de CORS.
- Se incluyen cuatro pruebas de HTTP/preflight/errores/origen rechazado con FastAPI TestClient, pero NO pudieron ejecutarse en esta sesión: faltan FastAPI y httpx y no se pudieron instalar. No se presentan como aprobadas.
- No se probó el servidor real: /salud del túnel devolvió «Host desconocido» desde esta sesión. El usuario confirma que es la URL correcta; se conserva. No se ha demostrado que ese problema sea el que ven los demás equipos.

Para ejecutar todas las pruebas en el entorno Python del backend (donde ya están sus dependencias):

```powershell
python .\tests\test_cors.py
```

El test usa una aplicación de prueba, no la base de datos real. Debe ejecutar nueve pruebas sin omisiones. Después comprobar desde la página publicada y las Quest. Si sigue fallando, guardar el error de consola, la URL de la petición y el resultado de Comprobar-CORS.ps1.

Esta es una corrección preparada para aplicar y verificar en el backend del compañero. No se afirma que el servidor remoto ya esté corregido.
