# Entrada del usuario desde Gatex2.glb

## Aplicar en el proyecto
Haz una copia de seguridad de main.js y escenario.js actuales. Copia los archivos de esta entrega:
- js/main.js: sustituye el anterior.
- js/escenario.js: sustituye el anterior.
- js/entrada-vr.mjs: nuevo.
- js/referencia-cono.mjs: nuevo.
- assets/Gatex2.glb: nuevo.

Conserva index.html, inicio.js, catalogos.js y desplegables.mjs. altura-vr.mjs puede permanecer como archivo, pero ya no se importa: la entrada desde el cono reemplaza la altura fija de 1.50 m. Gatex1.glb y modelo-tablet.js tampoco se cargan. No es necesario borrarlos.

Esta entrega se preparó en outputs; no modificó la carpeta original de OneDrive ni el GLB de Downloads.

## Decisiones confirmadas
Se utiliza la punta del cono Usuario, su altura en el modelo y la dirección completa de base a punta, incluida su inclinación. La vista queda 1 cm más allá de la punta siguiendo esa dirección. El cono se oculta después de obtener la referencia. La tablet se centra frente a la persona conservando su geometría, tamaño, materiales e interfaz.

## Referencia obtenida
Se detectó un único nodo Usuario, con una malla de 128 vértices que contiene 33 posiciones distintas: 32 forman la base circular y una es la punta. La identificación compara geometría y coplanaridad; no asume que el cono apunta hacia X, Y o Z.

Tras aplicar las transformaciones del objeto:
- Centro de base: aproximadamente (-10.757259, 5.192857, 0).
- Punta: aproximadamente (-8.758111, 5.134486, 0).
- Dirección normalizada base → punta: (0.999574, -0.029186, 0).
- Vista inicial, 1 cm después: aproximadamente (-8.748115, 5.134195, 0).

La altura de entrada queda, por tanto, cerca de 5.13 metros en las coordenadas de este escenario, no a 1.50 m. No se baja ni se normaliza el modelo: es la altura que define tu cono. La inclinación vertical es de aproximadamente 1.67 grados hacia abajo.

## PC y WebXR
En PC, la cámara usa directamente la posición y orientación deducidas. En VR, al llegar la primera pose válida del visor, se calcula un nuevo espacio de referencia con posición Y orientación completas. El desplazamiento se aplica mediante getOffsetReferenceSpace y renderer.xr.setReferenceSpace, por igual al visor y a ambos mandos.

La transformación del origen es: pose real inicial × inversa de la pose virtual deseada. Por ello, la primera pose virtual coincide con la referencia, aunque el operador inicie sentado o mirando en otra dirección. El ajuste sucede una vez en cada sesión. Después se conservan los movimientos de cabeza y manos; no se fija la altura ni se corrige la dirección continuamente.

Se omite el renderizado del fotograma donde se instala el espacio nuevo para que la primera vista renderizada no mezcle poses antiguas de ojos o mandos con la entrada nueva. Al salir, vuelve a configurarse la vista de PC desde el cono.

## Tablet y escenario
La pantalla sigue midiendo 1.15 x 0.8625 m, dentro del mismo marco sencillo. Se centra a 1.35 m delante de la dirección de entrada completa y mira hacia la persona. Su altura se deriva ahora del punto del cono; no se fuerza a 1.50 m. El centrado se realiza al entrar y la tablet permanece fija en el mundo después; no persigue a la cabeza.

No cambió el formulario, los catálogos, los desplegables, el teclado, las zonas de selección ni los eventos de los mandos. No se conectó el backend. Se conserva el fondo inferior azul oscuro y superior gris claro.

Gatex2.glb se añade sin mover, girar, escalar ni recolorear sus objetos. La única modificación de visualización es Usuario.visible=false, autorizada para ocultar la referencia. No se eliminan sus datos ni se cambia el archivo original. No contiene SoporteTablet ni AnclajeTablet. El cargador mantiene una única instancia del escenario; deja de cargar Gatex1.glb.

Si falta Usuario, está duplicado, no puede distinguirse un cono inequívoco o falla el archivo, se informa explícitamente en el inicio y se bloquea la entrada; no se adivina un punto ni se carga el modelo anterior.

## Pruebas realizadas y límites
Pasó la sintaxis de los cuatro módulos JavaScript. Las pruebas leyeron la geometría real de Gatex2.glb, verificaron la punta/base y la igualdad binaria del archivo copiado con el original. La detección también pasó con un cono girado de forma oblicua y rechazó geometría insuficiente.

La calibración se comprobó con tres alturas y tres orientaciones reales iniciales, espera de seguimiento válido, conservación de traslaciones y giros posteriores, relación mano-ojo y un ajuste por sesión. La prueba de regresión del formulario y desplegables pasó. Se comparó literalmente su código para confirmar que los controles, la geometría de tablet y la interfaz permanecen intactos.

No se ha realizado una prueba visual de WebGL ni una prueba física en Quest 3. Falta confirmar que el encuadre coincide con lo esperado, que el cono no aparece, que la tablet se ve centrada y legible y que los dos mandos funcionan desde la nueva ubicación. También falta verificar fluidez y la visibilidad de los elementos lejanos con la niebla existente.

## Ejecutar
Desde la carpeta completa del proyecto, con Python instalado:

    py -m http.server 8000

En Ubuntu/WSL:

    python3 -m http.server 8000 --bind 0.0.0.0

Prueba PC: http://localhost:8000/?preview=1. Para Quest utiliza una URL HTTPS válida sin preview=1. Recarga completamente tras copiar los archivos y no abras index.html mediante doble clic.
