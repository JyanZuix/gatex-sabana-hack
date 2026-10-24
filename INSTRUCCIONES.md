# Tablet independiente y centrada

Copia únicamente js/main.js de esta entrega a js/main.js de tu proyecto, guardando antes una copia del anterior. Conserva altura-vr.mjs, catalogos.js, desplegables.mjs, inicio.js e index.html. No hace falta borrar los archivos GLB o modelo-tablet.js: ya no se importan ni se cargan.

Esta versión elimina de la escena todo el GLB, incluida la base, AnclajeTablet y Tarjeta1. La tablet utiliza únicamente un marco sencillo y la pantalla interactiva existente, sin modelos externos.

En PC el centro de la tablet queda en (0, 1.50, -1.35). En VR conserva la calibración inicial de vista a 1.50 m incluso sentado; al obtener la pose válida centra la tablet en la dirección horizontal de la mirada inicial, a 1.35 m y con el centro a 1.50 m. Esto sucede una vez al entrar; después la tablet permanece fija y se conserva el movimiento libre de la cabeza. Al volver a entrar se centra de nuevo.

Para evitar la inclinación y rotación del GLB, la pantalla queda vertical y mirando al usuario. Se recupera su tamaño independiente original de 1.15 x 0.8625 m, con proporción 4:3. Al centrarla verticalmente en la vista, el borde inferior queda aproximadamente a 1.07 m; esta versión reemplaza la distribución anterior de borde inferior a 75 cm.

Los desplegables, el teclado, las zonas de selección y los mandos conservan su lógica anterior. No hay envío al backend. El original de OneDrive no se modificó porque esta sesión no tiene escritura en esa carpeta.

Comprobaciones: sintaxis de main.js; regresión de desplegables y teclado; centrado a 1.35 m y altura 1.50 m en cuatro direcciones horizontales. No se ha verificado visualmente ni en Quest 3: falta probar entrada/salida, lectura y selección con ambos mandos.

Recarga completamente la página servida por HTTPS después de copiar el archivo. Para PC usa ?preview=1; para Quest utiliza la dirección sin ese parámetro.
