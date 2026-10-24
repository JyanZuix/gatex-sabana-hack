# Sustitución por Gatex4.glb

Guarda una copia de seguridad de main.js y escenario.js, y copia estos tres archivos a tu proyecto:
- js/main.js: sustituye el actual; solo se cambia el nombre de modelo en los errores de carga.
- js/escenario.js: sustituye el actual; solo se cambia assets/Gatex3.glb por assets/Gatex4.glb y el nombre en su mensaje de error.
- assets/Gatex4.glb: nuevo, copia binaria idéntica al archivo de Downloads.

Conserva entrada-vr.mjs, referencia-cono.mjs, catalogos.js, desplegables.mjs, inicio.js e index.html. Gatex3.glb puede permanecer como archivo, pero ya no se carga. No se modificó la carpeta original de OneDrive ni el modelo original.

Todo el resto de los dos archivos JS se conserva exactamente. Esto incluye la entrada 1 cm después de la punta de Usuario y su dirección completa, altura derivada del modelo, cono oculto, calibración una vez por sesión, movimientos naturales, mandos alineados y misma vista en PC.

La tablet conserva su centrado, descenso de 1 metro, aumento de 30 %, inclinación de atril de 45 grados, tamaño proporcional, formulario, desplegables y teclado. También se conserva el fondo azul/gris y la ausencia de niebla. No se cambia ninguna transformación, material o jerarquía del GLB nuevo.

Se verificó que Usuario conserva transformación, geometría, normales, UV e índices respecto a Gatex3; el cambio de número interno de malla en la exportación no cambia la referencia. El archivo nuevo tiene siete nodos: Tarjeta1, Flecha, Barco, Auto, Signos, Cylinder y Usuario. Se respeta esa organización sin recrear las tarjetas que ya no están como nodos independientes. No contiene SoporteTablet ni AnclajeTablet y no requiere recursos externos.

Pasaron las comprobaciones de sintaxis, la comparación del cono, la comparación binaria de la copia y la verificación de que los cambios de código son únicamente el nombre de archivo en ruta y errores. No se ha realizado renderizado WebGL ni prueba física en Quest 3 de esta versión. Falta comprobar visualmente el escenario actualizado, rendimiento y selección con los mandos.

Recarga completamente la página después de copiar. Para PC usa el servidor HTTP con ?preview=1; para Quest usa HTTPS sin ese parámetro. No abras index.html con doble clic.
