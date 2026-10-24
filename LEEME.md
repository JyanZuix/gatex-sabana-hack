# Gatex-sim VR — primera versión

## Qué incluye
- Inicio con un botón Entrar a VR; acceso directo a sección 2.
- Entorno 3D gris claro y tablet provisional creada con geometría, no con un modelo de Blender.
- Seis campos editables: origen, destino, tipo de carga, vehículo, peso y fecha límite.
- Teclado virtual: letras, números, espacio, borrar, siguiente campo y listo.
- Mandos: apunta a un campo o tecla y pulsa el gatillo. Ambos mandos tienen rayo de selección.
- Salir de VR desde la tablet o el sistema del visor.
- Lista de solicitudes vacía y análisis pendiente, sin recomendaciones ni datos ficticios.

## Alcance de los datos
Por indicación de no hacer nada todavía al ingresar datos, no hay peticiones al backend, persistencia ni envío de solicitudes. Los datos son un borrador en memoria que se borra al salir de VR o recargar. No hay validación de negocio todavía: todos los campos admiten texto. No se utiliza seguimiento de manos; esta versión está preparada para mandos Touch.

## Archivos
index.html: inicio, estilos y mapa de dependencias.
js/inicio.js: carga con mensaje de error si falla la dependencia remota.
js/main.js: escena, tablet, teclado e interacción WebXR.

No requiere npm ni compilación. Necesita internet para cargar Three.js 0.160.0 desde unpkg.com.

## Copiar a tu proyecto
Haz una copia de seguridad de index.html y js/main.js antes de sustituirlos. Copia index.html y los dos archivos de js/ a tu proyecto. No borres assets/ ni otros archivos existentes. No se ha modificado automáticamente la carpeta de OneDrive.

## Windows
Abre una terminal en esta carpeta y, si tienes Python instalado, ejecuta:

    py -m http.server 8000 --bind 127.0.0.1

Abre http://localhost:8000/?preview=1 para probar con ratón y teclado en PC. Pulsa Abrir prueba en PC. Haz clic en un campo y escribe con tu teclado o el teclado virtual. Tab y flechas cambian el foco, Enter activa, Escape cierra el teclado virtual. Esta vista no simula ni comprueba un visor.

## Ubuntu / WSL
Desde esta carpeta:

    python3 -m http.server 8000 --bind 0.0.0.0

Abre http://localhost:8000/?preview=1 desde Windows. Si hay problemas de red entre WSL y Windows usa el servidor directamente en Windows o publica la versión HTTPS.

## Quest 3 mediante HTTPS
1. Sube index.html y js/ a la raíz de un repositorio de GitHub.
2. Settings > Pages > Deploy from a branch > rama que contiene el código > / (root) > Save.
3. Espera la publicación y abre la URL HTTPS directamente en Meta Quest Browser. No añadas ?preview=1 en las gafas.
4. Pulsa Entrar a VR y acepta el permiso si se solicita. La página solicita immersive-vr y local-floor.
5. Comprueba la altura y legibilidad de la tablet y utiliza el gatillo de los mandos para introducir datos.
6. Pulsa Salir de VR en la tablet y comprueba que vuelve al inicio y el borrador queda vacío.

No abras index.html con doble clic. Una IP del PC por HTTP no proporciona HTTPS en el visor. La excepción de localhost corresponde al dispositivo que abre la página. No hace falta APK para esta prueba web. No se ha publicado la página automáticamente.

## Modelo de Blender pendiente
Comparte un .glb no vacío de la tablet, con pantalla separada de la carcasa, y sus dimensiones. La pantalla actual es un plano de proporción 4:3 y mide 1.15 x 0.8625 metros virtuales. La escala puede adaptarse al modelo. No se ha cargado un modelo de tablet ni el archivo almacen.glb del proyecto original, que está vacío. No se han implementado secciones 3 o 4.

## Verificación
La sintaxis de ambos módulos JavaScript pasó node --check. La apertura de la vista previa del navegador falló por tiempo de conexión, por lo que no se ha completado la verificación visual. Falta probar WebGL, la descarga de Three.js, el flujo de permisos, mandos y la legibilidad en unas Quest 3 reales. No se garantiza compatibilidad sin esa prueba.

Referencias:
https://developers.meta.com/vr/documentation/web/port-vr-xr/
https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
